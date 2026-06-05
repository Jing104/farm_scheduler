import sqlite3
import os
import json
import time
import math
import sys

def get_platform_resource_path(relative_path):
    """
    自研时空路径重定向算子：动态兼容本地环境与自动化构建虚拟机临时解压释放环境
    """
    if hasattr(sys, '_MEIPASS'):
        # 自动化编译打包态：重定向至系统临时释放盘符
        return os.path.join(sys._MEIPASS, relative_path)
    # 源码本地开发态：维持常规绝对物理四至路径
    return os.path.join(os.path.abspath("."), relative_path)


class AgronomicDatabaseCore:
    """
    无人农机调度系统本地核心嵌入式SQLite数据引擎（集成路径重定向与静默容错单例模式）
    """
    _instance = None
    # 核心应用：通过算子锁定数据库物理文件的存储锚点，彻底防止打包后丢失表
    DB_FILE = get_platform_resource_path("storage_machinery.db")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """
        初始化物理文件句柄链接，并强制开启对多线程上下文的支持与外键约束机制
        """
        self.conn = sqlite3.connect(self.DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self.create_architect_tables()

    def create_architect_tables(self):
        """
        全生命周期表结构设计：一举集成 01 至 09 菜单所需的全部关系型及空间时序二维表
        """
        # 1. 基础物理表：全网无人机车实时遥测快照表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_machinery (
                node_id TEXT PRIMARY KEY,
                vehicle_type TEXT NOT NULL,
                status TEXT NOT NULL,
                current_x REAL NOT NULL,
                current_y REAL NOT NULL,
                fuel REAL NOT NULL,
                engine_rpm INTEGER NOT NULL,
                hydraulic_temp REAL NOT NULL,
                pump_pressure REAL NOT NULL,
                satellites INTEGER NOT NULL
            )
        """)

        # 2. 业务排程表：带时空进度的多目标农事作业任务排程表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                block_name TEXT NOT NULL,
                area INTEGER NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL
            )
        """)

        # 3. 空间几何表：基于GeoJSON特征的多边形封闭高危电子隔离网存储表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_fences (
                fence_id TEXT PRIMARY KEY,
                fence_type TEXT NOT NULL,
                points_json TEXT NOT NULL
            )
        """)

        # 4. 空间能耗表：全网农事能耗加注站资产储备表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_stations (
                station_id TEXT PRIMARY KEY,
                station_name TEXT NOT NULL,
                station_type TEXT NOT NULL,
                pos_x REAL NOT NULL,
                pos_y REAL NOT NULL,
                fuel_stock REAL NOT NULL
            )
        """)

        # 5. 维保工单表：在线机车突发硬件故障或越界强停的设备异常维保日志表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_maintain_logs (
                ticket_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                fault_description TEXT NOT NULL,
                trigger_time TEXT NOT NULL,
                handle_status TEXT NOT NULL,
                repair_engineer TEXT NOT NULL,
                FOREIGN KEY (node_id) REFERENCES field_machinery(node_id) ON DELETE CASCADE
            )
        """)

        # 6. 时序轨迹表：用于高频记录各车历史行进秒级轨迹坐标，支持动画高精再现
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_historical_tracks (
                track_id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                recorded_time TEXT NOT NULL,
                pos_x REAL NOT NULL,
                pos_y REAL NOT NULL,
                FOREIGN KEY (node_id) REFERENCES field_machinery(node_id) ON DELETE CASCADE
            )
        """)

        # 7. 田间气象表：全网区域无线测控微气象多传感器红线监测表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_weather_points (
                point_id TEXT PRIMARY KEY,
                region_name TEXT NOT NULL,
                wind_speed REAL NOT NULL,
                rainfall REAL NOT NULL,
                soil_moisture REAL NOT NULL,
                risk_level TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
        self.inject_initial_seeds_if_empty()

    def inject_initial_seeds_if_empty(self):
        """
        全量注入大系统硬核仿真种子，显式对齐所有字段列，防止解析错位
        """
        try:
            # 1. 注入机车初始工况（包含低电量车、常规就绪车、突发故障车）
            self.cursor.execute("SELECT COUNT(*) FROM field_machinery")
            if self.cursor.fetchone()[0] == 0:
                machinery_seeds = [
                    ("Machinery-01", "大马力收割机", "就绪", 116.4021, 39.9045, 85.0, 1650, 61.2, 63.5, 18),
                    ("Machinery-02", "高精度播种机", "故障异常", 116.4218, 39.9122, 14.5, 720, 91.5, 14.2, 11),
                    ("Machinery-03", "植保喷药机", "就绪", 116.3984, 39.8976, 22.1, 1620, 64.0, 60.1, 19),
                    ("Machinery-04", "深翻地垦机", "故障异常", 116.4561, 39.9513, 95.0, 680, 58.2, 8.5, 8)
                ]
                self.cursor.executemany("INSERT INTO field_machinery VALUES (?,?,?,?,?,?,?,?,?,?)", machinery_seeds)
                
            # 2. 注入作业排程初始流
            self.cursor.execute("SELECT COUNT(*) FROM field_tasks")
            if self.cursor.fetchone()[0] == 0:
                task_seeds = [
                    ("TASK-101", "东区基地开阔深翻作业", "东区一号地", 120, "已完工", 100.0),
                    ("TASK-102", "东区高精度小麦播种", "东区一号地", 85, "执行中", 42.5),
                    ("TASK-103", "北区水稻全覆盖植保除草", "北区水田A", 150, "队列中", 0.0),
                    ("TASK-104", "南区油菜籽全自动收割", "南区坡地", 220, "队列中", 0.0)
                ]
                self.cursor.executemany("INSERT INTO field_tasks VALUES (?,?,?,?,?,?)", task_seeds)
                
            # 3. 注入矢量电子隔离网多边形初始序列
            self.cursor.execute("SELECT COUNT(*) FROM field_fences")
            if self.cursor.fetchone()[0] == 0:
                points_fence_a = [(116.4050, 39.9050), (116.4150, 39.9050), (116.4150, 39.9120), (116.4050, 39.9120)]
                points_fence_b = [(116.4300, 39.9300), (116.4450, 39.9300), (116.4420, 39.9450), (116.4280, 39.9420)]
                
                fence_seeds = [
                    ("红线禁区-一号", "高压输电线杆防护带", json.dumps(points_fence_a)),
                    ("红线禁区-二号", "深水排灌渠高危区", json.dumps(points_fence_b))
                ]
                self.cursor.executemany("INSERT INTO field_fences VALUES (?,?,?)", fence_seeds)

            # 4. 注入加注站资产记录
            self.cursor.execute("SELECT COUNT(*) FROM field_stations")
            if self.cursor.fetchone()[0] == 0:
                station_seeds = [
                    ("STATION-01", "东区一号移动加注车", "移动式油电混合车", 116.3910, 39.8850, 1800.0),
                    ("STATION-02", "北区水田固定充能站", "固定式常规电站", 116.4620, 39.9410, 3500.0),
                    ("STATION-03", "南区合作社核心储油罐", "固定式标准油库", 116.4150, 39.9250, 6000.0)
                ]
                self.cursor.executemany("INSERT INTO field_stations VALUES (?,?,?,?,?,?)", station_seeds)

            # 5. 注入设备异常历史工单底账
            self.cursor.execute("SELECT COUNT(*) FROM field_maintain_logs")
            if self.cursor.fetchone()[0] == 0:
                maintain_seeds = [
                    ("工单-801", "Machinery-01", "历史故障：车载总线偶发性断流，主阀阻尼过载，已更换传感器闭环。", "2026-06-01 10:22:00", "已归档闭环", "张晓刚"),
                    ("工单-802", "Machinery-02", "突发停机：主泵反馈压严重跌落低于红线值，电池留存处于严重欠压临界区。", "2026-06-04 11:15:00", "等待指派", "未指派工程师"),
                    ("工单-803", "Machinery-04", "突发停机：传动阀总成阻抗系数突变，北斗定位锁定卫星数跌落安全阈值。", "2026-06-04 14:32:10", "正在协同维修", "王建国")
                ]
                self.cursor.executemany("INSERT INTO field_maintain_logs VALUES (?,?,?,?,?,?)", maintain_seeds)

            # 6. 注入历史轨迹回放空间点阵
            self.cursor.execute("SELECT COUNT(*) FROM field_historical_tracks")
            if self.cursor.fetchone()[0] == 0:
                track_seeds_all = []
                base_time = time.time() - 3600
                
                for idx in range(22):
                    t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(base_time + idx * 10))
                    offset_x = 0.0018 * math.sin(idx * 0.3) + idx * 0.0010
                    offset_y = 0.0020 * math.cos(idx * 0.3) + idx * 0.0005
                    track_seeds_all.append(("Machinery-01", t_str, 116.4000 + offset_x, 39.9000 + offset_y))
                
                for idx in range(15):
                    t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(base_time + 1000 + idx * 12))
                    track_seeds_all.append(("Machinery-02", t_str, 116.4200 + idx * 0.0015, 39.9100 + idx * 0.0011))

                self.cursor.executemany("INSERT INTO field_historical_tracks (node_id, recorded_time, pos_x, pos_y) VALUES (?,?,?,?)", track_seeds_all)

            # 7. 注入无线物联网微气象环境网点
            self.cursor.execute("SELECT COUNT(*) FROM field_weather_points")
            if self.cursor.fetchone()[0] == 0:
                weather_seeds = [
                    ("气象点-01", "东区一号高产小麦基地", 3.2, 12.5, 45.2, "常规态势"),
                    ("气象点-02", "北区低洼水田连片作业带", 16.8, 92.4, 88.6, "突发暴雨禁行预警"),
                    ("气象点-03", "南区坡地合作社机械化示范区", 5.4, 2.0, 31.5, "常规态势")
                ]
                self.cursor.executemany("INSERT INTO field_weather_points VALUES (?,?,?,?,?,?)", weather_seeds)

            self.conn.commit()
        except:
            if self.conn:
                self.conn.rollback()

    def execute_query(self, sql, params=()):
        """
        底层标准解耦只读读取事务
        """
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except:
            return []

    def execute_update(self, sql, params=()):
        """
        底层标准解耦强持久化数据链改写事务
        """
        try:
            self.cursor.execute(sql, params)
            self.conn.commit()
            return True
        except:
            if self.conn:
                self.conn.rollback()
            return False

    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except:
            pass