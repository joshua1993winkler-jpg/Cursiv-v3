import sys
import os
from PyQt6.QtWidgets import QApplication
from cursiv_launcher import CursivLauncher

def main():
    # Change to the launcher directory so relative paths work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QApplication(sys.argv)
    app.setApplicationName("Cursiv v3.0")
    app.setApplicationVersion("3.0.0")

    window = CursivLauncher()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()