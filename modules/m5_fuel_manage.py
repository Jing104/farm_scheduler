import math
import random
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QLineEdit, QComboBox, QSplitter, QGroupBox, 
                             QHeaderView, QSpinBox)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from core.db_manager import AgronomicDatabaseCore

class FuelEnergyPieChart(QWidget):
    """
    自研大屏数字化能耗占比图表（底层QPainter重绘）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.normal_count = 0
        self.low_count = 0

    def update_energy_proportions(self, normal, low):
        self.normal_count = normal
        self.low_count = low
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        
        total = self.normal_count + self.low_count
        center_x, center_y = int(w / 3), int(h / 2)
        radius = min(w, h) // 2 - 25
        
        if total == 0:
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.setPen(QColor("#6C7A8C"))
            painter.drawText(20, h - 20, "数据链路：等待读取全网能耗比率")
            return

        angle_normal = int((self.normal_count / total) * 360)
        angle_low = 360 - angle_normal

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#007A66")))
        painter.drawPie(center_x - radius, center_y - radius, radius * 2, radius * 2, 90 * 16, -angle_normal * 16)

        if angle_low > 0:
            painter.setBrush(QBrush(QColor("#D97706")))
            painter.drawPie(center_x - radius, center_y - radius, radius * 2, radius * 2, (90 - angle_normal) * 16, -angle_low * 16)

        legend_x = center_x + radius + 40
        painter.setFont(QFont("Microsoft YaHei", 9))
        
        painter.setBrush(QBrush(QColor("#007A66")))
        painter.drawRect(legend_x, center_y - 25, 14, 14)
        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(legend_x + 24, center_y - 13, f"能源充沛节点: {self.normal_count} 台")
        
        painter.setBrush(QBrush(QColor("#D97706")))
        painter.drawRect(legend_x, center_y + 10, 14, 14)
        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(legend_x + 24, center_y + 22, f"能耗预警节点: {self.low_count} 台")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_machinery_id = None
        self.selected_station_id = None
        self.db = AgronomicDatabaseCore()
        
        self.apply_internal_style()
        self.init_ui_components()
        
        self.energy_timer = QTimer(self)
        self.energy_timer.timeout.connect(self.global_machinery_energy_consumption_tick)
        self.energy_timer.start(1000)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        wizard_box = QGroupBox("智能化能源补给车与固定加注站资产准入中心")
        wizard_box.setObjectName("WizardBox")
        wizard_layout = QHBoxLayout(wizard_box)
        wizard_layout.setSpacing(12)

        wizard_layout.addWidget(QLabel("资源唯一识别码:"))
        self.in_station_id = QLineEdit()
        self.in_station_id.setPlaceholderText("例如: 加注车-05")
        wizard_layout.addWidget(self.in_station_id, stretch=1)

        wizard_layout.addWidget(QLabel("补给设备分类:"))
        self.in_station_type = QComboBox()
        self.in_station_type.addItems(["移动式油电混合车", "固定式常规电站", "固定式标准油库"])
        wizard_layout.addWidget(self.in_station_type, stretch=2)

        wizard_layout.addWidget(QLabel("初始储备容量:"))
        self.in_station_stock = QSpinBox()
        self.in_station_stock.setRange(500, 10000)
        self.in_station_stock.setValue(1000)
        self.in_station_stock.setSuffix(" 升/度")
        wizard_layout.addWidget(self.in_station_stock, stretch=1)

        commit_btn = QPushButton("下发准入并记入本地数据库")
        commit_btn.setObjectName("ActionBtn")
        commit_btn.clicked.connect(self.sqlite_insert_station)
        wizard_layout.addWidget(commit_btn, stretch=1)

        layout.addWidget(wizard_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("全网在线机车实时留存电量/油量状况"))
        self.machinery_table = QTableWidget()
        self.machinery_table.setColumnCount(4)
        self.machinery_table.setHorizontalHeaderLabels(["机车编号", "分配类别", "能耗剩余率", "调度优先级"])
        self.machinery_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.machinery_table.verticalHeader().setVisible(False)
        self.machinery_table.itemSelectionChanged.connect(self.handle_machinery_row_selection)
        left_layout.addWidget(self.machinery_table)

        left_layout.addSpacing(5)
        left_layout.addWidget(QLabel("本地关系库托管的补给站与加注车资产"))
        
        self.station_table = QTableWidget()
        self.station_table.setColumnCount(4)
        self.station_table.setHorizontalHeaderLabels(["资产识别码", "补给设备分类", "地理相对坐标", "当前留存总量"])
        self.station_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.station_table.verticalHeader().setVisible(False)
        self.station_table.itemSelectionChanged.connect(self.handle_station_row_selection)
        left_layout.addWidget(self.station_table)

        btn_remove_station = QPushButton("对选中的加注资产执行强制物理注销拔除")
        btn_remove_station.setObjectName("DangerBtn")
        btn_remove_station.clicked.connect(self.sqlite_delete_station)
        left_layout.addWidget(btn_remove_station)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        chart_group = QGroupBox("全网在线机车当前健康能耗状态多道比例图谱")
        cg_layout = QVBoxLayout(chart_group)
        self.pie_chart = FuelEnergyPieChart()
        cg_layout.addWidget(self.pie_chart)
        right_layout.addWidget(chart_group)

        algo_group = QGroupBox("基于多维阻抗的就近智能补给站寻优算法决策")
        ag_layout = QVBoxLayout(algo_group)
        ag_layout.setSpacing(10)

        self.lbl_dispatch_status = QLabel("算法处于静默态：请框选左上方急需加注的低电量机车")
        self.lbl_dispatch_status.setWordWrap(True)
        self.lbl_dispatch_status.setObjectName("MetricText")
        ag_layout.addWidget(self.lbl_dispatch_status)

        btn_optimize = QPushButton("运行就近能耗代价寻优匹配算法并派遣加注")
        btn_optimize.setObjectName("ActionBtn")
        btn_optimize.clicked.connect(self.execute_nearest_station_optimization_solver)
        ag_layout.addWidget(btn_optimize)

        right_layout.addWidget(algo_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([580, 480])
        layout.addWidget(splitter)

        self.refresh_all_grids_from_sqlite()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLineEdit, QComboBox, QSpinBox { background-color: #161D26; border: 1px solid #232E3C; color: #FFFFFF; padding: 5px; font-size: 12px; border-radius: 2px; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 11px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QLabel#MetricText { font-family: "Segoe UI", monospace; font-size: 11px; color: #8A9BB0; background-color: #18222E; padding: 10px; border-left: 2px solid #D97706; line-height: 18px; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 7px; border-radius: 2px; }
            QPushButton#ActionBtn:hover { background-color: #007A66; }
            QPushButton#DangerBtn { background-color: #251820; color: #FF6B6B; border: 1px solid #3D222E; padding: 6px; border-radius: 2px; width: 100%; }
        """)

    def global_machinery_energy_consumption_tick(self):
        records = self.db.execute_query("SELECT node_id, fuel, status, vehicle_type FROM field_machinery")
        normal_nodes = 0
        low_nodes = 0

        for r in records:
            node_id, fuel, status, v_type = r
            if status == "加注中":
                fuel = min(100.0, round(fuel + 6.5, 2))
                if fuel >= 100.0:
                    status = "就绪"
            elif status == "故障异常":
                fuel = fuel 
            else:
                base_drag_loss = 0.003
                tool_power_loss = 0.005 if v_type in ["大马力收割机", "深翻地垦机"] else 0.002
                total_loss = base_drag_loss + tool_power_loss + random.uniform(0.001, 0.003)
                fuel = max(0.0, round(fuel - total_loss, 3))

            if fuel < 25.0:
                low_nodes += 1
            else:
                normal_nodes += 1

            self.db.execute_update("UPDATE field_machinery SET fuel=?, status=? WHERE node_id?", (fuel, status, node_id))

        self.pie_chart.update_energy_proportions(normal_nodes, low_nodes)
        self.refresh_grid_values_only()

    def refresh_all_grids_from_sqlite(self):
        """
        全面对齐 7 表结构的字段依赖关系检索
        """
        m_rows = self.db.execute_query("SELECT node_id, vehicle_type, fuel, status FROM field_machinery")
        self.machinery_table.setRowCount(len(m_rows))
        for r_idx, row in enumerate(m_rows):
            nid, v_type, fuel, status = row
            self.machinery_table.setItem(r_idx, 0, QTableWidgetItem(nid))
            self.machinery_table.setItem(r_idx, 1, QTableWidgetItem(v_type))
            self.machinery_table.setItem(r_idx, 2, QTableWidgetItem(f"{fuel:.1f}%"))
            self.machinery_table.setItem(r_idx, 3, QTableWidgetItem("常规排程" if fuel >= 25.0 else "特级强补充"))
            for c in range(4):
                self.machinery_table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.machinery_table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # 修复位置：全面对应 field_stations 的 6 个全量字段格式
        s_rows = self.db.execute_query("SELECT station_id, station_name, pos_x, pos_y, fuel_stock FROM field_stations")
        self.station_table.setRowCount(len(s_rows))
        for r_idx, row in enumerate(s_rows):
            sid, s_name, px, py, stock = row
            self.station_table.setItem(r_idx, 0, QTableWidgetItem(sid))
            self.station_table.setItem(r_idx, 1, QTableWidgetItem(s_name))
            self.station_table.setItem(r_idx, 2, QTableWidgetItem(f"({px:.3f}, {py:.3f})"))
            self.station_table.setItem(r_idx, 3, QTableWidgetItem(f"{int(stock)} 单元"))
            for c in range(4):
                self.station_table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.station_table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.refresh_grid_values_only()

    def refresh_grid_values_only(self):
        for r_idx in range(self.machinery_table.rowCount()):
            nid = self.machinery_table.item(r_idx, 0).text()
            res = self.db.execute_query("SELECT fuel, status FROM field_machinery WHERE node_id=?", (nid,))
            if res:
                fuel, status = res[0]
                self.machinery_table.item(r_idx, 2).setText(f"{fuel:.2f}%")
                p_item = self.machinery_table.item(r_idx, 3)
                if fuel < 25.0:
                    p_item.setText(f"特级强补充 ({status})")
                    p_item.setForeground(QColor("#D97706"))
                else:
                    p_item.setText(f"常规排程 ({status})")
                    p_item.setForeground(QColor("#00FFCC"))

        for r_idx in range(self.station_table.rowCount()):
            sid = self.station_table.item(r_idx, 0).text()
            res = self.db.execute_query("SELECT fuel_stock FROM field_stations WHERE station_id=?", (sid,))
            if res:
                stock = res[0][0]
                self.station_table.item(r_idx, 3).setText(f"{int(stock)} 单元")

    def handle_machinery_row_selection(self):
        selected = self.machinery_table.selectedRanges()
        if not selected: return
        self.selected_machinery_id = self.machinery_table.item(selected[0].topRow(), 0).text()
        self.lbl_dispatch_status.setText(f"已锁定待寻优机车目标: {self.selected_machinery_id}\n请一键下发就近能耗空间匹配决策。")

    def handle_station_row_selection(self):
        selected = self.station_table.selectedRanges()
        if not selected: return
        self.selected_station_id = self.station_table.item(selected[0].topRow(), 0).text()

    def execute_nearest_station_optimization_solver(self):
        if not self.selected_machinery_id:
            QMessageBox.warning(self, "调度拦截", "决策失败：请先在左上方选取需要实施紧急资源回补的目标机车编号。")
            return

        m_res = self.db.execute_query("SELECT current_x, current_y, fuel FROM field_machinery WHERE node_id=?", (self.selected_machinery_id,))
        if not m_res: return
        mx, my, m_fuel = m_res[0]

        if m_fuel >= 95.0:
            QMessageBox.information(self, "无需加注", "系统审计终止：该机车留存荷电率接近饱和状态，无需挤占加注带宽。")
            return

        stations = self.db.execute_query("SELECT station_id, station_name, pos_x, pos_y, fuel_stock FROM field_stations WHERE fuel_stock > 100")
        if not stations:
            self.lbl_dispatch_status.setText("算法熔断：全网加注资产储备告罄或无可用补给车点阵。")
            return

        best_station_id = None
        best_station_name = ""
        min_spatial_impedance = float('inf')

        for st in stations:
            sid, s_name, sx, sy, stock = st
            spatial_distance = math.sqrt((sx - mx)**2 + (sy - my)**2) * 1000.0
            stock_bonus = (stock / 5000.0) * 15.0
            total_impedance = spatial_distance - stock_bonus

            if total_impedance < min_spatial_impedance:
                min_spatial_impedance = total_impedance
                best_station_id = sid
                best_station_name = s_name

        if best_station_id:
            self.db.execute_update("UPDATE field_machinery SET status='加注中' WHERE node_id=?", (self.selected_machinery_id,))
            self.db.execute_update("UPDATE field_stations SET fuel_stock = max(0, fuel_stock - 150) WHERE station_id=?", (best_station_id,))
            
            self.lbl_dispatch_status.setText(
                f"决策成功！多维阻抗模型已闭合：\n"
                f"指派源: {best_station_name} [{best_station_id}]\n"
                f"前往加注目标: {self.selected_machinery_id}\n"
                f"解算空间路径阻抗代价: {min_spatial_impedance:.2f} 拓扑米\n"
                f"状态机联动：无线遥控链引导开始，进入逆向能耗回补程序。"
            )
            self.refresh_all_grids_from_sqlite()

    def sqlite_insert_station(self):
        sid = self.in_station_id.text().strip()
        if not sid: return
        
        dup = self.db.execute_query("SELECT COUNT(*) FROM field_stations WHERE station_id=?", (sid,))
        if dup and dup[0][0] > 0:
            QMessageBox.warning(self, "主键冲突", "该设备资产编号在 SQLite 持久层中已被占用。")
            return
            
        s_name = self.in_station_type.currentText()
        stock = self.in_station_stock.value()
        rx = 116.40 + random.uniform(-0.05, 0.05)
        ry = 39.90 + random.uniform(-0.05, 0.05)
        
        # 修复位置：插入数据对齐 6 个标准列结构
        status = self.db.execute_update("INSERT INTO field_stations VALUES (?, ?, ?, ?, ?, ?)",
                                        (sid, s_name, s_name, rx, ry, float(stock)))
        if status:
            self.refresh_all_grids_from_sqlite()
            self.in_station_id.clear()

    def sqlite_delete_station(self):
        if not self.selected_station_id:
            QMessageBox.warning(self, "析构阻断", "未在下方表格中捕捉到高亮选中的加注设备主键行。")
            return
            
        confirm = QMessageBox.question(self, "资产注销审计", f"是否将补给端主键 {self.selected_station_id} 从本调度系统资产链中物理注销清除？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            status = self.db.execute_update("DELETE FROM field_stations WHERE station_id=?", (self.selected_station_id,))
            if status:
                self.selected_station_id = None
                self.refresh_all_grids_from_sqlite()

    def get_module_title(self):
        return "05. 能耗与油料调度"