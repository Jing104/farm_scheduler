import sys
from PyQt6.QtWidgets import QApplication
from ui.login import LoginStage
from ui.main_window import FleetSchedulerPlatform

def launch_application():
    app = QApplication(sys.argv)
    
    login_gate = LoginStage()
    main_window = None

    def transit_to_platform(authenticated_user):
        nonlocal main_window
        login_gate.close()
        # 将 login_gate 本身作为参数注入主平台，形成回溯路由
        main_window = FleetSchedulerPlatform(authenticated_user, login_gate)
        main_window.show()

    login_gate.login_success.connect(transit_to_platform)
    login_gate.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_application()