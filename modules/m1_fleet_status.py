import math
import random
import time
from collections import deque
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHBoxLayout, QPushButton, QMessageBox, QLabel, 
                             QLineEdit, QComboBox, QSplitter, QGroupBox, 
                             QProgressBar, QHeaderView, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from core.db_manager import AgronomicDatabaseCore

class GaussKrugerProjector:
    """
    手写级北斗大地坐标（WGS-84经纬度）至中央子午线平面直角坐标系（高斯-克吕格偏置）解算算法模型
    """
    def __init__(self, center_lon=116.5):
        self.center_lon = math.radians(center_lon)
        self.a = 6378137.0         
        self.b = 6356752.3142      
        self.f = (self.a - self.b) / self.a
        self.e2 = (self.a**2 - self.b**2) / (self.a**2)

    def project_wgs84_to_xy(self, lon, lat):
        """
        核心物理转换公式：解算农机空间相对米级位移偏移量
        """
        rad_lon = math.radians(lon)
        rad_lat = math.radians(lat)
        
        delta_lon = rad_lon - self.center_lon
        sin_lat = math.sin(rad_lat)
        cos_lat = math.cos(rad_lat)
        tan_lat = math.tan(rad_lat)
        
        N = self.a / math.sqrt(1.0 - self.e2 * (sin_lat**2))
        t = tan_lat**2
        eta2 = (self.e2 / (1.0 - self.e2)) * (cos_lat**2)
        
        A = 1.0 + (3.0/4.0)*self.e2 + (45.0/64.0)*(self.e2**2)
        B = (3.0/4.0)*self.e2 + (15.0/16.0)*(self.e2**2)
        C = (15.0/32.0)*(self.e2**2)
        
        X_arc = self.a * (A * rad_lat - B * sin_lat * cos_lat - C * sin_lat * (cos_lat**3))
        
        x_coord = X_arc + (N/2.0)*sin_lat*cos_lat*(delta_lon**2) + (N/24.0)*sin_lat*(cos_lat**3)*(5.0 - t + 9.0*eta2)*(delta_lon**4)
        y_coord = N*cos_lat*delta_lon + (N/6.0)*(cos_lat**3)*(1.0 - t + eta2)*(delta_lon**3)
        
        return round(x_coord, 3), round(y_coord, 3)


class CanBusJ1939ProtocolParser:
    """
    工业级SAE J1939车载CAN总线原始数据链路层协议明文解包封装器
    """
    @staticmethod
    def construct_raw_frame(pgn, source_address, data_bytes):
        """
        将仿真传感器状态字节矩阵序列化为标准16进制物理层报文
        """
        timestamp = time.strftime("%H:%M:%S")
        can_id = f"18{pgn:04X}{source_address:02X}"
        hex_data = " ".join(f"{b:02X}" for b in data_bytes)
        return f"[{timestamp}]  帧标识: 0x{can_id}  数据流: {hex_data}"


