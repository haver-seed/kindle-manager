import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from kindle_manager.ui.main_window import MainWindow, detect_kindle


def _resource_path(relative: str) -> Path:
    """Get resource path, works for dev and PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent
    return base / relative


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Kindle Manager")
    app.setFont(QFont("Microsoft YaHei", 9))

    qss_path = _resource_path("resources/style.qss")
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    kindle_path = detect_kindle()
    window = MainWindow(kindle_path=kindle_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
