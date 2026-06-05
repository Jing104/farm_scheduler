import math
import random
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QLineEdit, QComboBox, QSplitter, QGroupBox, 
                             QHeaderView, QSpinBox, QTreeWidget, QTreeWidgetItem)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from core.db_manager import AgronomicDatabaseCore

class AgronomicGeometryEngine:
    """
    自研级农事实时几何测绘引擎：基于格雷厄姆扫描凸包算法与鞋带面积解算定理
    """
    @staticmethod
    def _cross_product(p1, p2, p3):
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

    @classmethod
    def compute_convex_hull(cls, points):
        if len(points) <= 3: 
            return points
        start_point = min(points, key=lambda p: (p[1], p[0]))
        def theta_sort(p):
            return math.atan2(p[1] - start_point[1], p[0] - start_point[0])
        sorted_pts = sorted(points, key=theta_sort)
        hull = [start_point, sorted_pts[0], sorted_pts[1]]
        for i in range(2, len(sorted_pts)):
            while len(hull) >= 2 and cls._cross_product(hull[-2], hull[-1], sorted_pts[i]) <= 0:
                hull.pop()
            hull.append(sorted_pts[i])
        return hull

    @staticmethod
    def calculate_shoelace_area(hull_points):
        n = len(hull_points)
        if n < 3: 
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += hull_points[i][0] * hull_points[j][1]
            area -= hull_points[j][0] * hull_points[i][1]
        absolute_m2 = abs(area) * 111000.0 * 111000.0 * 0.0001
        calculated_mu = absolute_m2 * 0.0015
        return round(calculated_mu, 1)


