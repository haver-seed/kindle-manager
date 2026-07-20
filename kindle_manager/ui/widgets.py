from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)


class SearchBar(QWidget):
    text_changed = Signal(str)

    def __init__(self, placeholder: str = "搜索…", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.input = QLineEdit()
        self.input.setObjectName("searchInput")
        self.input.setPlaceholderText(placeholder)
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self.text_changed.emit)
        layout.addWidget(self.input)


class SidebarButton(QPushButton):
    def __init__(self, text: str, icon: str, parent=None):
        super().__init__(parent)
        self.setText(f"{icon}    {text}")
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("navButton")


class Sidebar(QWidget):
    navigation_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(224)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 24, 18, 20)
        layout.setSpacing(6)

        brand = QHBoxLayout()
        mark = QLabel("K")
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(38, 38)
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("Kindle")
        name.setObjectName("brandName")
        manager = QLabel("LIBRARY MANAGER")
        manager.setObjectName("brandCaption")
        brand_text.addWidget(name)
        brand_text.addWidget(manager)
        brand.addLayout(brand_text)
        brand.addStretch()
        layout.addLayout(brand)
        layout.addSpacing(30)

        section = QLabel("LIBRARY")
        section.setObjectName("sidebarSection")
        layout.addWidget(section)

        self.buttons: list[SidebarButton] = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        items = [
            ("书架", "▦"),
            ("笔记", "✎"),
            ("生词", "Aa"),
            ("统计", "◒"),
            ("格式工具", "⇄"),
        ]
        for index, (text, icon) in enumerate(items):
            button = SidebarButton(text, icon)
            self._button_group.addButton(button, index)
            button.setChecked(index == 0)
            self.buttons.append(button)
            layout.addWidget(button)
        self._button_group.idClicked.connect(self.navigation_changed.emit)
        layout.addStretch()

        self.device_card = QFrame()
        self.device_card.setObjectName("deviceCard")
        device_layout = QVBoxLayout(self.device_card)
        device_layout.setContentsMargins(14, 12, 14, 12)
        device_layout.setSpacing(4)
        self.device_heading = QLabel("●  DEVICE")
        self.device_heading.setObjectName("deviceHeading")
        self.device_text = QLabel("正在检测设备")
        self.device_text.setObjectName("deviceText")
        self.device_text.setWordWrap(True)
        device_layout.addWidget(self.device_heading)
        device_layout.addWidget(self.device_text)
        layout.addWidget(self.device_card)

        version = QLabel("Kindle Manager  ·  0.2")
        version.setObjectName("versionLabel")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

    def set_connection(self, state: str, text: str):
        colors = {
            "connected": "#77D1AE",
            "loading": "#E1B56F",
            "disconnected": "#D98B83",
        }
        self.device_heading.setText("●  DEVICE")
        self.device_heading.setStyleSheet(f"color: {colors.get(state, '#AAB7B1')};")
        self.device_text.setText(text)


class PlaceholderView(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("emptyState")
        layout.addWidget(label)