class RealTimeOscilloscope(QWidget):
    """
    高精度双通道自适应网格遥测曲线图表（底层重绘）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.buffer_a = deque([60.0] * 60, maxlen=60)   
        self.buffer_b = deque([-65.0] * 60, maxlen=60)  
        self.max_val_a = 100.0
        self.min_val_a = 40.0
        self.max_val_b = -40.0
        self.min_val_b = -95.0

    def append_data(self, val_a, val_b):
        self.buffer_a.append(val_a)
        self.buffer_b.append(val_b)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor("#0A0F14"))
        
        grid_pen = QPen(QColor("#15202C"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        
        total_time_ticks = 12
        for i in range(1, total_time_ticks):
            x = int(w * i / total_time_ticks)
            painter.drawLine(x, 0, x, h)
            
        total_value_ticks = 5
        painter.setFont(QFont("Consolas", 7))
        for i in range(total_value_ticks):
            y = int((h - 30) * i / (total_value_ticks - 1)) + 15
            painter.setPen(grid_pen)
            painter.drawLine(0, y, w, y)
            
            val_scale_a = self.max_val_a - (i * (self.max_val_a - self.min_val_a) / (total_value_ticks - 1))
            painter.setPen(QColor("#558B2F"))
            painter.drawText(w - 45, y - 3, f"{val_scale_a:.1f}兆帕")

        if len(self.buffer_a) < 2: 
            return

        step_width = w / 59.0
        
        pen_a = QPen(QColor("#00FF66"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen_a)
        for i in range(len(self.buffer_a) - 1):
            y1 = h - int((self.buffer_a[i] - self.min_val_a) / (self.max_val_a - self.min_val_a) * (h - 30)) - 15
            y2 = h - int((self.buffer_a[i+1] - self.min_val_a) / (self.max_val_a - self.min_val_a) * (h - 30)) - 15
            painter.drawLine(QPointF(i * step_width, y1), QPointF((i + 1) * step_width, y2))
            
        pen_b = QPen(QColor("#00E5FF"), 1.5, Qt.PenStyle.SolidLine)
        painter.setPen(pen_b)
        for i in range(len(self.buffer_b) - 1):
            y1 = h - int((self.buffer_b[i] - self.min_val_b) / (self.max_val_b - self.min_val_b) * (h - 30)) - 15
            y2 = h - int((self.buffer_b[i+1] - self.min_val_b) / (self.max_val_b - self.min_val_b) * (h - 30)) - 15
            painter.drawLine(QPointF(i * step_width, y1), QPointF((i + 1) * step_width, y2))

        painter.setFont(QFont("Microsoft YaHei", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#00FF66"))
        painter.drawText(15, 25, "通道一: 主液压泵反馈压 (动态波形)")
        painter.setPen(QColor("#00E5FF"))
        painter.drawText(220, 25, "通道二: 北斗差分授时信号载噪比")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_node_id = None
        self.display_rows = []
        self.db = AgronomicDatabaseCore() 
        self.projector = GaussKrugerProjector() 
        self.apply_internal_style()
        self.init_ui_components()
        
        self.bus_timer = QTimer(self)
        self.bus_timer.timeout.connect(self.global_telemetry_bus_tick)
        self.bus_timer.start(1000)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 顶部高级功能交互区：接入向导与多维检索
        top_ctrl_box = QGroupBox("全新机车节点动态准入控制中枢（满足选择类型与强关系交互）")
        top_ctrl_box.setObjectName("TopCtrlBox")
        top_ctrl_layout = QHBoxLayout(top_ctrl_box)
        top_ctrl_layout.setSpacing(12)

        top_ctrl_layout.addWidget(QLabel("准入编号:"))
        self.input_new_id = QLineEdit()
        self.input_new_id.setPlaceholderText("例如: 机车-09")
        top_ctrl_layout.addWidget(self.input_new_id, stretch=1)

        top_ctrl_layout.addWidget(QLabel("机型分配:"))
        self.combo_new_type = QComboBox()
        self.combo_new_type.addItems(["大马力收割机", "高精度播种机", "植保喷药机", "深翻地垦机"])
        top_ctrl_layout.addWidget(self.combo_new_type, stretch=1)

        add_btn = QPushButton("下发准入数据链")
        add_btn.setObjectName("ActionBtn")
        add_btn.clicked.connect(self.sqlite_insert_node)
        top_ctrl_layout.addWidget(add_btn, stretch=1)

        # 检索功能平移并入顶部
        top_ctrl_layout.addSpacing(20)
        top_ctrl_layout.addWidget(QLabel("多维条件筛查:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("键入编号主键执行匹配...")
        self.search_input.textChanged.connect(self.refresh_table_view_from_sqlite)
        top_ctrl_layout.addWidget(self.search_input, stretch=2)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["全部机型分类", "大马力收割机", "高精度播种机", "植保喷药机", "深翻地垦机"])
        self.type_combo.currentIndexChanged.connect(self.refresh_table_view_from_sqlite)
        top_ctrl_layout.addWidget(self.type_combo, stretch=1)

        layout.addWidget(top_ctrl_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        # 左面板：关系表格面板布局
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        section_lbl = QLabel("全网分布式无人农机实时链路状况网格")
        section_lbl.setObjectName("SectionLabel")
        left_layout.addWidget(section_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["农机主键", "机型分类", "工况安全边界", "高斯平面直角坐标 (米)", "电池剩余电量"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.handle_row_selection)
        left_layout.addWidget(self.table)

        # 关系型底层变更控制层（删除控制）
        bottom_ctrl_layout = QHBoxLayout()
        del_btn = QPushButton("强行断开并剔除物理通道数据链")
        del_btn.setObjectName("DangerBtn")
        del_btn.clicked.connect(self.sqlite_delete_node)
        bottom_ctrl_layout.addWidget(del_btn)
        left_layout.addLayout(bottom_ctrl_layout)
        
        # 右面板：高级高信息密度遥测中枢
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)
        
        telemetry_group = QGroupBox("当前活动操作链车载总线物理流解算")
        telemetry_group.setObjectName("TelemetryGroup")
        tg_layout = QVBoxLayout(telemetry_group)
        tg_layout.setSpacing(6)
        
        self.node_info_lbl = QLabel("未联通数据探针，请在左侧指定行发起硬握手")
        self.node_info_lbl.setStyleSheet("color: #6C7A8C; font-weight: bold; font-size: 11px;")
        tg_layout.addWidget(self.node_info_lbl)
        
        self.rpm_lbl = QLabel("动力总成转速解算: -- 转/分")
        self.temp_lbl = QLabel("主传动系统油温核心感知: -- 摄氏度")
        self.sat_lbl = QLabel("北斗空间交会锁定可用卫星: -- 颗")
        self.pressure_lbl = QLabel("主泵负载液压流阀值: -- 兆帕")
        
        for lbl in [self.rpm_lbl, self.temp_lbl, self.sat_lbl, self.pressure_lbl]:
            lbl.setObjectName("MetricText")
            tg_layout.addWidget(lbl)
            
        tg_layout.addWidget(QLabel("全车主能耗电量留存率:"))
        self.fuel_bar = QProgressBar()
        self.fuel_bar.setRange(0, 100)
        tg_layout.addWidget(self.fuel_bar)
        right_layout.addWidget(telemetry_group)

        # 图形渲染与报文审计监控面板
        chart_group = QGroupBox("时空拓扑数据链：高频双通道遥测实时曲线")
        chart_group.setObjectName("ChartGroup")
        cg_layout = QVBoxLayout(chart_group)
        
        self.oscilloscope = RealTimeOscilloscope()
        cg_layout.addWidget(self.oscilloscope)
        
        cg_layout.addWidget(QLabel("车载总线底层原始报文协议监听流:"))
        self.raw_hex_logger = QTextEdit()
        self.raw_hex_logger.setReadOnly(True)
        self.raw_hex_logger.setObjectName("RawHexLogger")
        cg_layout.addWidget(self.raw_hex_logger)
        
        # 故障状态双向演进按钮区
        fault_ctrl_layout = QHBoxLayout()
        fault_ctrl_layout.setSpacing(10)

        inject_fault_btn = QPushButton("模拟注入突发物理故障")
        inject_fault_btn.setObjectName("InjectBtn")
        inject_fault_btn.clicked.connect(self.sqlite_update_fault)

        recover_fault_btn = QPushButton("下发无线清错恢复就绪指令")
        recover_fault_btn.setObjectName("RecoverBtn")
        recover_fault_btn.clicked.connect(self.sqlite_recover_normal)

        fault_ctrl_layout.addWidget(inject_fault_btn)
        fault_ctrl_layout.addWidget(recover_fault_btn)
        cg_layout.addLayout(fault_ctrl_layout)
        
        right_layout.addWidget(chart_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([610, 490])
        layout.addWidget(splitter)
        
        self.refresh_table_view_from_sqlite()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QLabel#SectionLabel { font-size: 13px; font-weight: bold; color: #00FFCC; }
            QLabel#ControlLabel { font-weight: bold; color: #8A9BB0; font-size: 12px; }
            QLineEdit, QComboBox { background-color: #161D26; border: 1px solid #232E3C; border-radius: 2px; padding: 5px 8px; color: #FFFFFF; font-size: 12px; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #00FFCC; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 12px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 8px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; margin-top: 5px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 12px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLabel#MetricText { font-family: "Consolas", monospace; font-size: 11px; color: #E2E8F0; background-color: #18222E; padding: 5px; border-left: 2px solid #3F4C5E; }
            QProgressBar { border: 1px solid #232E3C; background-color: #161D26; text-align: center; color: #FFFFFF; font-weight: bold; font-size: 11px; height: 16px; border-radius: 2px; }
            QProgressBar::chunk { background-color: #007A66; }
            QTextEdit#RawHexLogger { background-color: #0A0E14; border: 1px solid #1F2936; color: #F59E0B; font-family: "Consolas", monospace; font-size: 10px; min-height: 70px; max-height: 90px; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; padding: 6px 12px; font-weight: bold; border-radius: 2px; font-size: 12px; }
            QPushButton#ActionBtn:hover { background-color: #007A66; }
            QPushButton#DangerBtn { background-color: #251820; color: #FF6B6B; border: 1px solid #3D222E; padding: 8px 12px; font-weight: bold; border-radius: 2px; font-size: 12px; width: 100%; }
            QPushButton#DangerBtn:hover { background-color: #3D222E; }
            QPushButton#InjectBtn { background-color: #451A1A; color: #FFA3A3; border: 1px solid #632323; font-size: 11px; padding: 6px; border-radius: 2px; }
            QPushButton#InjectBtn:hover { background-color: #632323; }
            QPushButton#RecoverBtn { background-color: #1A352B; color: #A3F5D1; border: 1px solid #234E3D; font-size: 11px; padding: 6px; border-radius: 2px; }
            QPushButton#RecoverBtn:hover { background-color: #234E3D; }
        """)

    def global_telemetry_bus_tick(self):
        """
        核心数据动力学进化链：周期化演算并同步重写本地关系型存储库
        """
        try:
            records = self.db.execute_query("SELECT * FROM field_machinery")
            for r in records:
                node_id, v_type, status, cx, cy, fuel, rpm, temp, press, sats = r
                
                if status == "故障异常":
                    rpm = max(700, rpm - 35)
                    press = max(6.5, press - 2.2)
                    temp = min(99.0, temp + 0.6)
                else:
                    heading = random.randint(0, 359)
                    rad = math.radians(heading)
                    cx += (4.0 * 0.000008) * math.cos(rad)
                    cy += (4.0 * 0.000008) * math.sin(rad)
                    fuel = max(0.0, round(fuel - 0.003, 3))
                    rpm = int(1660 + 25 * math.sin(time.time()))
                    press = round(64.2 + random.uniform(-1.5, 1.5), 2)
                    temp = round(62.1 + random.uniform(-0.3, 0.3), 2)
                    
                    if random.randint(0, 10) == 5:
                        sats = max(12, min(24, sats + random.choice([-1, 1])))

                self.db.execute_update("""
                    UPDATE field_machinery 
                    SET current_x=?, current_y=?, fuel=?, engine_rpm=?, hydraulic_temp=?, pump_pressure=?, satellites=? 
                    WHERE node_id=?
                """, (cx, cy, fuel, rpm, temp, press, sats, node_id))

            self.refresh_table_values_only()
            
            if self.selected_node_id:
                res = self.db.execute_query("SELECT engine_rpm, hydraulic_temp, pump_pressure, status FROM field_machinery WHERE node_id=?", (self.selected_node_id,))
                if res:
                    c_rpm, c_temp, c_press, c_status = res[0]
                    
                    byte1 = int(c_rpm / 0.25) & 0xFF
                    byte2 = (int(c_rpm / 0.25) >> 8) & 0xFF
                    byte3 = int(c_temp + 40) & 0xFF
                    byte4 = int(c_press / 0.4) & 0xFF
                    dummy_bytes = [0x7F, byte1, byte2, byte3, byte4, 0x00, 0xFF, 0xAA]
                    
                    raw_frame_str = CanBusJ1939ProtocolParser.construct_raw_frame(0xFEF6, 0x1A, dummy_bytes)
                    self.raw_hex_logger.append(raw_frame_str)
                    if self.raw_hex_logger.document().blockCount() > 20:
                        self.raw_hex_logger.clear()
                        
                    pseudo_rssi = -64.0 + random.uniform(-5.0, 5.0) if c_status != "故障异常" else -94.0
                    self.oscilloscope.append_data(c_press, pseudo_rssi)
                    
                self.update_active_telemetry_panel()
        except Exception as e:
            print(f"数据总线时钟同步异常阻断: {e}")

    def refresh_table_view_from_sqlite(self):
        """
        关系型二维网格条件过滤检索
        """
        search_kw = self.search_input.text().strip()
        type_filter = self.type_combo.currentText()

        sql = "SELECT node_id, vehicle_type, status, current_x, current_y, fuel FROM field_machinery WHERE 1=1"
        params = []
        if search_kw:
            sql += " AND node_id LIKE ?"
            params.append(f"%{search_kw}%")
        if type_filter != "全部机型分类":
            sql += " AND vehicle_type = ?"
            params.append(type_filter)

        self.display_rows = self.db.execute_query(sql, params)
        self.table.setRowCount(len(self.display_rows))
        
        for r_idx, row in enumerate(self.display_rows):
            node_id, v_type, status, cx, cy, fuel = row
            gx, gy = self.projector.project_wgs84_to_xy(cx, cy)
            
            self.table.setItem(r_idx, 0, QTableWidgetItem(node_id))
            self.table.setItem(r_idx, 1, QTableWidgetItem(v_type))
            self.table.setItem(r_idx, 2, QTableWidgetItem(status))
            self.table.setItem(r_idx, 3, QTableWidgetItem(f"横:{gx:.1f}, 纵:{gy:.1f}"))
            self.table.setItem(r_idx, 4, QTableWidgetItem(f"{int(fuel)}%"))
            
            for c in range(5):
                self.table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh_table_values_only()

    def refresh_table_values_only(self):
        for r_idx in range(self.table.rowCount()):
            node_id = self.table.item(r_idx, 0).text()
            res = self.db.execute_query("SELECT status, current_x, current_y, fuel FROM field_machinery WHERE node_id=?", (node_id,))
            if res:
                status, cx, cy, fuel = res[0]
                gx, gy = self.projector.project_wgs84_to_xy(cx, cy)
                
                status_item = self.table.item(r_idx, 2)
                status_item.setText(status)
                if status == "故障异常":
                    status_item.setForeground(QColor("#FF4D4D"))
                elif fuel < 20.0:
                    status_item.setForeground(QColor("#FFAA00"))
                else:
                    status_item.setForeground(QColor("#00FFCC"))
                    
                self.table.item(r_idx, 3).setText(f"横:{gx:.1f}, 纵:{gy:.1f}")
                self.table.item(r_idx, 4).setText(f"{fuel:.1f}%")

    def handle_row_selection(self):
        selected = self.table.selectedRanges()
        if not selected: 
            return
        self.selected_node_id = self.table.item(selected[0].topRow(), 0).text()
        self.update_active_telemetry_panel()

    def update_active_telemetry_panel(self):
        if not self.selected_node_id: 
            return
        res = self.db.execute_query("SELECT * FROM field_machinery WHERE node_id=?", (self.selected_node_id,))
        if res:
            _, v_type, _, _, _, fuel, rpm, temp, press, sats = res[0]
            self.node_info_lbl.setText(f"总线探针物理硬同步主键: {self.selected_node_id} [{v_type}]")
            self.rpm_lbl.setText(f"动力总成转速解算: {rpm} 转/分")
            self.temp_lbl.setText(f"主传动系统油温核心感知: {temp} 摄氏度")
            self.sat_lbl.setText(f"北斗空间交会锁定可用卫星: {sats} 颗")
            self.pressure_lbl.setText(f"主泵负载液压流阀值: {press} 兆帕")
            self.fuel_bar.setValue(int(fuel))

            if fuel < 25:
                self.fuel_bar.setStyleSheet("QProgressBar::chunk { background-color: #E63946; }")
            else:
                self.fuel_bar.setStyleSheet("QProgressBar::chunk { background-color: #008066; }")

    def sqlite_insert_node(self):
        """
        数据持久层管理：自主指派机种与编号接入 (INSERT)
        """
        raw_id = self.input_new_id.text().strip()
        if not raw_id:
            QMessageBox.warning(self, "下发终止", "请输入规范的机车节点注册编号。")
            return
            
        dup_query = self.db.execute_query("SELECT COUNT(*) FROM field_machinery WHERE node_id=?", (raw_id,))
        if dup_query[0][0] > 0: 
            QMessageBox.warning(self, "准入冲突", "该编号主键在数据库阵列中已存在，拒绝重复并网。")
            return
            
        selected_category = self.combo_new_type.currentText()
        rx = 116.40 + random.uniform(-0.04, 0.04)
        ry = 39.90 + random.uniform(-0.04, 0.04)
        
        status = self.db.execute_update("""
            INSERT INTO field_machinery VALUES (?, ?, '就绪', ?, ?, 100.0, 1660, 57.0, 61.5, 18)
        """, (raw_id, selected_category, rx, ry))
        
        if status:
            self.refresh_table_view_from_sqlite()
            self.input_new_id.clear()

    def sqlite_delete_node(self):
        """
        数据持久层管理：断开注销记录 (DELETE)
        """
        if not self.selected_node_id:
            QMessageBox.warning(self, "事务终止", "网格阵列内未捕捉到活跃高亮的物理实体主键行。")
            return
            
        verify = QMessageBox.question(self, "物理析构确认", f"是否将底层节点 {self.selected_node_id} 从本地存储库中强行熔断并抹除？",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if verify == QMessageBox.StandardButton.Yes:
            self.db.execute_update("DELETE FROM field_machinery WHERE node_id=?", (self.selected_node_id,))
            self.selected_node_id = None
            self.node_info_lbl.setText("未联通数据探针，请在左侧指定行发起硬握手")
            self.refresh_table_view_from_sqlite()

    def sqlite_update_fault(self):
        """
        数据持久层管理：故障突变干预 (UPDATE)
        """
        if not self.selected_node_id:
            QMessageBox.warning(self, "干预挂起", "请在网格中选定特定硬件节点作为注入目标。")
            return
        self.db.execute_update("UPDATE field_machinery SET status='故障异常' WHERE node_id=?", (self.selected_node_id,))
        self.refresh_table_values_only()

    def sqlite_recover_normal(self):
        """
        数据持久层管理：一键恢复正常状态机并清洗故障 (UPDATE)
        """
        if not self.selected_node_id:
            return
        # 重设正常状态机，复位传动油温与液压阀基准值
        self.db.execute_update("""
            UPDATE field_machinery SET status='就绪', engine_rpm=1650, hydraulic_temp=60.0, pump_pressure=64.0 WHERE node_id=?
        """, (self.selected_node_id,))
        self.refresh_table_values_only()

    def get_module_title(self):
        return "01. 农机实时状态监控"