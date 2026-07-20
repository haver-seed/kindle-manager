from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QScrollArea, QLabel,
    QPushButton, QFileDialog, QMessageBox, QFrame, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from kindle_manager.core.clippings import parse_clippings, group_by_book, remove_clipping
from kindle_manager.core.exporter import export_markdown, export_csv, export_json
from kindle_manager.models.clipping import Clipping
from kindle_manager.ui.theme import ACCENT, ACCENT_SOFT, BG, BORDER, GOLD, MUTED, SURFACE, TEXT

# Cream light palette
CARD_BG = SURFACE
SIDEBAR_BG = SURFACE
ACCENT2 = GOLD
BADGE_BG = ACCENT_SOFT
BADGE_TEXT = ACCENT


class NotesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clippings: list[Clipping] = []
        self.groups: dict[str, list[Clipping]] = {}
        self._all_books: list[str] = []
        self._kindle_path: str = ""
        self._current_book: str = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        header.addWidget(self.count_label)
        header.addStretch()

        btn_style = f"""
            QPushButton {{
                background: {ACCENT}; color: #fff; border: none;
                border-radius: 4px; padding: 6px 14px; font-size: 12px;
            }}
            QPushButton:hover {{ background: #8aae8a; }}
        """
        for label, slot in [("导出 MD", self._export_md),
                            ("导出 CSV", self._export_csv),
                            ("导出 JSON", self._export_json)]:
            btn = QPushButton(label)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            header.addWidget(btn)

        layout.addLayout(header)

        # Splitter: book list | clipping cards
        splitter = QSplitter(Qt.Horizontal)

        # Left: book list
        self.book_list = QListWidget()
        self.book_list.setMaximumWidth(260)
        self.book_list.setMinimumWidth(220)
        self.book_list.itemClicked.connect(self._on_book_clicked)
        splitter.addWidget(self.book_list)

        # Right: clipping cards in scroll area
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(0)

        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cards_widget)
        scroll.setStyleSheet(f"QScrollArea {{ background: {BG}; border: none; }}")
        right_layout.addWidget(scroll)

        self._empty_label = QLabel("← 选择一本书查看笔记")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {MUTED}; font-size: 15px; padding: 60px;")
        right_layout.addWidget(self._empty_label)

        splitter.addWidget(right)
        layout.addWidget(splitter, 1)

    def load_clippings(self, kindle_path: str):
        self._kindle_path = kindle_path
        try:
            self.set_clippings(parse_clippings(kindle_path), kindle_path)
        except FileNotFoundError:
            self.set_clippings([], kindle_path)

    def set_clippings(self, clippings: list[Clipping], kindle_path: str = ""):
        self._kindle_path = kindle_path
        self.clippings = clippings
        self.groups = group_by_book(self.clippings)
        self._all_books = sorted(self.groups.keys())
        self._populate_book_list()
        if self.clippings:
            self.count_label.setText(f"{len(self.clippings)} 条 · {len(self.groups)} 本书")
        else:
            self._clear_cards()
            self.count_label.setText("暂无笔记")
            self._empty_label.setText("连接 Kindle 后，这里会整理你的标注与笔记")
            self._empty_label.show()

    def _populate_book_list(self):
        self.book_list.clear()
        for book_title in self._all_books:
            clips = self.groups[book_title]
            item = QListWidgetItem(f"  {book_title}")
            item.setData(Qt.UserRole, book_title)
            item.setToolTip(f"{book_title}\n{len(clips)} 条笔记")
            self.book_list.addItem(item)

        if self._all_books:
            self.book_list.setCurrentRow(0)
            self._show_clippings(self._all_books[0])

    def _on_book_clicked(self, item):
        book_title = item.data(Qt.UserRole)
        if book_title:
            self._show_clippings(book_title)

    def _show_clippings(self, book_title: str):
        self._current_book = book_title
        clips = self.groups.get(book_title, [])
        while self.cards_layout.count() > 1:
            w = self.cards_layout.takeAt(0)
            if w.widget():
                w.widget().deleteLater()

        for i, c in enumerate(sorted(clips, key=lambda x: x.date or _min_date())):
            card = _ClippingCard(c)
            card.delete_requested.connect(self._delete_clipping)
            self.cards_layout.insertWidget(i, card)

        self._empty_label.hide()

    def _clear_cards(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _delete_clipping(self, clipping: Clipping):
        reply = QMessageBox.question(
            self, "删除这条笔记？",
            "将从 My Clippings.txt 中删除匹配记录，并自动保留 .bak 备份。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            removed = remove_clipping(self._kindle_path, clipping)
            if not removed:
                QMessageBox.warning(self, "未删除", "没有在原始文件中找到匹配记录。")
                return
            self.load_clippings(self._kindle_path)
        except OSError as exc:
            QMessageBox.critical(self, "删除失败", f"未修改笔记文件：\n{exc}")

    def _export_md(self):
        if not self.clippings:
            return
        d = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if d:
            export_markdown(self.clippings, d)
            QMessageBox.information(self, "导出完成", f"笔记已导出为 Markdown 到:\n{d}")

    def _export_csv(self):
        if not self.clippings:
            return
        p, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "kindle_notes.csv", "CSV (*.csv)")
        if p:
            export_csv(self.clippings, p)
            QMessageBox.information(self, "导出完成", f"笔记已导出为 CSV 到:\n{p}")

    def _export_json(self):
        if not self.clippings:
            return
        p, _ = QFileDialog.getSaveFileName(self, "导出 JSON", "kindle_notes.json", "JSON (*.json)")
        if p:
            export_json(self.clippings, p)
            QMessageBox.information(self, "导出完成", f"笔记已导出为 JSON 到:\n{p}")


class _ClippingCard(QFrame):
    delete_requested = Signal(object)

    def __init__(self, clipping: Clipping, parent=None):
        super().__init__(parent)
        self.clipping = clipping
        c = clipping
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.setStyleSheet(f"""
            _ClippingCard {{
                background: {CARD_BG}; border-radius: 11px;
                border: 1px solid {BORDER};
                border-left: 3px solid {ACCENT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Top row: type badge + meta
        top = QHBoxLayout()

        badge = QLabel(f" {c.type_display} ")
        badge.setStyleSheet(f"""
            QLabel {{
                background: {BADGE_BG}; color: {BADGE_TEXT}; border-radius: 3px;
                padding: 2px 10px; font-size: 11px; font-weight: bold;
            }}
        """)
        top.addWidget(badge)

        meta_parts = []
        if c.page:
            meta_parts.append(f"第 {c.page} 页")
        if c.location:
            meta_parts.append(f"位置 {c.location}")
        if c.date:
            meta_parts.append(c.date.strftime("%Y-%m-%d %H:%M"))
        meta = QLabel(" · ".join(meta_parts))
        meta.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        top.addWidget(meta)
        top.addStretch()
        layout.addLayout(top)

        # Content
        content = QLabel(c.content)
        content.setWordWrap(True)
        content.setTextFormat(Qt.PlainText)
        content.setStyleSheet(f"""
            QLabel {{
                color: {TEXT}; font-size: 14px;
                padding: 6px 0; line-height: 1.8;
            }}
        """)
        layout.addWidget(content)

    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: #fff; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}
            QMenu::item {{ padding: 8px 32px 8px 18px; }}
            QMenu::item:selected {{ background: {BADGE_BG}; }}
        """)
        act = QAction("删除此条", menu)
        act.triggered.connect(lambda: self.delete_requested.emit(self.clipping))
        menu.addAction(act)
        menu.exec(self.mapToGlobal(pos))


def _min_date():
    from datetime import datetime
    return datetime(2000, 1, 1)
