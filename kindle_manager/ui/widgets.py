from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QFrame, QButtonGroup,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class SearchBar(QWidget):
    text_changed = Signal(str)

    def __init__(self, placeholder: str = "搜索...", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self.text_changed.emit)
        layout.addWidget(self.input)


class SidebarButton(QPushButton):
    def __init__(self, text: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}  {text}")
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                color: #8a8075;
                background: transparent;
            }
            QPushButton:hover {
                background: #e8e0d4;
                color: #5a5045;
            }
            QPushButton:checked {
                background: #7a9a7a;
                color: #ffffff;
                font-weight: bold;
            }
        """)


class Sidebar(QWidget):
    navigation_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setStyleSheet("background: #ede7db;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        title = QLabel("Kindle Manager")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setStyleSheet("color: #4a4038; padding: 8px 12px;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #d5cebf;")
        layout.addWidget(line)
        layout.addSpacing(8)

        self.buttons: list[SidebarButton] = []
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        items = [
            ("书架", "📚"),
            ("笔记", "📝"),
            ("词库", "📖"),
            ("统计", "📊"),
            ("格式", "📄"),
        ]
        for i, (text, icon) in enumerate(items):
            btn = SidebarButton(text, icon)
            self._btn_group.addButton(btn, i)
            btn.setChecked(i == 0)
            self.buttons.append(btn)
            layout.addWidget(btn)

        self._btn_group.idClicked.connect(self.navigation_changed.emit)

        layout.addStretch()

        version = QLabel("v0.1.0")
        version.setStyleSheet("color: #b0a898; padding: 8px 12px; font-size: 11px;")
        layout.addWidget(version)


class PlaceholderView(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 16px;")
        layout.addWidget(label)
