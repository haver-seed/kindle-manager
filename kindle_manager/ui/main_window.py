import string
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget,
    QStatusBar, QMessageBox, QLabel,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont

from kindle_manager.core.scanner import scan_kindle
from kindle_manager.ui.widgets import Sidebar
from kindle_manager.ui.book_list import BookListView
from kindle_manager.ui.notes_view import NotesView
from kindle_manager.ui.vocab_view import VocabView
from kindle_manager.ui.stats_view import StatsView
from kindle_manager.ui.format_guide import FormatGuideView

BG = "#faf6f0"
STATUS_BG = "#f0ece4"
TEXT = "#3d3830"
MUTED = "#8a8075"
ACCENT = "#7a9a7a"
GREEN = "#5a9a6a"
RED = "#c06050"


def detect_kindle() -> str | None:
    """Auto-detect Kindle drive by scanning all drives for Kindle-specific markers."""
    for letter in string.ascii_uppercase:
        drive = f"{letter}:/"
        try:
            p = Path(drive)
            if not p.exists():
                continue
            # Kindle signature: /documents + /system folders + version file
            ver_file = p / "system" / "version.txt"
            if (p / "documents").is_dir() and ver_file.exists():
                try:
                    content = ver_file.read_text(encoding="utf-8", errors="ignore")
                    if content.startswith("Kindle"):
                        return drive
                except Exception:
                    continue
        except Exception:
            continue
    return None


class _ConnectionIndicator(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_connected(False)

    def set_connected(self, connected: bool):
        if connected:
            self.setText(
                f"<span style='color:{GREEN}; font-size:18px;'>&#9679;</span>"
                f"<span style='color:{TEXT}; font-size:15px; font-weight:bold;'>"
                f" 已连接 Kindle</span>"
            )
        else:
            self.setText(
                f"<span style='color:{RED}; font-size:18px;'>&#9679;</span>"
                f"<span style='color:{TEXT}; font-size:15px; font-weight:bold;'>"
                f" 未连接 Kindle</span>"
            )
        self.setTextFormat(Qt.RichText)


class MainWindow(QMainWindow):
    def __init__(self, kindle_path: str | None = None):
        super().__init__()
        self.kindle_path = kindle_path
        self.books = []
        self._indicator = _ConnectionIndicator()
        self._setup_ui()
        self._connect_signals()
        QTimer.singleShot(200, self._scan_kindle)

    def _setup_ui(self):
        self.setWindowTitle("Kindle Manager")
        self.setMinimumSize(1050, 680)
        self.resize(1250, 780)
        self.setStyleSheet(f"QMainWindow {{ background: {BG}; }}")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.book_list_view = BookListView(kindle_path=self.kindle_path or "")
        self.stack.addWidget(self.book_list_view)
        self.notes_view = NotesView()
        self.stack.addWidget(self.notes_view)
        self.vocab_view = VocabView()
        self.stack.addWidget(self.vocab_view)
        self.stats_view = StatsView()
        self.stack.addWidget(self.stats_view)
        self.format_guide_view = FormatGuideView()
        self.stack.addWidget(self.format_guide_view)
        main_layout.addWidget(self.stack, 1)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ background: {STATUS_BG}; color: {MUTED}; "
            "border-top: 1px solid #e0d8c8; font-size: 12px; }"
        )
        self.status_bar.addWidget(self._indicator)
        self.setStatusBar(self.status_bar)

    def _connect_signals(self):
        self.sidebar.navigation_changed.connect(self.stack.setCurrentIndex)
        self.book_list_view.book_selected.connect(self._on_book_selected)
        self.book_list_view.refresh_requested.connect(self._scan_kindle)
        self.format_guide_view.conversion_done.connect(self._scan_kindle)

    def _scan_kindle(self):
        # Re-detect drive if needed
        if not self.kindle_path or not Path(self.kindle_path).exists():
            self.kindle_path = detect_kindle()

        if not self.kindle_path:
            self._indicator.set_connected(False)
            self.status_bar.showMessage("未检测到 Kindle 设备")
            self.format_guide_view.set_books([])
            return

        self._indicator.set_connected(True)
        self.status_bar.showMessage("正在扫描 Kindle...")

        try:
            self.books = scan_kindle(self.kindle_path)
        except FileNotFoundError:
            self.books = []

        self.book_list_view.kindle_path = self.kindle_path
        self.book_list_view.set_books(self.books)

        try:
            self.notes_view.load_clippings(self.kindle_path)
        except Exception:
            pass
        try:
            self.vocab_view.load_vocab(self.kindle_path)
        except Exception:
            pass

        self.stats_view.set_data(
            self.books,
            len(self.notes_view.clippings),
            len(self.vocab_view.words),
        )
        self.format_guide_view.set_books(self.books)
        self.status_bar.showMessage(
            f"Kindle ({self.kindle_path}) — {len(self.books)} 本书"
        )

    def _on_book_selected(self, book):
        self.status_bar.showMessage(
            f"{book.title} | {book.format_display} | {book.size_display}"
        )
