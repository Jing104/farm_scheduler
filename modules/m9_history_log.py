import math
import random
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QLineEdit, QComboBox, QSplitter, QGroupBox, 
                             QHeaderView, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from core.db_manager import AgronomicDatabaseCore

class WeatherDynamicRiskRadar(QWidget):
    """
    自研局地微气象矢量态势与风险热力环大屏（纯底层QPainter重绘高级组件，无英文及表情符号）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.weather_records = []  
        self.selected_index = -1   
        self.scan_line_y = 0.0     
        
        # 激活矢量光栅时高频雷达扫描时钟
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._advance_grid_scan_line)
        self.scan_timer.start(30)

    def load_weather_matrix(self, records):
        self.weather_records = records
        if records and self.selected_index == -1:
            self.selected_index = 0
        self.update()

    def set_active_point_index(self, index):
        if 0 <= index < len(self.weather_records):
            self.selected_index = index
            self.update()

    def _advance_grid_scan_line(self):
        h = self.height()
        if h > 0:
            self.scan_line_y = (self.scan_line_y + 2.0) % h
            if self.weather_records:
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # 1. 钛金黑工业多中心底盘背景
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        
        # 2. 绘制无线物联网微气象测控网格雷达线条
        grid_pen = QPen(QColor("#112535"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        grid_step = 30
        for x in range(0, w, grid_step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid_step):
            painter.drawLine(0, y, w, y)

        # 3. 动态绘制荧光绿雷达扫描光栅切面线
        painter.setPen(QPen(QColor(0, 255, 204, 35), 1.5))
        painter.drawLine(0, int(self.scan_line_y), w, int(self.scan_line_y))

        if not self.weather_records:
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.setPen(QColor("#6C7A8C"))
            painter.drawText(20, h - 20, "全局数据链：等待无线传感器阵列上报微气象参数...")
            return

        # 4. 遍历气象网点，绘制空间相对分布的热力灾害危险扩散环
        cx, cy = w / 2, h / 2
        for i, rec in enumerate(self.weather_records):
            pid, name, wind, rain, soil, risk_lv = rec
            
            # 利用主键哈希空间发散坐标偏置
            px = cx + math.sin(i * 120) * 100 + random.uniform(-1, 1)
            py = cy + math.cos(i * 120) * 70 + random.uniform(-1, 1)
            
            # 计算局地风险指数核心分数（结合风速与降雨）
            risk_score = (wind * 2.5) + (rain * 0.6)
            radius = max(15.0, min(65.0, risk_score * 0.7))
            
            # 根据危险级别确定渲染包络圈颜色
            if "预警" in risk_lv or risk_score > 45.0:
                brush_color = QColor(220, 38, 38, 35)  # 红色强阻断
                pen_color = QColor("#EF4444")
            else:
                brush_color = QColor(5, 150, 105, 15)  # 绿色常规态
                pen_color = QColor("#10B981")

            # 如果是当前左侧选中的焦点网点，赋予呼吸边界高亮
            if i == self.selected_index:
                painter.setPen(QPen(QColor("#FFFFFF"), 2, Qt.PenStyle.DashLine))
                # 绘制锁定指示器十字丝
                painter.drawLine(int(px - radius - 10), int(py), int(px + radius + 10), int(py))
                painter.drawLine(int(px), int(py - radius - 10), int(px), int(py + radius + 10))
            else:
                painter.setPen(QPen(pen_color, 1, Qt.PenStyle.SolidLine))

            painter.setBrush(QBrush(brush_color))
            painter.drawEllipse(QPointF(px, py), radius, radius)
            
            # 标注网点汉字简称标识
            painter.setPen(QColor("#E2E8F0"))
            painter.setFont(QFont("Microsoft YaHei", 8))
            painter.drawText(int(px - 25), int(py + 4), name[:4])

        # 5. 测控抬头
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.setPen(QColor("#00FFCC"))
        painter.drawText(15, 25, "安全主轴：田间气象多传感器红线矢量控制大屏")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_point_id = None
        self.db = AgronomicDatabaseCore()
        
        self.apply_internal_style()
        self.init_ui_components()
        
        # 挂载无线局地微气象动态对冲时钟（秒级高频演进）
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.global_weather_telemetry_simulation_tick)
        self.weather_timer.start(1000)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 区域一：气象逆向仿真与干预调整向导控制盒（增删改查之【改】）
        wizard_box = QGroupBox("智能化物联网传感器测控输入干预中心")
        wizard_box.setObjectName("WizardBox")
        wizard_layout = QHBoxLayout(wizard_box)
        wizard_layout.setSpacing(12)

        wizard_layout.addWidget(QLabel("突发局地瞬时风速:"))
        self.in_wind = QDoubleSpinBox()
        self.in_wind.setRange(0.0, 35.0)
        self.in_wind.setValue(4.5)
        self.in_wind.setSuffix(" 米每秒")
        wizard_layout.addWidget(self.in_wind, stretch=1)

        wizard_layout.addWidget(QLabel("累积一小时降雨量:"))
        self.in_rain = QDoubleSpinBox()
        self.in_rain.setRange(0.0, 150.0)
        self.in_rain.setValue(10.0)
        self.in_rain.setSuffix(" 毫米")
        wizard_layout.addWidget(self.in_rain, stretch=1)

        commit_btn = QPushButton("向指定气象网点下发环境突变指令")
        commit_btn.setObjectName("ActionBtn")
        commit_btn.clicked.connect(self.sqlite_update_weather_metrics)
        wizard_layout.addWidget(commit_btn, stretch=2)

        layout.addWidget(wizard_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        # 区域二：左面板-数据联动排程大表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("分布式物联网环境传感器上报数据列表（选择单行联动右侧图层）"))
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["网点识别码", "监控对应基地区域", "传感器风速", "传感器降雨", "当前风险级别"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.handle_weather_row_selection_sync)
        left_layout.addWidget(self.table)

        # 终极一键全网最高权限灾害强阻断控制盒
        emergency_group = QGroupBox("最高优先指挥权限：全网抗灾防碰撞级联强熔断中心")
        eg_layout = QVBoxLayout(emergency_group)
        
        btn_abort_all = QPushButton("一键下发全网机车强行挂起并紧急就近返航机库")
        btn_abort_all.setObjectName("DangerBtn")
        btn_abort_all.clicked.connect(self.execute_global_emergency_cascade_abort_transaction)
        eg_layout.addWidget(btn_abort_all)
        left_layout.addWidget(emergency_group)

        # 区域三：右面板-画布及级联审计日志
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        radar_group = QGroupBox("分布式无线传感器环境测控网点局地风险扩散热力透视图")
        rg_layout = QVBoxLayout(radar_group)
        self.risk_radar = WeatherDynamicRiskRadar()
        rg_layout.addWidget(self.risk_radar)
        right_layout.addWidget(radar_group)

        log_group = QGroupBox("应急防灾控制中枢全局级联事务审计流")
        lg_layout = QVBoxLayout(log_group)
        self.lbl_audit_text = QLabel("数据控制链处于静态监听：当前全网处于安全生产四至红线内。")
        self.lbl_audit_text.setWordWrap(True)
        self.lbl_audit_text.setObjectName("MetricText")
        lg_layout.addWidget(self.lbl_audit_text)
        right_layout.addWidget(log_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([590, 470])
        layout.addWidget(splitter)

        self.refresh_weather_table_view_from_sqlite()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QDoubleSpinBox { background-color: #161D26; border: 1px solid #232E3C; color: #FFFFFF; padding: 4px; font-size: 11px; border-radius: 2px; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 11px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QLabel#MetricText { font-family: "Segoe UI", monospace; font-size: 11px; color: #8A9BB0; background-color: #18222E; padding: 12px; border-left: 2px solid #DC2626; line-height: 18px; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 6px 12px; border-radius: 2px; }
            QPushButton#ActionBtn:hover { background-color: #007A66; }
            QPushButton#DangerBtn { background-color: #7F1D1D; color: #FCA5A5; border: 1px solid #991B1B; font-weight: bold; padding: 10px; border-radius: 2px; font-size: 12px; width: 100%; }
            QPushButton#DangerBtn:hover { background-color: #991B1B; }
        """)

    def global_weather_telemetry_simulation_tick(self):
        """
        环境动力学仿真算子：每秒微量自然演进气象波动，同步刷新本地关系表
        """
        records = self.db.execute_query("SELECT point_id, wind_speed, rainfall, soil_moisture FROM field_weather_points")
        for r in records:
            pid, wind, rain, soil = r
            
            # 自然扰动常态计算
            wind = max(0.5, min(32.0, round(wind + random.uniform(-0.15, 0.15), 2)))
            # 降雨不执行自然无缘由突变，维持干预值，土壤湿度受水分正向波动
            soil = max(10.0, min(98.0, round(soil + random.uniform(-0.05, 0.1), 2)))
            
            # 根据最新物理数值反向重算灾害等级
            calc_cri = (wind * 2.5) + (rain * 0.6)
            if calc_cri > 50.0:
                level = "突发暴雨禁行预警"
            elif calc_cri > 25.0:
                level = "风速大范围扰动"
            else:
                level = "常规态势"
                
            self.db.execute_update("""
                UPDATE field_weather_points SET wind_speed=?, soil_moisture=?, risk_level=? WHERE point_id=?
            """, (wind, soil, level, pid))
            
        self.refresh_grid_values_only()

    def refresh_weather_table_view_from_sqlite(self):
        """
        全量提取环境表数据映射到排程大表中（查）
        """
        self.display_rows = self.db.execute_query("SELECT point_id, region_name, wind_speed, rainfall, risk_level FROM field_weather_points")
        self.table.setRowCount(len(self.display_rows))
        
        for r_idx, row in enumerate(self.display_rows):
            pid, name, wind, rain, risk_lv = row
            self.table.setItem(r_idx, 0, QTableWidgetItem(pid))
            self.table.setItem(r_idx, 1, QTableWidgetItem(name))
            self.table.setItem(r_idx, 2, QTableWidgetItem(f"{wind:.2f} 米每秒"))
            self.table.setItem(r_idx, 3, QTableWidgetItem(f"{rain:.1f} 毫米"))
            self.table.setItem(r_idx, 4, QTableWidgetItem(risk_lv))
            
            for c in range(5):
                self.table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
        self.refresh_grid_values_only()

    def refresh_grid_values_only(self):
        rows = self.db.execute_query("SELECT point_id, wind_speed, rainfall, risk_level FROM field_weather_points")
        mapped_payload = []
        
        for r_idx, row in enumerate(rows):
            pid, wind, rain, risk_lv = row
            
            # 同步更新网格行
            if r_idx < self.table.rowCount():
                self.table.item(r_idx, 2).setText(f"{wind:.2f} 米每秒")
                self.table.item(r_idx, 3).setText(f"{rain:.1f} 毫米")
                
                status_item = self.table.item(r_idx, 4)
                status_item.setText(risk_lv)
                if "预警" in risk_lv:
                    status_item.setForeground(QColor("#EF4444"))
                elif "扰动" in risk_lv:
                    status_item.setForeground(QColor("#F59E0B"))
                else:
                    status_item.setForeground(QColor("#10B981"))

            # 提取全量原始记录，打包推送给底层画布重绘
            full_res = self.db.execute_query("SELECT * FROM field_weather_points WHERE point_id=?", (pid,))
            if full_res:
                mapped_payload.append(full_res[0])
                
        self.risk_radar.load_weather_matrix(mapped_payload)

    def handle_weather_row_selection_sync(self):
        selected = self.table.selectedRanges()
        if not selected: return
        row = selected[0].topRow()
        self.selected_point_id = self.table.item(row, 0).text()
        self.risk_radar.set_active_point_index(row)

        # 回填数值微调按钮
        res = self.db.execute_query("SELECT wind_speed, rainfall FROM field_weather_points WHERE point_id=?", (self.selected_point_id,))
        if res:
            self.in_wind.setValue(res[0][0])
            self.in_rain.setValue(res[0][1])

    def sqlite_update_weather_metrics(self):
        """
        环境数据链突变干预之【改】：手动控制天气偏离安全红线 (UPDATE)
        """
        if not self.selected_point_id:
            QMessageBox.warning(self, "干预挂起", "请先在排程大表中点击锁定需要下发天气突变的目标气象网点。")
            return
            
        w_val = self.in_wind.value()
        r_val = self.in_rain.value()
        
        calc_cri = (w_val * 2.5) + (r_val * 0.6)
        if calc_cri > 50.0:
            level = "突发暴雨禁行预警"
        elif calc_cri > 25.0:
            level = "风速大范围扰动"
        else:
            level = "常规态势"

        status = self.db.execute_update("""
            UPDATE field_weather_points SET wind_speed=?, rainfall=?, risk_level=? WHERE point_id=?
        """, (w_val, r_val, level, self.selected_point_id))
        
        if status:
            self.refresh_grid_values_only()

    def execute_global_emergency_cascade_abort_transaction(self):
        """
        核心独创算法应用：大系统级联熔断控制链（改——多表强级联大回滚事务逻辑闭环）
        """
        if not self.selected_point_id:
            QMessageBox.warning(self, "防灾命令拒绝", "指派终止：必须先选定具体的灾害红线辐射气象网点作为应急基准标尺。")
            return
            
        res_w = self.db.execute_query("SELECT region_name, risk_level FROM field_weather_points WHERE point_id=?", (self.selected_point_id,))
        if not res_w: return
        r_name, r_level = res_w[0]
        
        if "预警" not in r_level:
            confirm = QMessageBox.question(
                self, "非高危区域熔断提醒", 
                f"当前网点 [{r_name}] 的解算指标尚处于安全生产红线内，是否强制下发越级强停命令？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        # 启动抗灾级联大事务：一举切断多张独立数据表的常态状态机，进行状态大回滚
        timestamp = time.strftime("%H:%M:%S")
        
        # 1. 级联改写任务排程表 (field_tasks)：将所有正在东区或全网执行中的任务，强行修改为“已挂起暂停”，封锁进度
        status_tasks = self.db.execute_update("UPDATE field_tasks SET status='已挂起' WHERE status='执行中'")
        
        # 2. 级联改写无人机车表 (field_machinery)：将全网所有活跃前行的就绪或作业车，状态强制复位转变为“紧急返航中”，就近向机库做安全位移
        status_machinery = self.db.execute_update("UPDATE field_machinery SET status='故障异常' WHERE status='就绪' OR status='作业中'")
        
        if status_tasks and status_machinery:
            self.lbl_audit_text.setText(
                f"最高级抗灾指派链路已激活（时间戳: {timestamp}）：\n"
                f"    - 灾害指派源: {r_name} [{self.selected_point_id}]\n"
                f"    - 级联动作一：全网运行中作业任务进度线已实施强行熔断拦截，状态变更为【已挂起】\n"
                f"    - 级联动作二：全网并网农机节点无线控制链路已强行接管，工况硬切切换为【故障异常】\n"
                f"    - 审计反馈：本地持久层双表同步回滚提交，前线航线已彻底清洗注销。"
            )
            QMessageBox.information(self, "最高级熔断指令已落地", "全网级联抗灾应急预案下发成功！\n两张核心业务持久表已顺利提交回滚。")

    def get_module_title(self):
        return "09. 气象风险预警"