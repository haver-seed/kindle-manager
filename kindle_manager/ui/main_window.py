import string
import sqlite3
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from kindle_manager.core.clippings import parse_clippings
from kindle_manager.core.scanner import scan_kindle
from kindle_manager.core.vocabulary import read_vocabulary
from kindle_manager.ui.book_list import BookListView
from kindle_manager.ui.format_guide import FormatGuideView
from kindle_manager.ui.notes_view import NotesView
from kindle_manager.ui.stats_view import StatsView
from kindle_manager.ui.vocab_view import VocabView
from kindle_manager.ui.widgets import Sidebar
from kindle_manager.ui.workers import TaskWorker


def detect_kindle() -> str | None:
    """Auto-detect a mounted Kindle without assuming one drive layout."""
    for letter in string.ascii_uppercase:
        drive = f"{letter}:/"
        try:
            root = Path(drive)
            if not root.exists() or not (root / "documents").is_dir():
                continue
            version = root / "system" / "version.txt"
            if version.exists():
                content = version.read_text(encoding="utf-8", errors="ignore")
                if content.startswith("Kindle"):
                    return drive
            # Some models hide the version file but expose both standard folders.
            if (root / "system").is_dir():
                return drive
        except OSError:
            continue
    return None


def _load_snapshot(requested_path: str | None) -> dict:
    path = requested_path if requested_path and Path(requested_path).exists() else detect_kindle()
    if not path:
        return {"path": None, "books": [], "clippings": [], "words": [], "warnings": []}
    warnings: list[str] = []
    books = scan_kindle(path)
    try:
        clippings = parse_clippings(path)
    except (FileNotFoundError, OSError) as exc:
        clippings = []
        warnings.append(str(exc))
    try:
        words = read_vocabulary(path)
    except (FileNotFoundError, OSError, sqlite3.Error) as exc:
        words = []
        warnings.append(str(exc))
    return {"path": path, "books": books, "clippings": clippings, "words": words, "warnings": warnings}


class MainWindow(QMainWindow):
    PAGE_META = [
        ("我的书架", "浏览、筛选并安全管理设备上的书籍"),
        ("阅读笔记", "按书籍整理 Kindle 标注、书签与随手记"),
        ("生词本", "回看查询过的单词与原文语境"),
        ("阅读概览", "了解藏书组成、空间占用与阅读足迹"),
        ("格式工具", "转换本地电子书并了解设备兼容性"),
    ]

    def __init__(self, kindle_path: str | None = None):
        super().__init__()
        self.kindle_path = kindle_path
        self.books = []
        self._scan_worker = None
        self._setup_ui()
        self._connect_signals()
        QTimer.singleShot(100, self._scan_kindle)

    def _setup_ui(self):
        self.setWindowTitle("Kindle Manager")
        self.setMinimumSize(1080, 700)
        self.resize(1320, 820)

        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        workspace = QWidget()
        workspace.setObjectName("workspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(30, 22, 30, 24)
        workspace_layout.setSpacing(18)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.scan_status = QLabel("准备连接设备")
        self.scan_status.setObjectName("scanStatus")
        header.addWidget(self.scan_status)
        self.refresh_button = QPushButton("↻  刷新设备")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self._scan_kindle)
        header.addWidget(self.refresh_button)
        workspace_layout.addLayout(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("divider")
        workspace_layout.addWidget(divider)

        self.stack = QStackedWidget()
        self.book_list_view = BookListView(kindle_path=self.kindle_path or "")
        self.notes_view = NotesView()
        self.vocab_view = VocabView()
        self.stats_view = StatsView()
        self.format_guide_view = FormatGuideView()
        for view in (
            self.book_list_view, self.notes_view, self.vocab_view,
            self.stats_view, self.format_guide_view,
        ):
            self.stack.addWidget(view)
        workspace_layout.addWidget(self.stack, 1)
        root.addWidget(workspace, 1)
        self._set_page(0)

    def _connect_signals(self):
        self.sidebar.navigation_changed.connect(self._set_page)
        self.book_list_view.book_selected.connect(self._on_book_selected)
        self.book_list_view.refresh_requested.connect(self._scan_kindle)
        self.book_list_view.book_deleted.connect(self._scan_kindle)
        self.format_guide_view.conversion_done.connect(self._scan_kindle)

    def _set_page(self, index: int):
        self.stack.setCurrentIndex(index)
        title, subtitle = self.PAGE_META[index]
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)

    def _scan_kindle(self):
        if self._scan_worker is not None:
            return
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("正在扫描…")
        self.scan_status.setText("正在读取 Kindle")
        self.sidebar.set_connection("loading", "正在扫描设备")
        self._scan_worker = TaskWorker(_load_snapshot, self.kindle_path)
        self._scan_worker.signals.result.connect(self._apply_snapshot)
        self._scan_worker.signals.error.connect(self._scan_error)
        self._scan_worker.signals.finished.connect(self._scan_finished)
        QThreadPool.globalInstance().start(self._scan_worker)

    def _apply_snapshot(self, snapshot: dict):
        self.kindle_path = snapshot["path"]
        self.books = snapshot["books"]
        path = self.kindle_path or ""
        self.book_list_view.kindle_path = path
        self.book_list_view.set_books(self.books)
        self.notes_view.set_clippings(snapshot["clippings"], path)
        self.vocab_view.set_words(snapshot["words"])
        self.stats_view.set_data(self.books, len(snapshot["clippings"]), len(snapshot["words"]))
        self.format_guide_view.set_books(self.books)
        if path:
            self.sidebar.set_connection("connected", f"Kindle · {path}")
            self.scan_status.setText(f"{len(self.books)} 本书 · 已连接")
        else:
            self.sidebar.set_connection("disconnected", "未检测到 Kindle")
            self.scan_status.setText("连接 Kindle 后点击刷新")

    def _scan_error(self, details: str):
        self._clear_device_state()
        message = details.splitlines()[-1] if details else "未知错误"
        QMessageBox.warning(self, "扫描失败", f"读取设备时发生错误：\n{message}")

    def _scan_finished(self):
        self._scan_worker = None
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("↻  刷新设备")

    def _clear_device_state(self):
        self.kindle_path = None
        self.books = []
        self.book_list_view.kindle_path = ""
        self.book_list_view.set_books([])
        self.notes_view.set_clippings([], "")
        self.vocab_view.set_words([])
        self.stats_view.set_data([], 0, 0)
        self.format_guide_view.set_books([])
        self.sidebar.set_connection("disconnected", "设备连接已断开")
        self.scan_status.setText("未连接")

    def _on_book_selected(self, book):
        self.scan_status.setText(f"{book.format_display} · {book.size_display} · {book.title[:34]}")
