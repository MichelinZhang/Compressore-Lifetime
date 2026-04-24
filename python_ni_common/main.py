import sys
from PyQt6.QtWidgets import QApplication
from modules.ui_main import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())