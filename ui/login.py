from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QFrame
from PyQt6.QtCore import pyqtSignal, Qt
from core.auth import SessionManager

class LoginStage(QWidget):
    login_success = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.auth_engine = SessionManager()
        self.init_interface()
        self.apply_advanced_theme()
        self.auto_fill_credentials()

    def init_interface(self):
        self.setWindowTitle("无人农机调度系统 - 全局控制台中心认证")
        self.setFixedSize(760, 420)  # 拓宽窗体，改为双面板专业布局
        
        # 全局横向主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ------------------ 左侧：数据与系统状态面板 ------------------
        left_panel = QFrame()
        left_panel.setObjectName("LeftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(35, 40, 35, 40)
        left_layout.setSpacing(18)

        brand_title = QLabel("无人农机一体化智能调度系统")
        brand_title.setObjectName("BrandTitle")
        
        system_desc = QLabel("国家级数字化农事服务网核心中枢\n北斗三号高精度动态时空授时解算内核")
        system_desc.setObjectName("SystemDesc")
        
        # 增加几行体现专业业务深度的虚拟监控指标（非系统配置）
        status_frame = QFrame()
        status_frame.setObjectName("StatusFrame")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(8)
        
        s1 = QLabel("中心全网状态： 边缘侧计算节点就绪")
        s2 = QLabel("北斗基准站源： 地面增补差分站同步中")
        s3 = QLabel("冲突重规划内核： 动态拓扑矩阵已加载")
        for s in [s1, s2, s3]:
            s.setObjectName("StatusText")
            status_layout.addWidget(s)

        left_layout.addWidget(brand_title)
        left_layout.addWidget(system_desc)
        left_layout.addStretch()
        left_layout.addWidget(status_frame)
        
        # ------------------ 右侧：凭证鉴权交互表单 ------------------
        right_panel = QFrame()
        right_panel.setObjectName("RightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(40, 50, 40, 50)
        right_layout.setSpacing(20)

        form_title = QLabel("操作员安全鉴权")
        form_title.setObjectName("FormTitle")
        form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("请输入系统操作员账户")
        self.user_input.setMaxLength(20)

        self.pwd_input = QLineEdit()
        self.pwd_input.setPlaceholderText("请输入全权限访问密钥")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setMaxLength(32)

        # 按钮横向布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_login = QPushButton("授权登录")
        self.btn_reg = QPushButton("注册凭证")
        self.btn_login.setObjectName("BtnLogin")
        self.btn_reg.setObjectName("BtnReg")
        
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_reg)

        right_layout.addWidget(form_title)
        right_layout.addSpacing(right_layout.spacing() * 2)
        right_layout.addWidget(self.user_input)
        right_layout.addWidget(self.pwd_input)
        right_layout.addStretch()
        right_layout.addLayout(btn_layout)

        # 组装双面板
        main_layout.addWidget(left_panel, stretch=11)
        main_layout.addWidget(right_panel, stretch=10)

        # 事件信号绑定
        self.btn_login.clicked.connect(self.execute_login)
        self.btn_reg.clicked.connect(self.execute_register)

    def apply_advanced_theme(self):
        """
        全屏幕高级工业级控制台QSS：引入钛金灰、极光青及暗底半透悬浮微晶风格
        """
        self.setStyleSheet("""
            QWidget {
                background-color: #0E1217;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                color: #B0B5BC;
            }
            
            /* 左侧专业数据面板样式 */
            QFrame#LeftPanel {
                background-color: #121820;
                border-right: 1px solid #1E2733;
            }
            QLabel#BrandTitle {
                font-size: 20px;
                font-weight: bold;
                color: #00FFCC;
                letter-spacing: 1px;
            }
            QLabel#SystemDesc {
                font-size: 12px;
                color: #6C7A8C;
                line-height: 18px;
            }
            QFrame#StatusFrame {
                background-color: #16202C;
                border: 1px solid #223143;
                border-radius: 4px;
                padding: 10px;
            }
            QLabel#StatusText {
                font-size: 11px;
                color: #8A9BB0;
            }
            
            /* 右侧表单鉴权面板样式 */
            QFrame#RightPanel {
                background-color: #0E1217;
            }
            QLabel#FormTitle {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                letter-spacing: 3px;
                border-bottom: 2px solid #00FFCC;
                padding-bottom: 8px;
            }
            
            /* 输入框精细化交互 */
            QLineEdit {
                background-color: #181F2A;
                border: 1px solid #2D3A4B;
                border-radius: 2px;
                padding: 10px 14px;
                font-size: 13px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 1px solid #00FFCC;
                background-color: #1C2635;
            }
            
            /* 按钮控制组 */
            QPushButton {
                border-radius: 2px;
                padding: 10px 0px;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton#BtnLogin {
                background-color: #007A66;
                border: 1px solid #009980;
                color: #FFFFFF;
            }
            QPushButton#BtnLogin:hover {
                background-color: #009980;
                border: 1px solid #00FFCC;
            }
            QPushButton#BtnLogin:pressed {
                background-color: #005F50;
            }
            QPushButton#BtnReg {
                background-color: #202936;
                border: 1px solid #313F54;
                color: #909BB0;
            }
            QPushButton#BtnReg:hover {
                background-color: #2A3749;
                border: 1px solid #455873;
                color: #FFFFFF;
            }
            QPushButton#BtnReg:pressed {
                background-color: #171E28;
            }
        """)

    def auto_fill_credentials(self):
        self.user_input.setText("admin")
        self.pwd_input.setText("admin123")

    def validate_password_strength(self, password):
        if len(password) < 6:
            return False, "系统安全规则拒绝：密钥长度不得低于6位"
        return True, ""

    def execute_login(self):
        username = self.user_input.text().strip()
        password = self.pwd_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "认证提示", "操作员账户与访问密钥均不能为空。")
            return
            
        if self.auth_engine.authenticate(username, password):
            self.login_success.emit(username)
        else:
            QMessageBox.critical(self, "认证错误", "安全令牌校验未通过，请检查账户名或密钥。")

    def execute_register(self):
        username = self.user_input.text().strip()
        password = self.pwd_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "注册提示", "待注册的凭证信息不完整。")
            return
            
        is_valid, err_msg = self.validate_password_strength(password)
        if not is_valid:
            QMessageBox.warning(self, "安全阻断", err_msg)
            return

        status, msg = self.auth_engine.register_user(username, password)
        if status:
            QMessageBox.information(self, "注册成功", "系统安全凭证已成功下发至本地数据层。")
        else:
            QMessageBox.warning(self, "注册终止", "该账户名称在调度系统中已存在。")