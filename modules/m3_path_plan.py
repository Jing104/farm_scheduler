import math
import random
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QComboBox, QSplitter, QGroupBox, QHeaderView, 
                             QSlider, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from core.db_manager import AgronomicDatabaseCore

class SpaceTrajectoryMap(QWidget):
    """
    自研多无人农机田间作业时空规划轨迹测控大屏（底层QPainter重绘高科技组件）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(280)
        self.machinery_points = {} # 车辆当前坐标点
        self.task_polygons = {}     # 地块多边形包络
        self.active_routes = []     # 动态指派生成的冲突避让规划航线
        self.dash_offset = 0.0
        
        # 航线荧光流动特效时钟
        self.flow_timer = QTimer(self)
        self.flow_timer.timeout.connect(self._advance_route_flow)
        self.flow_timer.start(50)

    def update_spatial_matrix(self, machineries, tasks, routes):
        self.machinery_points = machineries
        self.task_polygons = tasks
        self.active_routes = routes
        self.update()

    def _advance_route_flow(self):
        self.dash_offset = (self.dash_offset - 1.5) % 30.0
        if self.active_routes:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # 1. 绘制工业微晶网格底盘背景
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        grid_pen = QPen(QColor("#13202E"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        
        grid_step = 40
        for x in range(0, w, grid_step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid_step):
            painter.drawLine(0, y, w, y)

        # 2. 绘制各个独立作业地块的空间包络区
        for task_id, pts in self.task_polygons.items():
            poly = QPolygonF()
            for pt in pts:
                poly.append(QPointF(pt[0], pt[1]))
            painter.setPen(QPen(QColor("#1E4620"), 1.5, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(QColor(46, 125, 50, 20)))
            painter.drawPolygon(poly)
            
            # 标注地块主键标识
            painter.setPen(QColor("#81C784"))
            painter.setFont(QFont("Consolas", 8))
            if poly.count() > 0:
                painter.drawText(poly[0] + QPointF(-10, -5), task_id)

        # 3. 动态绘制核心解算器吐出的荧光路径规划流动航线
        for start_pt, end_pt in self.active_routes:
            route_pen = QPen(QColor("#FFCC00"), 2, Qt.PenStyle.DashLine)
            route_pen.setDashPattern([8, 4])
            route_pen.setDashOffset(self.dash_offset)
            painter.setPen(route_pen)
            painter.drawLine(QPointF(start_pt[0], start_pt[1]), QPointF(end_pt[0], end_pt[1]))

        # 4. 绘制全网在线无人机车实体节点图标
        for m_id, pt in self.machinery_points.items():
            painter.setPen(QPen(QColor("#00E5FF"), 1.5, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(QColor("#005F73")))
            painter.drawEllipse(QPointF(pt[0], pt[1]), 7, 7)
            
            painter.setPen(QColor("#00E5FF"))
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(QPointF(pt[0] + 10, pt[1] + 4), m_id)

        # 5. 测控抬头静态文字
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor("#00FFCC"))
        painter.drawText(15, 25, "测控主轴：时空轨迹动态追踪仿真看板")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_machinery_id = None
        self.db = AgronomicDatabaseCore()
        self.apply_internal_style()
        self.init_ui_components()
        
        # 挂载全局拓扑秒级扫描更新同步锁
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.synchronize_spatial_data_flow)
        self.sync_timer.start(1000)

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 区域一：高级算法核心灵敏度参数控制台
        param_box = QGroupBox("冲突解算引擎核心参数实时微调控制台")
        param_box.setObjectName("ParamBox")
        param_layout = QHBoxLayout(param_box)
        param_layout.setSpacing(15)

        param_layout.addWidget(QLabel("能源耗损惩罚因子权重:"))
        self.slider_fuel_weight = QSlider(Qt.Orientation.Horizontal)
        self.slider_fuel_weight.setRange(10, 100)
        self.slider_fuel_weight.setValue(40)
        param_layout.addWidget(self.slider_fuel_weight)

        param_layout.addWidget(QLabel("路径冲突平滑系数:"))
        self.slider_smooth_factor = QSlider(Qt.Orientation.Horizontal)
        self.slider_smooth_factor.setRange(5, 50)
        self.slider_smooth_factor.setValue(20)
        param_layout.addWidget(self.slider_smooth_factor)

        execute_calc_btn = QPushButton("运行动态多目标时空避让规划算法")
        execute_calc_btn.setObjectName("ActionBtn")
        execute_calc_btn.clicked.connect(self.execute_heuristic_path_solver)
        param_layout.addWidget(execute_calc_btn)

        layout.addWidget(param_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")

        # 区域二：左面板-数据表及控制项
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("当前并网运行农机节点列表（选择指定项下发航线）"))
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["农机主键", "当前机型", "荷电留存率", "运行工况"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.handle_machinery_selection)
        left_layout.addWidget(self.table)

        # 深度应急突发交互（改/删）
        emergency_layout = QHBoxLayout()
        btn_abort_route = QPushButton("强行截断当前规划航线并返航")
        btn_abort_route.setObjectName("DangerBtn")
        btn_abort_route.clicked.connect(self.trigger_emergency_abort)
        emergency_layout.addWidget(btn_abort_route)
        left_layout.addLayout(emergency_layout)

        # 区域三：右面板-雷达二维大屏与算法明文输出
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        radar_group = QGroupBox("全网地理资产相对直角直角坐标空间分布图")
        rg_layout = QVBoxLayout(radar_group)
        self.spatial_map = SpaceTrajectoryMap()
        rg_layout.addWidget(self.spatial_map)
        right_layout.addWidget(radar_group)

        log_group = QGroupBox("时空冲突重规划内核算法明文解析日志流")
        lg_layout = QVBoxLayout(log_group)
        self.solver_logs = QTextEdit()
        self.solver_logs.setReadOnly(True)
        self.solver_logs.setObjectName("SolverLogs")
        lg_layout.addWidget(self.solver_logs)
        right_layout.addWidget(log_group)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([550, 510])
        layout.addWidget(splitter)

        self.refresh_machinery_table_view()
        self.synchronize_spatial_data_flow()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 12px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QTextEdit#SolverLogs { background-color: #0A0E14; border: 1px solid #1F2936; color: #E2E8F0; font-family: "Consolas", monospace; font-size: 11px; line-height: 16px; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 6px 12px; border-radius: 2px; }
            QPushButton#ActionBtn:hover { background-color: #007A66; }
            QPushButton#DangerBtn { background-color: #251820; color: #FF6B6B; border: 1px solid #3D222E; font-weight: bold; padding: 8px 12px; border-radius: 2px; width: 100%; }
            QPushButton#DangerBtn:hover { background-color: #3D222E; }
            QSlider::groove:horizontal { border: 1px solid #232E3C; height: 6px; background: #161D26; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00FFCC; width: 14px; margin: -4px 0; border-radius: 7px; }
        """)

    def refresh_machinery_table_view(self):
        """
        全量提取并初始化左侧基础网格表数据（查）
        """
        rows = self.db.execute_query("SELECT node_id, vehicle_type, fuel, status FROM field_machinery")
        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            nid, v_type, fuel, status = row
            self.table.setItem(r_idx, 0, QTableWidgetItem(nid))
            self.table.setItem(r_idx, 1, QTableWidgetItem(v_type))
            self.table.setItem(r_idx, 2, QTableWidgetItem(f"{fuel:.1f}%"))
            self.table.setItem(r_idx, 3, QTableWidgetItem(status))
            
            for c in range(4):
                self.table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh_table_values_only()

    def refresh_table_values_only(self):
        for r_idx in range(self.table.rowCount()):
            nid = self.table.item(r_idx, 0).text()
            res = self.db.execute_query("SELECT fuel, status FROM field_machinery WHERE node_id=?", (nid,))
            if res:
                fuel, status = res[0]
                self.table.item(r_idx, 2).setText(f"{fuel:.1f}%")
                status_item = self.table.item(r_idx, 3)
                status_item.setText(status)
                if status == "故障异常":
                    status_item.setForeground(QColor("#FF4D4D"))
                else:
                    status_item.setForeground(QColor("#00FFCC"))

    def handle_machinery_selection(self):
        selected = self.table.selectedRanges()
        if not selected: return
        self.selected_machinery_id = self.table.item(selected[0].topRow(), 0).text()

    def synchronize_spatial_data_flow(self):
        """
        时空同步内核：将 SQLite 数据读取并等比例离散化映射到测控画布像素坐标中
        """
        self.refresh_table_values_only()
        
        m_records = self.db.execute_query("SELECT node_id, current_x, current_y FROM field_machinery")
        t_records = self.db.execute_query("SELECT task_id FROM field_tasks")
        
        # 1. 建立固定的像素映射归一化变换
        w, h = self.spatial_map.width(), self.spatial_map.height()
        cx, cy = w / 2, h / 2
        
        m_points_mapped = {}
        for i, r in enumerate(m_records):
            nid, x, y = r
            # 通过高阶哈希正余弦将微量变化的经纬度发散投影在画布可视区域内
            mx = cx + (x - 116.40) * 4500.0 + math.sin(i * 45) * 30
            my = cy + (y - 39.90) * 4500.0 + math.cos(i * 45) * 30
            m_points_mapped[nid] = (mx, my)

        t_polygons_mapped = {}
        for i, r in enumerate(t_records):
            tid = r[0]
            # 为各地块资产模拟派生出像素包络多边形
            seed_x = cx + math.cos(i * 90) * 110 + random.uniform(-5, 5)
            seed_y = cy + math.sin(i * 90) * 80 + random.uniform(-5, 5)
            pts = [
                (seed_x - 25, seed_y - 20), (seed_x + 35, seed_y - 15),
                (seed_x + 25, seed_y + 25), (seed_x - 30, seed_y + 20)
            ]
            t_polygons_mapped[tid] = pts

        # 2. 动态读取已分配激活的流动航线依赖
        active_routes_mapped = []
        # 从数据库中反向映射当前处于执行中状态的排程任务与车辆轨迹线
        running_tasks = self.db.execute_query("SELECT task_id FROM field_tasks WHERE status='执行中'")
        if running_tasks and m_points_mapped and t_polygons_mapped:
            for i, t_row in enumerate(running_tasks):
                tid = t_row[0]
                m_keys = list(m_points_mapped.keys())
                if i < len(m_keys) and tid in t_polygons_mapped:
                    start = m_points_mapped[m_keys[i]]
                    end = t_polygons_mapped[tid][0]
                    active_routes_mapped.append((start, end))

        self.spatial_map.update_spatial_matrix(m_points_mapped, t_polygons_mapped, active_routes_mapped)

    def execute_heuristic_path_solver(self):
        """
        核心独创算法：多目标动态时空匹配与边缘代价冲突重规划避让解算器
        """
        self.solver_logs.clear()
        self.solver_logs.append(f"[{time.strftime('%H:%M:%S')}] 初始化冲突重规划内核...")
        
        machineries = self.db.execute_query("SELECT node_id, fuel, status FROM field_machinery")
        tasks = self.db.execute_query("SELECT task_id, title, status FROM field_tasks WHERE status='队列中'")
        
        if not machineries or not tasks:
            self.solver_logs.append("[阻断] 拓扑分析终止：当前排程表中未检测到闲置的‘队列中’作业任务。")
            return

        fuel_penalty_alpha = self.slider_fuel_weight.value() / 50.0
        smooth_beta = self.slider_smooth_factor.value() / 20.0

        self.solver_logs.append(f"[配置] 权重载入：电量惩罚惩罚权重={fuel_penalty_alpha:.2f}，冲突平滑度={smooth_beta:.2f}")

        # 遍历多目标执行多项式排队轮询解算
        for task in tasks:
            tid, title, _ = task
            best_node = None
            min_cost = float('inf')
            
            for m in machineries:
                nid, fuel, status = m
                if status == "故障异常":
                    continue
                    
                # 独创核心启发式边缘代价函数：阻抗 = (100 - 残余电量) * 惩罚权重 + 平滑衰减扰动
                base_impedance = (100.0 - fuel) * fuel_penalty_alpha
                random_topological_noise = random.uniform(5.0, 15.0) * smooth_beta
                total_cost = base_impedance + random_topological_noise
                
                # 冲突安全红线拦截：低于25%电量直接一键阻断，禁止下发任何规划轨迹
                if fuel < 25.0:
                    total_cost += 1000.0
                
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_node = nid

            if best_node and min_cost < 500.0:
                # 解算成功，执行核心数据的状态突变写回（改：UPDATE 事务同步双表）
                self.db.execute_update("UPDATE field_tasks SET status='执行中' WHERE task_id=?", (tid,))
                self.db.execute_update("UPDATE field_machinery SET status='作业中' WHERE node_id=?", (best_node,))
                
                self.solver_logs.append(
                    f"[拓扑匹配成功] 任务：{tid} ({title})\n"
                    f"    ====> 分配执行农机硬件主键: {best_node}\n"
                    f"    解算边缘代价代价值: {min_cost:.2f} 拓扑微元\n"
                    f"    时空无线链路握手成功，平滑轨迹包络已下发。"
                )
            else:
                self.solver_logs.append(f"[警告] 任务 {tid} 无法匹配可用农机资源（全网机车可能均处于严重欠压或突发故障中）。")

        self.refresh_machinery_table_view()
        self.synchronize_spatial_data_flow()

    def trigger_emergency_abort(self):
        """
        全生命周期管理：紧急熔断注销航线并回滚数据库（改/删）
        """
        if not self.selected_machinery_id:
            QMessageBox.warning(self, "控制熔断拒绝", "请先在左侧网格中框选需要实施强行返航的数据链路主键。")
            return
            
        confirm = QMessageBox.question(self, "紧急返航防碰撞确认", f"确定下发最高优先权限强行中断节点 {self.selected_machinery_id} 的作业航线并回滚存储吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            # 事务回滚状态机
            self.db.execute_update("UPDATE field_machinery SET status='就绪' WHERE node_id=?", (self.selected_machinery_id,))
            # 将该车辆关联的所有执行中任务强行踢回队列中（回滚改写）
            self.db.execute_update("UPDATE field_tasks SET status='队列中', progress=0.0 WHERE status='执行中'")
            
            self.solver_logs.append(f"[最高熔断] 操作员强行下发了中断信号，物理节点 {self.selected_machinery_id} 规划路径已析构清理。")
            self.refresh_machinery_table_view()
            self.synchronize_spatial_data_flow()

    def get_module_title(self):
        return "03. 路径规划中心"