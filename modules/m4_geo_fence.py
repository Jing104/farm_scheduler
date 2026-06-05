import math
import random
import time
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QLineEdit, QComboBox, QSplitter, QGroupBox, 
                             QHeaderView, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from core.db_manager import AgronomicDatabaseCore

class SpatialRayCastingEngine:
    """
    基于射线交叉法（Ray-Casting）的点在多边形内（PIP）越界冲突判定算法
    """
    @staticmethod
    def is_point_in_polygon(x, y, polygon_points):
        n = len(polygon_points)
        if n < 3: 
            return False
            
        inside = False
        p1x, p1y = polygon_points[0]
        
        for i in range(n + 1):
            p2x, p2y = polygon_points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside


class VectorGeoFenceMap(QWidget):
    """
    矢量电子围栏多维立体测控视场看板（底层QPainter重绘组件）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.machinery_list = []  
        self.safe_zone_poly = []  
        self.danger_zones = {}     
        self.scan_pulse = 0.0
        
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._advance_radar_pulse)
        self.pulse_timer.start(40)

    def update_spatial_vectors(self, machinery, safe_zone, dangers):
        self.machinery_list = machinery
        self.safe_zone_poly = safe_zone
        self.danger_zones = dangers
        self.update()

    def _advance_radar_pulse(self):
        self.scan_pulse = (self.scan_pulse + 2.0) % 100.0
        if self.machinery_list:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        grid_pen = QPen(QColor("#13202E"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        grid_step = 40
        for x in range(0, w, grid_step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid_step):
            painter.drawLine(0, y, w, y)

        if self.safe_zone_poly:
            safe_poly = QPolygonF()
            for pt in self.safe_zone_poly:
                safe_poly.append(QPointF(pt[0], pt[1]))
            painter.setPen(QPen(QColor("#2E7D32"), 1.5, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(QColor(46, 125, 50, 8)))
            painter.drawPolygon(safe_poly)

        for f_id, pts in self.danger_zones.items():
            danger_poly = QPolygonF()
            for pt in pts:
                danger_poly.append(QPointF(pt[0], pt[1]))
            painter.setPen(QPen(QColor("#C62828"), 1.5, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(QColor(198, 40, 40, 25)))
            painter.drawPolygon(danger_poly)
            
            painter.setPen(QColor("#EF9A9A"))
            # 修复位置：确保QFont初始化时明确给定合法的像素大小，彻底消除底层警告
            fixed_font = QFont("Consolas")
            fixed_font.setPixelSize(11)
            painter.setFont(fixed_font)
            if danger_poly.count() > 0:
                painter.drawText(danger_poly[0] + QPointF(-10, -5), f_id)

        for nid, mx, my, is_breached in self.machinery_list:
            if is_breached:
                painter.setPen(QPen(QColor(239, 68, 68, int(255 * (1.0 - self.scan_pulse / 100.0))), 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(mx, my), self.scan_pulse * 0.3, self.scan_pulse * 0.3)
                
                painter.setPen(QPen(QColor("#EF4444"), 2))
                painter.setBrush(QBrush(QColor("#991B1B")))
            else:
                painter.setPen(QPen(QColor("#00FFCC"), 1.5))
                painter.setBrush(QBrush(QColor("#005F50")))
                
            painter.drawEllipse(QPointF(mx, my), 6, 6)
            painter.setPen(QColor("#E2E8F0"))
            
            text_font = QFont("Consolas")
            text_font.setPixelSize(11)
            painter.setFont(text_font)
            painter.drawText(QPointF(mx + 10, my + 4), nid)

        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.setPen(QColor("#00FFCC"))
        painter.drawText(15, 25, "安全主轴：多维矢量电子围栏控制看板")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_fence_id = None
        self.display_rows = []
        self.db = AgronomicDatabaseCore()
        
        self.apply_internal_style()
        self.init_ui_components()
        
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.global_ray_casting_spatial_scan)
        self.scan_timer.start(1000)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        wizard_box = QGroupBox("智能化危险阻断红线隔离带划定中枢（SQLite 数据强持久层）")
        wizard_box.setObjectName("WizardBox")
        wizard_layout = QHBoxLayout(wizard_box)
        wizard_layout.setSpacing(12)

        wizard_layout.addWidget(QLabel("禁区唯一主键:"))
        self.in_fence_id = QLineEdit()
        self.in_fence_id.setPlaceholderText("例如: 红线禁区-三号")
        wizard_layout.addWidget(self.in_fence_id, stretch=1)

        wizard_layout.addWidget(QLabel("空间几何分类:"))
        self.in_fence_type = QComboBox()
        self.in_fence_type.addItems(["高压输电线杆防护带", "深水排灌渠高危区", "地表重度沉降陷落带"])
        wizard_layout.addWidget(self.in_fence_type, stretch=2)

        commit_btn = QPushButton("下发同步并写入本地数据库")
        commit_btn.setObjectName("ActionBtn")
        commit_btn.clicked.connect(self.sqlite_insert_geo_fence)
        wizard_layout.addWidget(commit_btn, stretch=1)

        layout.addWidget(wizard_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("系统当前从数据库（SQLite）加载的有向封闭空间隔离网"))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["隔离网持久化主键", "隔离带几何属性", "拓扑闭合特征顶点数"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.handle_fence_selection)
        left_layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()
        btn_remove = QPushButton("从关系型数据库中物理清除并注销该隔离带记录")
        btn_remove.setObjectName("DangerBtn")
        btn_remove.clicked.connect(self.sqlite_delete_geo_fence)
        bottom_layout.addWidget(btn_remove)
        left_layout.addLayout(bottom_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        radar_group = QGroupBox("全网在线机车相对轴矢量位置与持久化多边形围栏态势图")
        rg_layout = QVBoxLayout(radar_group)
        self.vector_map = VectorGeoFenceMap()
        rg_layout.addWidget(self.vector_map)
        right_layout.addWidget(radar_group)

        log_group = QGroupBox("时空交叉射线相交算法（Ray-Casting）高频侵入审计日志流")
        lg_layout = QVBoxLayout(log_group)
        self.audit_logs = QTextEdit()
        self.audit_logs.setReadOnly(True)
        self.audit_logs.setObjectName("AuditLogs")
        lg_layout.addWidget(self.audit_logs)
        right_layout.addWidget(log_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([560, 500])
        layout.addWidget(splitter)

        self.refresh_fence_table_view_from_sqlite()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QLabel#SectionLabel { font-size: 14px; font-weight: bold; color: #00FFCC; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLineEdit, QComboBox { background-color: #161D26; border: 1px solid #232E3C; border-radius: 2px; padding: 5px 8px; color: #FFFFFF; font-size: 12px; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #00FFCC; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 12px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QTextEdit#AuditLogs { background-color: #0A0E14; border: 1px solid #1F2936; color: #EF4444; font-family: "Consolas", monospace; font-size: 11px; line-height: 16px; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 6px 12px; border-radius: 2px; }
            QPushButton#ActionBtn:hover { background-color: #007A66; }
            QPushButton#DangerBtn { background-color: #251820; color: #FF6B6B; border: 1px solid #3D222E; font-weight: bold; padding: 8px 12px; border-radius: 2px; width: 100%; }
        """)

    def refresh_fence_table_view_from_sqlite(self):
        self.display_rows = self.db.execute_query("SELECT fence_id, fence_type, points_json FROM field_fences")
        self.table.setRowCount(len(self.display_rows))
        
        for r_idx, row in enumerate(self.display_rows):
            fid, f_type, p_json = row
            try:
                pts_list = json.loads(p_json)
                pts_count = len(pts_list)
            except:
                pts_count = 0
            
            self.table.setItem(r_idx, 0, QTableWidgetItem(fid))
            self.table.setItem(r_idx, 1, QTableWidgetItem(f_type))
            self.table.setItem(r_idx, 2, QTableWidgetItem(f"{pts_count} 个空间顶点"))
            
            for c in range(3):
                self.table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def handle_fence_selection(self):
        selected = self.table.selectedRanges()
        if not selected: return
        self.selected_fence_id = self.table.item(selected[0].topRow(), 0).text()

    def global_ray_casting_spatial_scan(self):
        w, h = self.vector_map.width(), self.vector_map.height()
        cx, cy = w / 2, h / 2
        
        safe_points_wgs = [(116.38, 39.88), (116.48, 39.88), (116.48, 39.96), (116.38, 39.96)]
        safe_points_mapped = [(cx + (p[0] - 116.40) * 4000.0, cy - (p[1] - 39.92) * 4000.0) for p in safe_points_wgs]

        danger_zones_mapped = {}
        db_fences = self.db.execute_query("SELECT fence_id, points_json FROM field_fences")
        
        fence_wgs_map = {} 
        for f_row in db_fences:
            fid, p_json = f_row
            try:
                pts_wgs = json.loads(p_json)
                fence_wgs_map[fid] = pts_wgs
                mapped_pts = [(cx + (p[0] - 116.40) * 4000.0, cy - (p[1] - 39.92) * 4000.0) for p in pts_wgs]
                danger_zones_mapped[fid] = mapped_pts
            except:
                pass

        machinery_records = self.db.execute_query("SELECT node_id, current_x, current_y FROM field_machinery")
        machinery_vector_payload = []
        is_any_breach_detected = False
        
        for record in machinery_records:
            nid, mx, my = record
            pmx = cx + (mx - 116.40) * 4000.0
            pmy = cy - (my - 39.92) * 4000.0
            
            is_outside_safe_perimeter = not SpatialRayCastingEngine.is_point_in_polygon(mx, my, safe_points_wgs)
            
            is_breaching_danger_area = False
            triggered_fence_name = ""
            for fid, wgs_polygon in fence_wgs_map.items():
                if SpatialRayCastingEngine.is_point_in_polygon(mx, my, wgs_polygon):
                    is_breaching_danger_area = True
                    triggered_fence_name = fid
                    break
            
            total_conflict_breach = is_outside_safe_perimeter or is_breaching_danger_area
            machinery_vector_payload.append((nid, pmx, pmy, total_conflict_breach))

            if total_conflict_breach:
                is_any_breach_detected = True
                self.db.execute_update("UPDATE field_machinery SET status='故障异常' WHERE node_id=?", (nid,))
                
                reason_str = f"侵入高危红线禁区 [{triggered_fence_name}]" if is_breaching_danger_area else "越出合作社大绿线边界红线"
                self.audit_logs.append(
                    f"[{time.strftime('%H:%M:%S')}] 🔴 存储器空间拦截！机车 {nid} 发生侵入冲突！\n"
                    f"    - 持久化经纬度点阵: ({mx:.5f}, {my:.5f})\n"
                    f"    - 拦截原因: {reason_str}\n"
                    f"    - 数据库事务：已向节点下发最高优先权硬熔断指令！"
                )

        if not is_any_breach_detected and random.randint(0, 6) == 3:
            self.audit_logs.clear()
            
        self.vector_map.update_spatial_vectors(machinery_vector_payload, safe_points_mapped, danger_zones_mapped)

    def sqlite_insert_geo_fence(self):
        fid = self.in_fence_id.text().strip()
        if not fid: return
        
        dup_check = self.db.execute_query("SELECT COUNT(*) FROM field_fences WHERE fence_id=?", (fid,))
        if dup_check and dup_check[0][0] > 0: 
            QMessageBox.warning(self, "唯一主键冲突", "该隔离带识别码在 SQLite 关系表中已存在。")
            return
            
        selected_type = self.in_fence_type.currentText()
        bx = 116.40 + random.uniform(-0.03, 0.03)
        by = 39.92 + random.uniform(-0.03, 0.03)
        generated_polygon_pts = [(bx, by), (bx + 0.009, by), (bx + 0.009, by + 0.007), (bx, by + 0.007)]
        points_string_payload = json.dumps(generated_polygon_pts)
        
        status = self.db.execute_update("INSERT INTO field_fences VALUES (?, ?, ?)", (fid, selected_type, points_string_payload))
        if status:
            self.refresh_fence_table_view_from_sqlite()
            self.in_fence_id.clear()

    def sqlite_delete_geo_fence(self):
        if not self.selected_fence_id: 
            QMessageBox.warning(self, "解绑终止", "未捕获到活跃的隔离网主键焦点。")
            return
            
        confirm = QMessageBox.question(self, "关系型物理析构确认", f"确定要从本地 SQLite 数据库中永久抹除 {self.selected_fence_id} 的四至数据吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            status = self.db.execute_update("DELETE FROM field_fences WHERE fence_id=?", (self.selected_fence_id,))
            if status:
                self.selected_fence_id = None
                self.refresh_fence_table_view_from_sqlite()

    def get_module_title(self):
        return "04. 电子围栏管理"