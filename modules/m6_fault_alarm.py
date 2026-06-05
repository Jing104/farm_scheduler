import math
import random
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QLineEdit, QComboBox, QSplitter, QGroupBox, 
                             QHeaderView)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from core.db_manager import AgronomicDatabaseCore

class MaintainLifecycleChart(QWidget):
    """
    自研数字维保生命周期时态看板（底层QPainter重绘组件）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.pending_count = 0
        self.fixing_count = 0
        self.closed_count = 0

    def update_lifecycle_metrics(self, pending, fixing, closed):
        self.pending_count = pending
        self.fixing_count = fixing
        self.closed_count = closed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        
        total = self.pending_count + self.fixing_count + self.closed_count
        if total == 0:
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.setPen(QColor("#6C7A8C"))
            painter.drawText(20, h - 20, "全局数据链：当前全网未检测到活跃异常工单")
            return

        # 计算各自直方图或矩形比例块（工业微晶条形态）
        bar_max_w = w - 160
        bar_h = 24
        start_x = 25
        start_y = 40
        
        # 类别一：等待指派
        ratio_p = self.pending_count / total
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#DC2626"))) # 强阻断红
        painter.drawRect(start_x, start_y, int(bar_max_w * ratio_p) + 2, bar_h)
        painter.setPen(QColor("#E2E8F0"))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(bar_max_w + 40, start_y + 16, f"等待指派: {self.pending_count} 宗")

        # 类别二：协同维保
        ratio_f = self.fixing_count / total
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#D97706"))) # 警告橙
        painter.drawRect(start_x, start_y + 45, int(bar_max_w * ratio_f) + 2, bar_h)
        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(bar_max_w + 40, start_y + 61, f"正在协同: {self.fixing_count} 宗")

        # 类别三：闭环归档
        ratio_c = self.closed_count / total
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#059669"))) # 安全绿
        painter.drawRect(start_x, start_y + 90, int(bar_max_w * ratio_c) + 2, bar_h)
        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(bar_max_w + 40, start_y + 106, f"闭环归档: {self.closed_count} 宗")

        painter.setPen(QColor("#00FFCC"))
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.drawText(start_x, h - 15, "测控提示：工单生命周期配比状况实时动态解析")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_ticket_id = None
        self.selected_faulty_machinery_id = None
        self.db = AgronomicDatabaseCore()
        
        self.apply_internal_style()
        self.init_ui_components()
        
        # 挂载异常扫描监测总线时钟（实现m1注入故障或m4越界时自动在此插入工单）
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.global_fault_interception_and_auto_ticket_tick)
        self.scan_timer.start(1000)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 区域一：异常工单批量流转交互控制台
        ctrl_box = QGroupBox("全网突发设备工况故障异常指派管理控制台")
        ctrl_box.setObjectName("CtrlBox")
        ctrl_layout = QHBoxLayout(ctrl_box)
        ctrl_layout.setSpacing(15)

        ctrl_layout.addWidget(QLabel("指派协同高级工程师:"))
        self.combo_engineer = QComboBox()
        self.combo_engineer.addItems(["张晓刚（高级硬件师）", "王建国（北斗调校员）", "李德华（液压总工程师）", "刘明亮（边缘测控专家）"])
        ctrl_layout.addWidget(self.combo_engineer, stretch=2)

        btn_assign = QPushButton("下发无线故障维修指派工单")
        btn_assign.setObjectName("ActionBtn")
        btn_assign.clicked.connect(self.sqlite_update_assign_engineer)
        ctrl_layout.addWidget(btn_assign, stretch=1)

        btn_close_ticket = QPushButton("实施故障底层清错并闭环归档")
        btn_close_ticket.setObjectName("CloseBtn")
        btn_close_ticket.clicked.connect(self.sqlite_update_close_ticket_and_clear_fault)
        ctrl_layout.addWidget(btn_close_ticket, stretch=1)

        layout.addWidget(ctrl_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        # 区域二：左面板-两张细分排查表网格
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("当前存储库（SQLite）托管的全量历史与突发故障维保单账目"))
        self.ticket_table = QTableWidget()
        self.ticket_table.setColumnCount(5)
        self.ticket_table.setHorizontalHeaderLabels(["工单识别码", "关联农机", "突发时间轴", "当前处理状态", "委派责任人"])
        self.ticket_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ticket_table.verticalHeader().setVisible(False)
        self.ticket_table.itemSelectionChanged.connect(self.handle_ticket_row_selection)
        left_layout.addWidget(self.ticket_table)

        left_layout.addSpacing(5)
        left_layout.addWidget(QLabel("全网当前遭遇总线中断或突发红线阻断的异常机车底账"))
        self.machinery_table = QTableWidget()
        self.machinery_table.setColumnCount(4)
        self.machinery_table.setHorizontalHeaderLabels(["异常机车主键", "分配类别", "主泵反馈压", "油温感知"])
        self.machinery_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.machinery_table.verticalHeader().setVisible(False)
        self.machinery_table.itemSelectionChanged.connect(self.handle_machinery_row_selection)
        left_layout.addWidget(self.machinery_table)

        # 区域三：右面板-严重度深度解算看板与图表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        chart_group = QGroupBox("全网活动故障工单各阶段状态生命周期占比图谱")
        cg_layout = QVBoxLayout(chart_group)
        self.lifecycle_chart = MaintainLifecycleChart()
        cg_layout.addWidget(self.lifecycle_chart)
        right_layout.addWidget(chart_group)

        calc_group = QGroupBox("当前活动故障严重度加权非线性动态解算控制台")
        cal_layout = QVBoxLayout(calc_group)
        cal_layout.setSpacing(8)

        self.lbl_severity_output = QLabel("算法处于监听态：请在左下方选择需要执行深度解算的异常机车")
        self.lbl_severity_output.setWordWrap(True)
        self.lbl_severity_output.setObjectName("MetricText")
        cal_layout.addWidget(self.lbl_severity_output)
        
        right_layout.addWidget(calc_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([590, 470])
        layout.addWidget(splitter)

        self.refresh_all_grids_from_sqlite()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLineEdit, QComboBox { background-color: #161D26; border: 1px solid #232E3C; color: #FFFFFF; padding: 5px; font-size: 12px; border-radius: 2px; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 11px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QLabel#MetricText { font-family: "Segoe UI", monospace; font-size: 11px; color: #8A9BB0; background-color: #18222E; padding: 12px; border-left: 2px solid #DC2626; line-height: 18px; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 7px; border-radius: 2px; }
            QPushButton#CloseBtn { background-color: #065F46; color: #A7F3D0; border: 1px solid #047857; font-weight: bold; padding: 7px; border-radius: 2px; }
            QPushButton#CloseBtn:hover { background-color: #047857; }
        """)

    def global_fault_interception_and_auto_ticket_tick(self):
        """
        核心独创机制：高频对分布式农机表进行状态探针扫描，一旦捕获新增故障异常，自动无缝跨表INSERT入工单队列
        """
        fault_machineries = self.db.execute_query("SELECT node_id FROM field_machinery WHERE status='故障异常'")
        
        for m_row in fault_machineries:
            nid = m_row[0]
            # 查验该车是否已经在工单库中立账，规避频繁无限插入
            exist_check = self.db.execute_query("SELECT COUNT(*) FROM field_maintain_logs WHERE node_id=? AND handle_status != '已归档闭环'", (nid,))
            if exist_check and exist_check[0][0] == 0:
                new_ticket_id = f"TICKET-{random.randint(803, 999)}"
                cur_time = time.strftime("%Y-%m-%d %H:%M:%S")
                self.db.execute_update("""
                    INSERT INTO field_maintain_logs VALUES (?, ?, '系统总线硬捕获：车载控制模块反馈数值越过安全红线阻断', ?, '等待指派', '未指派工程师')
                """, (new_ticket_id, nid, cur_time))

        self.refresh_grid_values_only()

    def refresh_all_grids_from_sqlite(self):
        """
        全量关系加载映射（增删改查之【查】）
        """
        # 1. 映射全量维保单
        t_rows = self.db.execute_query("SELECT ticket_id, node_id, trigger_time, handle_status, repair_engineer FROM field_maintain_logs")
        self.ticket_table.setRowCount(len(t_rows))
        for r_idx, row in enumerate(t_rows):
            tid, nid, t_time, status, eng = row
            self.ticket_table.setItem(r_idx, 0, QTableWidgetItem(tid))
            self.ticket_table.setItem(r_idx, 1, QTableWidgetItem(nid))
            self.ticket_table.setItem(r_idx, 2, QTableWidgetItem(t_time))
            self.ticket_table.setItem(r_idx, 3, QTableWidgetItem(status))
            self.ticket_table.setItem(r_idx, 4, QTableWidgetItem(eng))
            for c in range(5):
                self.ticket_table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.ticket_table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. 映射异常机车表快照
        m_rows = self.db.execute_query("SELECT node_id, vehicle_type, pump_pressure, hydraulic_temp FROM field_machinery WHERE status='故障异常'")
        self.machinery_table.setRowCount(len(m_rows))
        for r_idx, row in enumerate(m_rows):
            nid, v_type, press, temp = row
            self.machinery_table.setItem(r_idx, 0, QTableWidgetItem(nid))
            self.machinery_table.setItem(r_idx, 1, QTableWidgetItem(v_type))
            self.machinery_table.setItem(r_idx, 2, QTableWidgetItem(f"{press:.1f} 兆帕"))
            self.machinery_table.setItem(r_idx, 3, QTableWidgetItem(f"{temp:.1f} 度"))
            for c in range(4):
                self.machinery_table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.machinery_table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.refresh_grid_values_only()

    def refresh_grid_values_only(self):
        pending = 0
        fixing = 0
        closed = 0

        # 局部刷新维保单网格文字与变色，并顺带进行状态占比统计
        for r_idx in range(self.ticket_table.rowCount()):
            tid = self.ticket_table.item(r_idx, 0).text()
            res = self.db.execute_query("SELECT handle_status, repair_engineer FROM field_maintain_logs WHERE ticket_id=?", (tid,))
            if res:
                status, eng = res[0]
                status_item = self.ticket_table.item(r_idx, 3)
                status_item.setText(status)
                self.ticket_table.item(r_idx, 4).setText(eng)
                
                if status == "等待指派":
                    pending += 1
                    status_item.setForeground(QColor("#EF4444"))
                elif status == "正在协同维修":
                    fixing += 1
                    status_item.setForeground(QColor("#F59E0B"))
                elif status == "已归档闭环":
                    closed += 1
                    status_item.setForeground(QColor("#10B981"))

        self.lifecycle_chart.update_lifecycle_metrics(pending, fixing, closed)

        # 局部高频联动机车快照更新
        for r_idx in range(self.machinery_table.rowCount()):
            nid = self.machinery_table.item(r_idx, 0).text()
            res = self.db.execute_query("SELECT pump_pressure, hydraulic_temp FROM field_machinery WHERE node_id=?", (nid,))
            if res:
                press, temp = res[0]
                self.machinery_table.item(r_idx, 2).setText(f"{press:.2f} 兆帕")
                self.machinery_table.item(r_idx, 3).setText(f"{temp:.2f} 度")

    def handle_ticket_row_selection(self):
        selected = self.ticket_table.selectedRanges()
        if not selected: return
        self.selected_ticket_id = self.ticket_table.item(selected[0].topRow(), 0).text()

    def handle_machinery_row_selection(self):
        selected = self.machinery_table.selectedRanges()
        if not selected: return
        self.selected_faulty_machinery_id = self.machinery_table.item(selected[0].topRow(), 0).text()
        
        # 激活核心算法：多指标偏离度加切严重等级解算方程
        res = self.db.execute_query("SELECT pump_pressure, hydraulic_temp, engine_rpm FROM field_machinery WHERE node_id=?", (self.selected_faulty_machinery_id,))
        if res:
            press, temp, rpm = res[0]
            
            # 偏离度解算公式
            press_deviation = abs(64.0 - press) / 64.0
            temp_deviation = max(0.0, (temp - 60.0) / 60.0)
            
            severity_index = (press_deviation * 0.6 + temp_deviation * 0.4) * 100.0
            
            if severity_index > 40.0:
                level = "灾难性非线性溃断（全车就地二级强熔断保护）"
            elif severity_index > 15.0:
                level = "突发紧急抢修工况（传感器总线拥堵严重）"
            else:
                level = "常规轻微耗损偏移（允许边缘端降频维持）"
                
            self.lbl_severity_output.setText(
                f"异常节点严重度解算闭环：\n"
                f"    - 分析机车: {self.selected_faulty_machinery_id}\n"
                f"    - 主压力偏离系数: {press_deviation:.2f}\n"
                f"    - 油温热过载比率: {temp_deviation:.2f}\n"
                f"    - 动态严重度权重得分: {severity_index:.1f} 节点分\n"
                f"    - 最终判定资信级别: {level}"
            )

    def sqlite_update_assign_engineer(self):
        """
        生命周期流转交互之【改】：修改工单状态，指派责任人
        """
        if not self.selected_ticket_id:
            QMessageBox.warning(self, "指派终止", "请先在上方历史网格中选中需要指派的异常工单。")
            return
            
        res = self.db.execute_query("SELECT handle_status FROM field_maintain_logs WHERE ticket_id=?", (self.selected_ticket_id,))
        if res and res[0][0] == "已归档闭环":
            QMessageBox.information(self, "流转拦截", "该工单已处于历史终结状态，拒绝二次重复指派。")
            return
            
        target_engineer = self.combo_engineer.currentText()
        status = self.db.execute_update("""
            UPDATE field_maintain_logs SET handle_status='正在协同维修', repair_engineer=? WHERE ticket_id=?
        """, (target_engineer, self.selected_ticket_id))
        
        if status:
            self.refresh_grid_values_only()

    def sqlite_update_close_ticket_and_clear_fault(self):
        """
        生命周期流转交互之【改/跨表级联更新】：终结工单并同步反向改写机车状态，解除故障阻断
        """
        if not self.selected_ticket_id:
            return
            
        res = self.db.execute_query("SELECT node_id, handle_status FROM field_maintain_logs WHERE ticket_id=?", (self.selected_ticket_id,))
        if not res: return
        associated_node_id, cur_status = res[0]
        
        if cur_status == "已归档闭环": return
        
        # 1. 终结维保单状态
        status_a = self.db.execute_update("UPDATE field_maintain_logs SET handle_status='已归档闭环' WHERE ticket_id=?", (self.selected_ticket_id,))
        
        # 2. 强力级联反向清洗农机表对应的状态机，将故障拔除，使其重获自由并网能力
        status_b = self.db.execute_update("""
            UPDATE field_machinery SET status='就绪', pump_pressure=64.0, hydraulic_temp=59.5, engine_rpm=1650 WHERE node_id=?
        """, (associated_node_id,))
        
        if status_a and status_b:
            QMessageBox.information(self, "闭环成功", f"总线无线复位指令下发成功！\n工单 {self.selected_ticket_id} 已解脱。\n机车 {associated_node_id} 底层硬件锁已卸载，状态复位为【就绪】。")
            self.selected_ticket_id = None
            self.refresh_all_grids_from_sqlite()

    def get_module_title(self):
        return "06. 农机故障维护"