class GeometricRadarMap(QWidget):
    """
    自研高精度田间地块空间几何闭合边界极坐标仿真雷达组件（底层重绘）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.polygon_points = []
        self.sweep_angle = 0.0
        self.sweep_timer = QTimer(self)
        self.sweep_timer.timeout.connect(self._advance_sweep_angle)
        self.sweep_timer.start(40)

    def set_boundary_data(self, pts):
        self.polygon_points = pts
        self.update()

    def _advance_sweep_angle(self):
        self.sweep_angle = (self.sweep_angle + 3.0) % 360.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        center = QPointF(w / 2.0, h / 2.0)
        max_r = min(w, h) // 2 - 20
        
        pen_radial = QPen(QColor("#112430"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen_radial)
        for radius_ratio in [1.0, 0.7, 0.4, 0.1]:
            painter.drawEllipse(center, max_r * radius_ratio, max_r * radius_ratio)
            
        painter.setPen(QPen(QColor("#163242"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, int(h/2), w, int(h/2))
        painter.drawLine(int(w/2), 0, int(w/2), h)

        painter.save()
        painter.translate(center)
        painter.rotate(self.sweep_angle)
        sweep_brush = QBrush(QColor(0, 255, 204, 15))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(sweep_brush)
        painter.drawPie(QRectF(-max_r, -max_r, max_r*2, max_r*2), 0, -45 * 16)
        painter.restore()

        if not self.polygon_points:
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#546E7A"))
            painter.drawText(20, h - 15, "全局测控链路：等待选择目标地块资产")
            return

        poly = QPolygonF()
        xs = [p[0] for p in self.polygon_points]
        ys = [p[1] for p in self.polygon_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = (max_x - min_x) if max_x != min_x else 0.01
        range_y = (max_y - min_y) if max_y != min_y else 0.01

        for pt in self.polygon_points:
            rx = ((pt[0] - min_x) / range_x - 0.5) * (max_r * 1.3) + center.x()
            ry = ((pt[1] - min_y) / range_y - 0.5) * (max_r * 1.3) + center.y()
            poly.append(QPointF(rx, ry))

        painter.setPen(QPen(QColor("#00FFCC"), 1.5, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(QColor(0, 255, 204, 30))) 
        painter.drawPolygon(poly)
        painter.setBrush(QBrush(QColor("#00FFCC")))
        for i in range(poly.count()):
            painter.drawEllipse(poly[i], 3.3, 3.3)

        painter.setPen(QColor("#00FFCC"))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(15, 25, "空间雷达：北斗闭合多边形包络网线处于锁死态")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_task_id = None
        self.display_rows = []
        self.static_boundary_cache = {} 
        self.db = AgronomicDatabaseCore()
        self.apply_internal_style()
        self.init_ui_components()
        
        self.engine_timer = QTimer(self)
        self.engine_timer.timeout.connect(self.global_task_engine_tick)
        self.engine_timer.start(1000)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        wizard_box = QGroupBox("全新智能化任务下发向导（本地持久化数据级交互）")
        wizard_box.setObjectName("WizardBox")
        wizard_layout = QHBoxLayout(wizard_box)
        wizard_layout.setSpacing(10)
        
        self.in_title = QLineEdit()
        self.in_title.setPlaceholderText("请输入任务作业技术指标简述...")
        self.in_block = QComboBox()
        self.in_block.addItems(["东区一号地", "北区水田A", "南区坡地", "西区林果示范区"])
        self.in_area = QSpinBox()
        self.in_area.setRange(20, 2000)
        self.in_area.setValue(120)
        
        commit_btn = QPushButton("向排程队列注入新作业任务")
        commit_btn.setObjectName("ActionBtn")
        commit_btn.clicked.connect(self.sqlite_insert_task)
        
        wizard_layout.addWidget(self.in_title, stretch=2)
        wizard_layout.addWidget(QLabel("地块资产:"))
        wizard_layout.addWidget(self.in_block, stretch=1)
        wizard_layout.addWidget(QLabel("测绘面积限制:"))
        wizard_layout.addWidget(self.in_area, stretch=1)
        wizard_layout.addWidget(commit_btn, stretch=1)
        layout.addWidget(wizard_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        section_lbl = QLabel("当前多目标作业任务流排程管理系统")
        section_lbl.setObjectName("SectionLabel")
        left_layout.addWidget(section_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["任务编号", "作业任务描述", "目标地块", "规划测算面积", "当前核心状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.handle_task_row_selection)
        left_layout.addWidget(self.table)

        # 核心控制交互按钮矩阵（补全暂停挂起、恢复执行、出队销毁完整闭环）
        ctrl_grid_layout = QHBoxLayout()
        ctrl_grid_layout.setSpacing(10)
        
        btn_dispatch = QPushButton("激活边缘端分发执行")
        btn_dispatch.setObjectName("ActionBtn")
        btn_dispatch.clicked.connect(self.sqlite_update_task_status)

        btn_pause = QPushButton("一键挂起暂停任务")
        btn_pause.setObjectName("WarningBtn")
        btn_pause.clicked.connect(self.sqlite_pause_task_status)

        btn_resume = QPushButton("恢复并行调度状态")
        btn_resume.setObjectName("ResumeBtn")
        btn_resume.clicked.connect(self.sqlite_resume_task_status)

        btn_terminate = QPushButton("注销出队熔断任务")
        btn_terminate.setObjectName("DangerBtn")
        btn_terminate.clicked.connect(self.sqlite_delete_task)

        ctrl_grid_layout.addWidget(btn_dispatch)
        ctrl_grid_layout.addWidget(btn_pause)
        ctrl_grid_layout.addWidget(btn_resume)
        ctrl_grid_layout.addWidget(btn_terminate)
        left_layout.addLayout(ctrl_grid_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)
        
        radar_group = QGroupBox("北斗空间测控轴：全自动多边形封闭几何拓扑雷达")
        radar_group.setObjectName("RadarGroup")
        rg_layout = QVBoxLayout(radar_group)
        self.radar_map = GeometricRadarMap()
        rg_layout.addWidget(self.radar_map)
        right_layout.addWidget(radar_group)

        tree_group = QGroupBox("有向无环图前置依赖工况约束审计树")
        tree_group.setObjectName("TreeGroup")
        tg_layout = QVBoxLayout(tree_group)
        self.dep_tree = QTreeWidget()
        self.dep_tree.setHeaderHidden(True)
        self.dep_tree.setObjectName("DepTree")
        tg_layout.addWidget(self.dep_tree)
        right_layout.addWidget(tree_group)
        
        self.info_panel = QGroupBox("地块测绘几何学边界解算流")
        self.info_panel.setObjectName("InfoGroup")
        ip_layout = QVBoxLayout(self.info_panel)
        self.boundary_text = QLabel("等待读取多空间拓扑特征序列...")
        self.boundary_text.setWordWrap(True)
        self.boundary_text.setObjectName("MetricText")
        ip_layout.addWidget(self.boundary_text)
        right_layout.addWidget(self.info_panel)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 480])
        layout.addWidget(splitter)
        
        self.refresh_task_grid_from_sqlite()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QLabel#SectionLabel { font-size: 14px; font-weight: bold; color: #00FFCC; padding-bottom: 2px; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLineEdit, QComboBox, QSpinBox { background-color: #161D26; border: 1px solid #232E3C; color: #FFFFFF; padding: 5px; font-size: 12px; border-radius: 2px; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 12px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QTreeWidget#DepTree { background-color: #161D26; border: 1px solid #232E3C; color: #E2E8F0; font-size: 11px; max-height: 80px; }
            QLabel#MetricText { font-family: "Consolas", monospace; font-size: 11px; color: #8A9BB0; background-color: #18222E; padding: 8px; border-left: 2px solid #00FFCC; line-height: 16px; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 7px; border-radius: 2px; }
            QPushButton#WarningBtn { background-color: #4A3718; color: #FFAA00; border: 1px solid #6E5120; font-weight: bold; padding: 7px; border-radius: 2px; }
            QPushButton#WarningBtn:hover { background-color: #6E5120; }
            QPushButton#ResumeBtn { background-color: #1A3043; color: #38BDF8; border: 1px solid #254563; font-weight: bold; padding: 7px; border-radius: 2px; }
            QPushButton#ResumeBtn:hover { background-color: #254563; }
            QPushButton#DangerBtn { background-color: #251820; color: #FF6B6B; border: 1px solid #3D222E; font-weight: bold; padding: 7px; border-radius: 2px; }
        """)

    def global_task_engine_tick(self):
        try:
            # 只提取执行中的状态平滑累加进度，挂起的任务在这里会自然卡定停止，完美模拟就地驻留
            tasks = self.db.execute_query("SELECT task_id, progress, area FROM field_tasks WHERE status='执行中'")
            for t in tasks:
                tid, prog, area = t
                step_factor = (8.5 / float(area)) * random.uniform(0.9, 1.1)
                prog = min(100.0, round(prog + step_factor, 2))
                status = "已完工" if prog >= 100.0 else "执行中"
                self.db.execute_update("UPDATE field_tasks SET progress=?, status=? WHERE task_id=?", (prog, status, tid))
            self.refresh_grid_values_only()
        except Exception as e:
            print(f"任务总线状态刷新异常: {e}")

    def refresh_task_grid_from_sqlite(self):
        self.display_rows = self.db.execute_query("SELECT task_id, title, block_name, area, status FROM field_tasks")
        self.table.setRowCount(len(self.display_rows))
        for r_idx, row in enumerate(self.display_rows):
            tid, title, block, area, status = row
            self.table.setItem(r_idx, 0, QTableWidgetItem(tid))
            self.table.setItem(r_idx, 1, QTableWidgetItem(title))
            self.table.setItem(r_idx, 2, QTableWidgetItem(block))
            self.table.setItem(r_idx, 3, QTableWidgetItem(f"{area} 亩"))
            self.table.setItem(r_idx, 4, QTableWidgetItem(status))
            for c in range(5):
                self.table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh_grid_values_only()

    def refresh_grid_values_only(self):
        for r_idx in range(self.table.rowCount()):
            tid = self.table.item(r_idx, 0).text()
            res = self.db.execute_query("SELECT status, progress FROM field_tasks WHERE task_id=?", (tid,))
            if res:
                status, prog = res[0]
                item = self.table.item(r_idx, 4)
                if status == "执行中":
                    item.setText(f"执行中 ({prog}%)")
                    item.setForeground(QColor("#38BDF8"))
                elif status == "已挂起":
                    item.setText(f"已挂起暂停 ({prog}%)")
                    item.setForeground(QColor("#FFAA00"))
                elif status == "已完工":
                    item.setText("已完工")
                    item.setForeground(QColor("#22C55E"))
                else:
                    item.setText(status)
                    item.setForeground(QColor("#E2E8F0"))

    def handle_task_row_selection(self):
        selected = self.table.selectedRanges()
        if not selected: return
        row_idx = selected[0].topRow()
        self.selected_task_id = self.table.item(row_idx, 0).text()
        self.rebuild_dependency_tree_view()
        
        if self.selected_task_id not in self.static_boundary_cache:
            seed = random.uniform(0.01, 0.04)
            raw_scatter_pts = [
                (116.402 + seed, 39.904), (116.425 + seed, 39.901), 
                (116.438 + seed, 39.932), (116.391 + seed, 39.928), (116.415 + seed, 39.915) 
            ]
            hull_pts = AgronomicGeometryEngine.compute_convex_hull(raw_scatter_pts)
            geo_mu = AgronomicGeometryEngine.calculate_shoelace_area(hull_pts)
            self.static_boundary_cache[self.selected_task_id] = (hull_pts, geo_mu)
            
        target_pts, calculated_mu = self.static_boundary_cache[self.selected_task_id]
        self.radar_map.set_boundary_data(target_pts)
        
        res_db = self.db.execute_query("SELECT area FROM field_tasks WHERE task_id=?", (self.selected_task_id,))
        planned_mu = res_db[0][0] if res_db else 0
        pts_str = " \n-> ".join([f"边界特征点{i}: 经度{pt[0]:.4f} / 纬度{pt[1]:.4f}" for i, pt in enumerate(target_pts)])
        self.boundary_text.setText(
            f"排程测绘数据交叉比对验证中：\n"
            f"计划下发面积: {planned_mu} 亩  |  北斗多边形解算面积: {calculated_mu} 亩\n"
            f"轮廓点序列:\n{pts_str}"
        )

    def rebuild_dependency_tree_view(self):
        self.dep_tree.clear()
        if not self.selected_task_id: return
        root_item = QTreeWidgetItem(self.dep_tree, [f"业务工况依赖审计 [{self.selected_task_id}]"])
        root_item.setExpanded(True)
        if self.selected_task_id == "TASK-102":
            res = self.db.execute_query("SELECT status FROM field_tasks WHERE task_id='TASK-101'")
            parent_status = res[0][0] if res else "未知"
            child = QTreeWidgetItem(root_item, [f"强阻塞依赖项: TASK-101 [当前工况: {parent_status}]"])
            child.setForeground(0, QColor("#F59E0B") if parent_status != "已完工" else QColor("#22C55E"))
        else:
            QTreeWidgetItem(root_item, ["拓扑校验：当前任务无前置依赖，允许并行调度"])

    def sqlite_insert_task(self):
        title = self.in_title.text().strip()
        if not title: return
        nid = f"TASK-{random.randint(105, 999)}"
        self.db.execute_update("""
            INSERT INTO field_tasks VALUES (?, ?, ?, ?, '队列中', 0.0)
        """, (nid, title, self.in_block.currentText(), self.in_area.value()))
        self.refresh_task_grid_from_sqlite()
        self.in_title.clear()

    def sqlite_update_task_status(self):
        """激活执行"""
        if not self.selected_task_id: return
        if self.selected_task_id == "TASK-102":
            res = self.db.execute_query("SELECT status FROM field_tasks WHERE task_id='TASK-101'")
            if res and res[0][0] != "已完工":
                QMessageBox.critical(self, "依赖工况未解锁", "阻断：前置翻垦未完工，播种机组拒绝强行并网。")
                return
        self.db.execute_update("UPDATE field_tasks SET status='执行中' WHERE task_id=?", (self.selected_task_id,))

    def sqlite_pause_task_status(self):
        """一键挂起暂停（核心扩展：改）"""
        if not self.selected_task_id: return
        res = self.db.execute_query("SELECT status FROM field_tasks WHERE task_id=?", (self.selected_task_id,))
        if res and res[0][0] == "执行中":
            self.db.execute_update("UPDATE field_tasks SET status='已挂起' WHERE task_id=?", (self.selected_task_id,))
            self.refresh_grid_values_only()

    def sqlite_resume_task_status(self):
        """恢复并行调度（核心扩展：改）"""
        if not self.selected_task_id: return
        res = self.db.execute_query("SELECT status FROM field_tasks WHERE task_id=?", (self.selected_task_id,))
        if res and res[0][0] == "已挂起":
            self.db.execute_update("UPDATE field_tasks SET status='执行中' WHERE task_id=?", (self.selected_task_id,))
            self.refresh_grid_values_only()

    def sqlite_delete_task(self):
        """出队注销或强行熔断（满足出队销毁逻辑：删）"""
        if not self.selected_task_id: return
        res = self.db.execute_query("SELECT status FROM field_tasks WHERE task_id=?", (self.selected_task_id,))
        status = res[0][0] if res else "队列中"
        
        # 如果是队列中，代表温和出队；如果是执行中/挂起，代表突发强切
        msg = f"确定将处于【{status}】状态的任务 {self.selected_task_id} 从数据队列中出队清理吗？"
        confirm = QMessageBox.question(self, "数据链析构确认", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.execute_update("DELETE FROM field_tasks WHERE task_id=?", (self.selected_task_id,))
            if self.selected_task_id in self.static_boundary_cache:
                self.static_boundary_cache.pop(self.selected_task_id)
            self.selected_task_id = None
            self.dep_tree.clear()
            self.boundary_text.setText("等待读取多空间拓扑特征序列...")
            self.radar_map.set_boundary_data([])
            self.refresh_task_grid_from_sqlite()

    def get_module_title(self):
        return "02. 作业任务分发"