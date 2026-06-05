import math
import random
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QComboBox, QSplitter, QGroupBox, QHeaderView, QSlider)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from core.db_manager import AgronomicDatabaseCore

class DynamicTrackPlaybackMap(QWidget):
    """
    自研高精度时序轨迹动画复现测控大屏（底层QPainter重绘组件）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(280)
        self.raw_points = []       # 原始经纬度坐标序列
        self.interpolated_pts = [] # 插值算法解算后的高频动画粒子点
        self.current_index = 0     # 动画当前步进帧指针
        
    def load_track_payload(self, pts):
        """
        核心空间插值动力学算子：在低频离散点之间注入阻尼虚拟粒子，提升动画平滑度
        """
        self.raw_points = pts
        self.interpolated_pts = []
        self.current_index = 0
        
        if len(pts) < 2:
            self.interpolated_pts = pts
            self.update()
            return

        # 手写级线性粒子差分插值方程（每两点间强制平滑加密20帧）
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i+1]
            self.interpolated_pts.append(p1)
            
            steps = 20
            for s in range(1, steps):
                t = s / steps
                # 阻尼内插权重解算
                ix = p1[0] + (p2[0] - p1[0]) * t
                iy = p1[1] + (p2[1] - p1[1]) * t
                self.interpolated_pts.append((ix, iy))
                
        self.interpolated_pts.append(pts[-1])
        self.update()

    def advance_frame(self, speed_multiplier):
        """
        时钟驱动的指针前向跳进机制
        """
        if not self.interpolated_pts: 
            return
        self.current_index += speed_multiplier
        if self.current_index >= len(self.interpolated_pts):
            self.current_index = len(self.interpolated_pts) - 1
        self.update()

    def reset_playback(self):
        self.current_index = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # 1. 钛金黑工业控制台底盘与数字网格
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        grid_pen = QPen(QColor("#13202E"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        grid_step = 40
        for x in range(0, w, grid_step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid_step):
            painter.drawLine(0, y, w, y)

        if not self.interpolated_pts:
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.setPen(QColor("#6C7A8C"))
            painter.drawText(20, h - 20, "全局测控总线：等待从时序表中析构数据源进行渲染")
            return

        # 2. 坐标空间等比例归一化缩放（确保历史轨迹完美包络在可视区中央）
        xs = [p[0] for p in self.interpolated_pts]
        ys = [p[1] for p in self.interpolated_pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        range_x = (max_x - min_x) if max_x != min_x else 0.01
        range_y = (max_y - min_y) if max_y != min_y else 0.01
        
        # 3. 绘制整条历史路线轨迹包络线（暗荧光绿）
        route_poly = QPolygonF()
        for pt in self.interpolated_pts:
            rx = ((pt[0] - min_x) / range_x - 0.5) * (w * 0.7) + w / 2
            ry = ((pt[1] - min_y) / range_y - 0.5) * (h * 0.7) + h / 2
            route_poly.append(QPointF(rx, ry))

        painter.setPen(QPen(QColor(0, 255, 204, 80), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(route_poly)

        # 4. 突出标记原始经纬度上报节点（实心蓝圆）
        painter.setBrush(QBrush(QColor("#00E5FF")))
        for pt in self.raw_points:
            rx = ((pt[0] - min_x) / range_x - 0.5) * (w * 0.7) + w / 2
            ry = ((pt[1] - min_y) / range_y - 0.5) * (h * 0.7) + h / 2
            painter.setPen(QPen(QColor("#0A0E14"), 1))
            painter.drawEllipse(QPointF(rx, ry), 4, 4)

        # 5. 核心：渲染当前正运行播放的时间轴粒子动画节点（亮黄星）
        if 0 <= self.current_index < len(route_poly):
            current_pos = route_poly[self.current_index]
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(QBrush(QColor("#F59E0B"))) # 亮橙粒子
            painter.drawEllipse(current_pos, 8, 8)
            
            # 附带环绕动圈效果
            painter.setPen(QPen(QColor(245, 158, 11, 100), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(current_pos, 14, 14)

        # 6. 信息抬头
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor("#00FFCC"))
        pct = (self.current_index / (len(self.interpolated_pts) - 1)) * 100.0 if len(self.interpolated_pts) > 1 else 0
        painter.drawText(15, 25, f"高高精时序测控盘：数字解算轨迹重现进度 {pct:.1f}%")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_node_id = None
        self.playback_speed = 1
        self.db = AgronomicDatabaseCore()
        
        self.apply_internal_style()
        self.init_ui_components()
        
        # 独立高频动画重绘引擎时钟（30帧/秒标准工业显卡同步）
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.global_trajectory_playback_animation_step_tick)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 区域一：多功能时序快进与控制盒
        ctrl_box = QGroupBox("时序大数据轨迹复现硬交互多控中心")
        ctrl_box.setObjectName("CtrlBox")
        ctrl_layout = QHBoxLayout(ctrl_box)
        ctrl_layout.setSpacing(12)

        ctrl_layout.addWidget(QLabel("快进速率调谐:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1倍 标准速率基准", "2倍 边缘压缩速率", "4倍 高速时空推演", "8倍 宏观极限跨度"])
        self.speed_combo.currentIndexChanged.connect(self.handle_speed_multiplier_change)
        ctrl_layout.addWidget(self.speed_combo, stretch=1)

        btn_play = QPushButton("开启数字链路播放")
        btn_play.setObjectName("ActionBtn")
        btn_play.clicked.connect(self.start_playback_sequence)
        ctrl_layout.addWidget(btn_play)

        btn_pause = QPushButton("暂停时空步进")
        btn_pause.setObjectName("WarningBtn")
        btn_pause.clicked.connect(self.pause_playback_sequence)
        ctrl_layout.addWidget(btn_pause)

        btn_reset = QPushButton("指令重置回零位")
        btn_reset.setObjectName("ResumeBtn")
        btn_reset.clicked.connect(self.reset_playback_sequence)
        ctrl_layout.addWidget(btn_reset)

        layout.addWidget(ctrl_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        # 区域二：左面板-数据表及擦除功能（CRUD之读/删）
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("已捕获存在历史空间时序轨迹链的无人农机实体"))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["农机主键标识", "当前运行工况", "累计抓取离散微元数"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.handle_machinery_row_selection)
        left_layout.addWidget(self.table)

        btn_purge = QPushButton("对选中节点的历史时序冗余行执行标准擦除 (数据表清洗)")
        btn_purge.setObjectName("DangerBtn")
        btn_purge.clicked.connect(self.sqlite_delete_historical_tracks_by_node)
        left_layout.addWidget(btn_purge)

        # 区域三：右面板-粒子画布
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        radar_group = QGroupBox("基于北斗时空位置线索的三维平面直角投影动画复现大屏")
        rg_layout = QVBoxLayout(radar_group)
        self.playback_screen = DynamicTrackPlaybackMap()
        rg_layout.addWidget(self.playback_screen)
        right_layout.addWidget(radar_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([550, 510])
        layout.addWidget(splitter)

        self.refresh_track_host_table_view_from_sqlite()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLineEdit, QComboBox { background-color: #161D26; border: 1px solid #232E3C; color: #FFFFFF; padding: 5px; font-size: 12px; border-radius: 2px; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 11px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 6px 14px; border-radius: 2px; }
            QPushButton#ActionBtn:hover { background-color: #007A66; }
            QPushButton#WarningBtn { background-color: #5C3E14; color: #FFAA00; border: 1px solid #7C5317; font-weight: bold; padding: 6px 14px; border-radius: 2px; }
            QPushButton#WarningBtn:hover { background-color: #7C5317; }
            QPushButton#ResumeBtn { background-color: #1A3043; color: #38BDF8; border: 1px solid #254563; font-weight: bold; padding: 6px 14px; border-radius: 2px; }
            QPushButton#DangerBtn { background-color: #251820; color: #FF6B6B; border: 1px solid #3D222E; font-weight: bold; padding: 7px; border-radius: 2px; width: 100%; }
        """)

    def global_trajectory_playback_animation_step_tick(self):
        """
        高频动画时钟演进算子
        """
        self.playback_screen.advance_frame(self.playback_speed)
        
        # 边界终结保护：如果动画粒子跑到头，自动挂起时钟
        scr = self.playback_screen
        if scr.current_index >= len(scr.interpolated_pts) - 1:
            self.playback_timer.stop()

    def refresh_track_host_table_view_from_sqlite(self):
        """
        联合分布式检索：查出所有在时序表中有物理行存储的农机记录（查）
        """
        sql = """
            SELECT DISTINCT m.node_id, m.status, COUNT(t.track_id) 
            FROM field_machinery m
            JOIN field_historical_tracks t ON m.node_id = t.node_id
            GROUP BY m.node_id
        """
        rows = self.db.execute_query(sql)
        self.table.setRowCount(len(rows))
        
        for r_idx, row in enumerate(rows):
            nid, status, count = row
            self.table.setItem(r_idx, 0, QTableWidgetItem(nid))
            self.table.setItem(r_idx, 1, QTableWidgetItem(status))
            self.table.setItem(r_idx, 2, QTableWidgetItem(f"{count} 帧物理节点"))
            
            for c in range(3):
                self.table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def handle_machinery_row_selection(self):
        selected = self.table.selectedRanges()
        if not selected: return
        row = selected[0].topRow()
        self.selected_node_id = self.table.item(row, 0).text()
        
        # 从 SQLite 时序表中全量抓取当前车辆的按时间排序的全部历史平面坐标
        track_rows = self.db.execute_query("""
            SELECT pos_x, pos_y FROM field_historical_tracks 
            WHERE node_id=? ORDER BY recorded_time ASC
        """, (self.selected_node_id,))
        
        if track_rows:
            # 灌入自研画布，自动触发粒子内插动力学解算
            self.playback_screen.load_track_payload(track_rows)

    def handle_speed_multiplier_change(self, index):
        # 动态快进控制矩阵
        multipliers = [1, 2, 4, 8]
        self.playback_speed = multipliers[index]

    def start_playback_sequence(self):
        if self.selected_node_id and self.playback_screen.interpolated_pts:
            self.playback_timer.start(33) # 逼近30帧每秒的电影级视觉重绘

    def pause_playback_sequence(self):
        self.playback_timer.stop()

    def reset_playback_sequence(self):
        self.playback_timer.stop()
        self.playback_screen.reset_playback()

    def sqlite_delete_historical_tracks_by_node(self):
        """
        时序大数据管理交互之【删】：清除冗余时序行，优化空间开销
        """
        if not self.selected_node_id:
            return
            
        confirm = QMessageBox.question(self, "数据链清除确认", f"是否将机车 {self.selected_node_id} 的全部历史时序轨迹块从SQLite磁盘中永久粉碎？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.playback_timer.stop()
            # 提交清除事务
            status = self.db.execute_update("DELETE FROM field_historical_tracks WHERE node_id=?", (self.selected_node_id,))
            if status:
                self.playback_screen.load_track_payload([])
                self.refresh_track_host_table_view_from_sqlite()

    def get_module_title(self):
        return "07. 历史轨迹回放"