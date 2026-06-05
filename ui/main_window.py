import os
import importlib
import sys
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QListWidget, QStackedWidget, QPushButton, QVBoxLayout, QLabel, QStatusBar
from PyQt6.QtCore import QFileSystemWatcher, QTimer

class FleetSchedulerPlatform(QMainWindow):
    def __init__(self, operator_name, login_gate_instance=None):
        super().__init__()
        self.operator = operator_name
        self.login_gate = login_gate_instance  # 持有登录窗口的引用以便注销时回滚
        self.setWindowTitle("无人农机调度管理平台")
        self.resize(1200, 750)
        
        self.module_registry = {}
        self.init_base_layout()
        self.apply_platform_theme()
        
        # 初始化核心自动化组件：智能文件系统看门狗（实现无需点击的自动热更新）
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self.handle_automatic_hot_reload)
        
        # 首次加载模块
        self.execute_core_load()

    def init_base_layout(self):
        main_widget = QWidget()
        main_widget.setObjectName("CentralWidget")
        self.setCentralWidget(main_widget)
        
        master_layout = QHBoxLayout(main_widget)
        master_layout.setContentsMargins(15, 15, 15, 15)
        master_layout.setSpacing(15)
        
        # 左侧控制面板
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)
        
        menu_title = QLabel("系统核心业务架构")
        menu_title.setObjectName("MenuTitle")
        
        self.menu_list = QListWidget()
        self.menu_list.setObjectName("MenuSubList")
        self.menu_list.setFixedWidth(240)
        self.menu_list.currentRowChanged.connect(self.switch_view)
        
        # 保留手动按钮作为冗余备用，文字改为更严谨的表达
        self.reload_btn = QPushButton("强制全量重载总线")
        self.reload_btn.setObjectName("ReloadBtn")
        self.reload_btn.clicked.connect(self.execute_core_load)
        
        # 新增右上角或侧边栏底部的工业风退出注销按钮
        self.logout_btn = QPushButton("注销当前安全凭证")
        self.logout_btn.setObjectName("LogoutBtn")
        self.logout_btn.clicked.connect(self.execute_logout_sequence)
        
        sidebar.addWidget(menu_title)
        sidebar.addWidget(self.menu_list)
        sidebar.addWidget(self.reload_btn)
        sidebar.addWidget(self.logout_btn)
        
        # 右侧工作区
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")
        
        master_layout.addLayout(sidebar)
        master_layout.addWidget(self.content_stack, stretch=1)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(False)
        
        operator_lbl = QLabel(f"全权限操作员: {self.operator}  |  通信链路: 北斗双向授时正常 ")
        operator_lbl.setObjectName("StatusBarOperator")
        self.status_bar.addPermanentWidget(operator_lbl)

    def apply_platform_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#CentralWidget {
                background-color: #0E1217;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QStatusBar {
                background-color: #121820;
                border-top: 1px solid #1E2733;
                color: #6C7A8C;
                font-size: 11px;
            }
            QLabel#StatusBarOperator {
                color: #00FFCC;
                font-size: 11px;
                padding-right: 10px;
            }
            QLabel#MenuTitle {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
                padding-left: 5px;
                border-left: 3px solid #00FFCC;
            }
            QListWidget#MenuSubList {
                background-color: #121820;
                border: 1px solid #1E2733;
                border-radius: 2px;
                padding: 5px;
            }
            QListWidget#MenuSubList::item {
                color: #B0B5BC;
                padding: 10px 12px;
                border-radius: 2px;
                margin-bottom: 4px;
                font-size: 13px;
            }
            QListWidget#MenuSubList::item:hover {
                background-color: #1C2532;
                color: #FFFFFF;
            }
            QListWidget#MenuSubList::item:selected {
                background-color: #005F50;
                color: #00FFCC;
                font-weight: bold;
            }
            QPushButton#ReloadBtn {
                background-color: #202936;
                border: 1px solid #313F54;
                color: #909BB0;
                padding: 10px 0px;
                border-radius: 2px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#ReloadBtn:hover {
                background-color: #2A3749;
                border: 1px solid #455873;
                color: #FFFFFF;
            }
            QPushButton#LogoutBtn {
                background-color: #2A1F25;
                border: 1px solid #4A323D;
                color: #FF8888;
                padding: 10px 0px;
                border-radius: 2px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#LogoutBtn:hover {
                background-color: #3D222E;
                color: #FF4444;
            }
            QStackedWidget#ContentStack {
                background-color: #121820;
                border: 1px solid #1E2733;
                border-radius: 2px;
            }
        """)

    def execute_core_load(self):
        """
        全量扫描核心加载程序，同时动态向底层看门狗注册文件路径
        """
        current_row = self.menu_list.currentRow()
        
        # 取消对旧文件的监听以防冲突
        existing_watched = self.file_watcher.files()
        if existing_watched:
            self.file_watcher.removePaths(existing_watched)

        self.menu_list.clear()
        while self.content_stack.count() > 0:
            widget = self.content_stack.widget(0)
            self.content_stack.removeWidget(widget)
            widget.deleteLater()

        self.module_registry.clear()
        
        module_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'modules')
        sys.path.insert(0, module_dir)

        files = [f for f in os.listdir(module_dir) if f.startswith('m') and f.endswith('.py')]
        files.sort()

        for file in files:
            module_name = file[:-3]
            full_path = os.path.join(module_dir, file)
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)
                
                mod = sys.modules[module_name]
                if hasattr(mod, 'ModuleEntry'):
                    instance = mod.ModuleEntry()
                    title = instance.get_module_title()
                    
                    self.module_registry[title] = instance
                    self.menu_list.addItem(title)
                    self.content_stack.addWidget(instance)
                    
                    # 将该子模块的物理磁盘路径动态绑入监听网络
                    self.file_watcher.addPath(full_path)
            except Exception as e:
                print(f"加载模块异常 {module_name}: {e}")

        if current_row >= 0 and current_row < self.menu_list.count():
            self.menu_list.setCurrentRow(current_row)
        else:
            self.menu_list.setCurrentRow(0)

    def handle_automatic_hot_reload(self, path):
        """
        看门狗异步回调事件：当检测到外部代码编辑器执行了Ctrl+S保存，触发无感秒级动态倒装
        """
        # 延迟100ms执行，防止部分编辑器分两步写入导致文件暂时空置产生的读取冲突
        QTimer.singleShot(100, self.execute_core_load)
        self.status_bar.showMessage(f"内核感知：检测到模块修改 [{os.path.basename(path)}]，已自动完成实时无感热更新", 4000)

    def execute_logout_sequence(self):
        """
        核心解耦注销逻辑：平滑释放主看板资产，并重组登录认证门禁
        """
        if self.login_gate:
            self.close()  # 关闭主调度窗体
            self.login_gate.auto_fill_credentials()  # 恢复默认填空
            self.login_gate.show()  # 重新唤醒安全认证页
        else:
            self.status_bar.showMessage("注销失败：回滚路由丢失", 3000)

    def switch_view(self, index):
        if index >= 0:
            self.content_stack.setCurrentIndex(index)