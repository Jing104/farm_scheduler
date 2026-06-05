import math
import random
import time
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QMessageBox, QLabel, 
                             QComboBox, QSplitter, QGroupBox, QHeaderView, QFileDialog)
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from core.db_manager import AgronomicDatabaseCore

class AdvancedIndustrialStatisticsCanvas(QWidget):
    """
    自研高科技多维能效审计数字大屏（纯底层QPainter重绘组件，包含极坐标雷达图与全网对比直方图）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(320)
        self.machinery_metrics = []  
        self.selected_index = -1     
        self.pulse_frame = 0         
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation_frame)
        self.anim_timer.start(50)

    def update_animation_frame(self):
        self.pulse_frame = (self.pulse_frame + 1) % 360
        self.update()

    def load_statistics_payload(self, metrics):
        self.machinery_metrics = metrics
        if metrics and self.selected_index == -1:
            self.selected_index = 0
        self.update()

    def set_active_machinery_index(self, index):
        if 0 <= index < len(self.machinery_metrics):
            self.selected_index = index
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor("#0A0E14"))
        grid_pen = QPen(QColor("#13202E"), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        grid_step = 50
        for x in range(0, w, grid_step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid_step):
            painter.drawLine(0, y, w, y)

        if not self.machinery_metrics:
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.setPen(QColor("#6C7A8C"))
            painter.drawText(20, h // 2, "全局多维分析线轴：等待跨表级联算子析构数据源...")
            return

        left_rect = QRectF(0, 0, w * 0.45, h)
        right_rect = QRectF(w * 0.45, 0, w * 0.55, h)

        self.draw_energy_efficiency_radar(painter, left_rect)
        self.draw_machinery_contrast_bars(painter, right_rect)

    def draw_energy_efficiency_radar(self, painter, rect):
        """
        核心空间三角函数算法：手写五维能效阻抗雷达图
        """
        cx = rect.left() + rect.width() / 2
        cy = rect.top() + rect.height() / 2
        max_r = min(rect.width(), rect.height()) // 2 - 35
        
        if self.selected_index < 0 or self.selected_index >= len(self.machinery_metrics):
            return
            
        metric = self.machinery_metrics[self.selected_index]
        node_id, v_type, fuel, rpm, temp, press, sats, track_count, score = metric

        # 维度映射归一化
        v1 = fuel / 100.0
        v2 = min(1.0, rpm / 2000.0)
        v3 = min(1.0, temp / 100.0)
        v4 = min(1.0, sats / 20.0)
        v5 = min(1.0, track_count / 30.0)
        
        dimensions = [v1, v2, v3, v4, v5]
        labels = ["荷电留存", "引擎转速", "液压温控", "卫星锁定", "时序里程"]
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for layer in [0.3, 0.6, 1.0]:
            r = max_r * layer
            poly = QPolygonF()
            for i in range(5):
                angle = i * 2 * math.pi / 5 - math.pi / 2
                poly.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
            painter.setPen(QPen(QColor("#1E2D3D"), 1, Qt.PenStyle.SolidLine))
            painter.drawPolygon(poly)

        painter.setFont(QFont("Microsoft YaHei", 8))
        for i in range(5):
            angle = i * 2 * math.pi / 5 - math.pi / 2
            tx = cx + max_r * math.cos(angle)
            ty = cy + max_r * math.sin(angle)
            painter.setPen(QPen(QColor("#4B5F75"), 1))
            painter.drawLine(int(cx), int(cy), int(tx), int(ty))
            
            lx = cx + (max_r + 16) * math.cos(angle) - 20
            ly = cy + (max_r + 12) * math.sin(angle) + 4
            painter.setPen(QColor("#8A9BB0"))
            painter.drawText(int(lx), int(ly), labels[i])

        data_poly = QPolygonF()
        for i in range(5):
            angle = i * 2 * math.pi / 5 - math.pi / 2
            r = max_r * dimensions[i]
            data_poly.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))

        pulse_alpha = int(70 + 30 * math.sin(self.pulse_frame * math.pi / 180))
        painter.setBrush(QBrush(QColor(0, 255, 204, pulse_alpha)))
        painter.setPen(QPen(QColor("#00FFCC"), 2, Qt.PenStyle.SolidLine))
        painter.drawPolygon(data_poly)
        
        painter.setPen(QColor("#00FFCC"))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        
        # 处理主键显示，过滤特定非中文字符
        display_id = node_id.replace("Machinery-", "机车节点-")
        painter.drawText(20, 25, f"核心审计拓扑: {display_id}")

    def draw_machinery_contrast_bars(self, painter, rect):
        """
        手写全网能效审计得分对比直方图
        """
        margin_left = rect.left() + 40
        margin_bottom = rect.bottom() - 40
        plot_w = rect.width() - 60
        plot_h = rect.height() - 80
        
        count = len(self.machinery_metrics)
        if count == 0: return
        
        bar_gap = 18
        total_gaps_w = bar_gap * (count - 1)
        bar_w = (plot_w - total_gaps_w) / count
        bar_w = max(15.0, min(bar_w, 45.0))

        painter.setPen(QPen(QColor("#23354A"), 1.5))
        painter.drawLine(int(margin_left), int(margin_bottom), int(margin_left + plot_w), int(margin_bottom))

        painter.setFont(QFont("Microsoft YaHei", 8))
        for i, metric in enumerate(self.machinery_metrics):
            node_id = metric[0]
            score = metric[8]  
            
            bx = margin_left + i * (bar_w + bar_gap)
            bh = (score / 100.0) * plot_h
            by = margin_bottom - bh
            
            if i == self.selected_index:
                painter.setBrush(QBrush(QColor("#F59E0B")))
                painter.setPen(QPen(QColor("#FFFFFF"), 1))
            else:
                painter.setBrush(QBrush(QColor("#1E3A8A")))
                painter.setPen(QPen(QColor("#3B82F6"), 1))
                
            painter.drawRect(QRectF(bx, by, bar_w, bh))
            
            painter.setPen(QColor("#E2E8F0"))
            painter.drawText(int(bx + bar_w/2 - 10), int(by - 6), f"{int(score)}")
            
            painter.setPen(QColor("#6C7A8C"))
            display_label = node_id.replace("Machinery-", "机车-")
            painter.drawText(int(bx + bar_w/2 - 18), int(margin_bottom + 16), display_label)

        painter.setPen(QColor("#38BDF8"))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        painter.drawText(int(margin_left), 25, "全网机车综合阻抗能效解算对账单")


class ModuleEntry(QWidget):
    def __init__(self):
        super().__init__()
        self.db = AgronomicDatabaseCore()
        self.cached_metrics = []
        self.current_filter_status = "全部工况总线"
        
        self.apply_internal_style()
        self.init_ui_components()

    def init_ui_components(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        filter_box = QGroupBox("多表级联能效核算控制总线")
        filter_box.setObjectName("FilterBox")
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setSpacing(15)

        filter_layout.addWidget(QLabel("工况状态机筛选:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部工况总线", "就绪", "加注中", "故障异常"])
        self.filter_combo.currentIndexChanged.connect(self.handle_filter_condition_changed)
        filter_layout.addWidget(self.filter_combo, stretch=2)

        btn_recalc = QPushButton("强制执行跨表级联算子重算")
        btn_recalc.setObjectName("ActionBtn")
        btn_recalc.clicked.connect(self.execute_cross_table_aggregation_solver)
        filter_layout.addWidget(btn_recalc, stretch=1)

        btn_export = QPushButton("安全导出全量高级审计报表表格")
        btn_export.setObjectName("ResumeBtn")
        btn_export.clicked.connect(self.export_audited_report_to_local_csv)
        filter_layout.addWidget(btn_export, stretch=1)

        layout.addWidget(filter_box)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setObjectName("MainSplitter")

        self.visual_screen = AdvancedIndustrialStatisticsCanvas()
        splitter.addWidget(self.visual_screen)

        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(0, 5, 0, 0)
        
        tc_layout.addWidget(QLabel("基于北斗时序与物理遥测交叉对冲的能效审计细节详单"))
        self.report_table = QTableWidget()
        self.report_table.setColumnCount(6)
        self.report_table.setHorizontalHeaderLabels([
            "机车唯一识别码", "设备物理分类", "卫星锁定质量", "历史轨迹总微元", "解算能效得分值", "审计合规判定标签"
        ])
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.report_table.verticalHeader().setVisible(False)
        self.report_table.itemSelectionChanged.connect(self.handle_table_row_selection_sync)
        tc_layout.addWidget(self.report_table)

        splitter.addWidget(table_container)
        splitter.setSizes([320, 240])
        layout.addWidget(splitter)

        self.execute_cross_table_aggregation_solver()

    def apply_internal_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #121820; color: #B0B5BC; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QGroupBox { border: 1px solid #232E3C; border-radius: 4px; font-weight: bold; font-size: 12px; color: #00FFCC; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QComboBox { background-color: #161D26; border: 1px solid #232E3C; color: #FFFFFF; padding: 5px; font-size: 12px; border-radius: 2px; }
            QTableWidget { background-color: #161D26; border: 1px solid #232E3C; gridline-color: #1F2936; color: #E2E8F0; font-size: 11px; }
            QHeaderView::section { background-color: #1E2734; color: #00FFCC; padding: 6px; border: 1px solid #232E3C; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1A2E3B; color: #00FFCC; }
            QPushButton#ActionBtn { background-color: #005F50; color: #FFFFFF; border: 1px solid #007A66; font-weight: bold; padding: 6px 12px; border-radius: 2px; }
            QPushButton#ActionBtn:hover { background-color: #007A66; }
            QPushButton#ResumeBtn { background-color: #1A3043; color: #38BDF8; border: 1px solid #254563; font-weight: bold; padding: 6px 12px; border-radius: 2px; }
            QPushButton#ResumeBtn:hover { background-color: #254563; }
        """)

    def execute_cross_table_aggregation_solver(self):
        """
        核心解算算子：级联多表，对全网机车数据进行综合交叉对冲及能效建模
        """
        sql_base = """
            SELECT node_id, vehicle_type, fuel, engine_rpm, hydraulic_temp, pump_pressure, satellites 
            FROM field_machinery
        """
        if self.current_filter_status != "全部工况总线":
            sql_base += f" WHERE status = '{self.current_filter_status}'"
            
        rows = self.db.execute_query(sql_base)
        self.cached_metrics = []

        for r in rows:
            node_id, v_type, fuel, rpm, temp, press, sats = r
            
            track_res = self.db.execute_query(
                "SELECT COUNT(*) FROM field_historical_tracks WHERE node_id = ?", (node_id,)
            )
            track_count = track_res[0][0] if track_res else 0

            sat_score = (sats / 20.0) * 30.0
            fuel_score = (fuel / 100.0) * 30.0
            activity_score = min(40.0, (track_count / 20.0) * 40.0)
            
            penalty = 0.0
            mach_status_check = self.db.execute_query("SELECT status FROM field_machinery WHERE node_id=?", (node_id,))
            if mach_status_check and mach_status_check[0][0] == "故障异常":
                penalty = 35.0
                
            total_score = max(5.0, min(100.0, sat_score + fuel_score + activity_score - penalty))
            
            self.cached_metrics.append((
                node_id, v_type, fuel, rpm, temp, press, sats, track_count, total_score
            ))

        self.visual_screen.load_statistics_payload(self.cached_metrics)
        
        self.report_table.setRowCount(len(self.cached_metrics))
        for r_idx, metric in enumerate(self.cached_metrics):
            nid, v_type, _, _, _, _, sats, track_cnt, score = metric
            
            display_id = nid.replace("Machinery-", "机车节点-")
            self.report_table.setItem(r_idx, 0, QTableWidgetItem(display_id))
            self.report_table.setItem(r_idx, 1, QTableWidgetItem(v_type))
            self.report_table.setItem(r_idx, 2, QTableWidgetItem(f"{sats} 颗锁空"))
            self.report_table.setItem(r_idx, 3, QTableWidgetItem(f"{track_cnt} 空间微元"))
            self.report_table.setItem(r_idx, 4, QTableWidgetItem(f"{score:.1f} 效能分"))
            
            if score >= 75.0:
                audit_item = QTableWidgetItem("优等资产及极高坪效")
            elif score >= 50.0:
                audit_item = QTableWidgetItem("常规留存及资源安全")
            else:
                audit_item = QTableWidgetItem("高危预警及效能挂起")
                
            self.report_table.setItem(r_idx, 5, audit_item)

            for c in range(6):
                self.report_table.item(r_idx, c).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.report_table.item(r_idx, c).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def handle_filter_condition_changed(self, index):
        self.current_filter_status = self.filter_combo.currentText()
        self.execute_cross_table_aggregation_solver()

    def handle_table_row_selection_sync(self):
        selected = self.report_table.selectedRanges()
        if not selected: return
        row = selected[0].topRow()
        self.visual_screen.set_active_machinery_index(row)

    def export_audited_report_to_local_csv(self):
        """
        高级文件资产持久化交互（创/写）：一键解算当前状态流并导出为本地数据表
        """
        if not self.cached_metrics:
            QMessageBox.warning(self, "导出终止", "当前核算缓冲区内无可用的清洗资产流，请重算后再试。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出全网能效审计对账单", f"全网能效审计表_{int(time.time())}.csv", "标准数据表格 (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8-sig") as f:
                f.write("机车唯一识别码,设备物理分类,当前荷电率百分比,引擎转速,液压温度,主泵反馈压,北斗卫星锁定数,时序轨迹总微元,解算能效得分值\n")
                for m in self.cached_metrics:
                    line = f"{m[0]},{m[1]},{m[2]},{m[3]},{m[4]},{m[5]},{m[6]},{m[7]},{m[8]:.2f}\n"
                    f.write(line)
            QMessageBox.information(self, "资产导出完成", f"跨表级联审计详单已安全写入本地磁盘：\n{os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "持久化失败", f"向指定磁盘写入报表资产时遭遇核心拦截：\n{str(e)}")

    def get_module_title(self):
        return "08. 统计报表与能效审计"