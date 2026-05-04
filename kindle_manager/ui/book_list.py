import os
import subprocess
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMenu, QMessageBox, QApplication, QScrollArea, QGridLayout,
    QFrame, QFileDialog, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy, QComboBox,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPixmap, QAction, QPainter

from kindle_manager.models.book import Book
from kindle_manager.core.clippings import parse_clippings, group_by_book
from kindle_manager.core.exporter import export_markdown
from kindle_manager.ui.widgets import SearchBar

# ── palette ──
BG = "#faf6f0"
CARD_BG = "#ffffff"
TABLE_ALT = "#f8f5ee"
TEXT = "#3d3830"
MUTED = "#8a8075"
ACCENT = "#7a9a7a"
ACCENT2 = "#c4a56a"
BORDER = "#e5ddd0"
CARD_HOVER = "#f0ebe0"
CARD_SELECTED = "#dce8d8"
HEADER_BG = "#f0ece4"

CARD_W, CARD_H, COVER_H = 140, 210, 175

_BTN = f"""
    QPushButton {{
        background: #fff; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: 4px; padding: 5px 14px; font-size: 12px;
    }}
    QPushButton:hover {{ background: #f0ebe0; }}
    QPushButton:checked {{ background: {ACCENT}; color: #fff; }}
"""

_TABLE_STYLE = f"""
    QTableWidget {{
        background: {CARD_BG}; color: {TEXT};
        border: 1px solid {BORDER}; border-radius: 4px;
        font-size: 13px; alternate-background-color: {TABLE_ALT};
    }}
    QTableWidget::item {{
        padding: 7px 10px; border-bottom: 1px solid {BORDER};
    }}
    QTableWidget::item:selected {{ background: {CARD_SELECTED}; color: {TEXT}; }}
    QTableWidget::item:hover {{ background: {CARD_HOVER}; }}
    QHeaderView::section {{
        background: {HEADER_BG}; color: {MUTED}; border: none;
        border-bottom: 2px solid {BORDER}; padding: 7px 10px;
        font-weight: bold; font-size: 12px;
    }}
"""

_MENU_STYLE = f"""
    QMenu {{
        background: #ffffff; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px;
    }}
    QMenu::item {{ padding: 7px 32px 7px 18px; }}
    QMenu::item:selected {{ background: {CARD_SELECTED}; }}
    QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
"""


# ═══════════════════════════════════════════════════════════════
# Book Card (for grid view)
# ═══════════════════════════════════════════════════════════════

class BookCard(QFrame):
    clicked = Signal(object)

    def __init__(self, book: Book, parent=None):
        super().__init__(parent)
        self.book = book
        self._selected = False
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 8)
        layout.setSpacing(4)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(CARD_W - 12, COVER_H - 8)
        self.cover_label.setAlignment(Qt.AlignCenter)

        if book.cover_path and book.cover_path.exists():
            pix = QPixmap(str(book.cover_path))
            if not pix.isNull():
                pix = pix.scaled(CARD_W - 16, COVER_H - 12, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.setText(book.title[:6])
            self.cover_label.setStyleSheet(
                f"background: #e8e2d6; color: {MUTED}; font-size: 18px; "
                "font-weight: bold; border-radius: 4px;"
            )
        layout.addWidget(self.cover_label, 0, Qt.AlignCenter)

        t = book.title[:20] + ("…" if len(book.title) > 20 else "")
        self.title_label = QLabel(t)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setFixedWidth(CARD_W - 12)
        self.title_label.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
        self.title_label.setToolTip(f"{book.title}\n{book.format_display} · {book.size_display}")
        layout.addWidget(self.title_label)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            f"BookCard {{ background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 6px; }}"
            f"BookCard:hover {{ background: {CARD_HOVER}; border: 1px solid #c5bfb2; }}"
        )

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.setStyleSheet(
                f"BookCard {{ background: {CARD_SELECTED}; "
                f"border: 2px solid {ACCENT}; border-radius: 6px; }}"
            )
        else:
            self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.book)


# ═══════════════════════════════════════════════════════════════
# Book Table (list view)
# ═══════════════════════════════════════════════════════════════

class _BookTableWidget(QWidget):
    book_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.books: list[Book] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["书名", "格式", "大小", "进度", "来源"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        hv = self.table.horizontalHeader()
        hv.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            hv.setSectionResizeMode(i, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 65)
        self.table.setColumnWidth(2, 85)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 60)
        self.table.setStyleSheet(_TABLE_STYLE)
        self.table.itemSelectionChanged.connect(self._emit_selected)
        layout.addWidget(self.table)

    def set_books(self, books: list[Book]):
        self.books = books
        self.table.setRowCount(len(books))
        for row, book in enumerate(books):
            ti = QTableWidgetItem(book.title)
            ti.setData(Qt.UserRole, book)
            ti.setToolTip(book.title)
            self.table.setItem(row, 0, ti)

            fi = QTableWidgetItem(book.format_display)
            fi.setTextAlignment(Qt.AlignCenter)
            fi.setForeground(QColor(ACCENT2 if book.is_sideloaded else ACCENT))
            self.table.setItem(row, 1, fi)

            si = QTableWidgetItem(book.size_display)
            si.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, si)

            if book.last_position > 0:
                pi = QTableWidgetItem("已读")
                pi.setForeground(QColor(ACCENT))
                pi.setToolTip(f"位置 {book.last_position}")
            else:
                pi = QTableWidgetItem("—")
                pi.setForeground(QColor(MUTED))
            pi.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, pi)

            src = "本地" if book.is_sideloaded else "商店"
            ri = QTableWidgetItem(src)
            ri.setTextAlignment(Qt.AlignCenter)
            ri.setForeground(QColor(ACCENT2 if book.is_sideloaded else ACCENT))
            self.table.setItem(row, 4, ri)

    def get_selected_book(self) -> Book | None:
        rows = self.table.selectionModel().selectedRows()
        if rows:
            return rows[0].data(Qt.UserRole)
        return None

    def _emit_selected(self):
        b = self.get_selected_book()
        if b:
            self.book_selected.emit(b)


# ═══════════════════════════════════════════════════════════════
# Book Grid (cover view)
# ═══════════════════════════════════════════════════════════════

class _BookGridWidget(QWidget):
    book_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.books: list[Book] = []
        self._cards: list[BookCard] = []
        self._selected: set[BookCard] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {BG}; border: none; }}")

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(4, 4, 4, 16)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def set_books(self, books: list[Book]):
        self.books = books
        for c in self._cards:
            c.setParent(None)
            c.deleteLater()
        self._cards.clear()
        self._selected.clear()

        cols = max(1, (self.width() - 30) // (CARD_W + 12))
        for i, book in enumerate(books):
            card = BookCard(book)
            card.clicked.connect(self._on_click)
            self._cards.append(card)
            self.grid.addWidget(card, i // cols, i % cols)

    def get_selected_book(self) -> Book | None:
        return next(iter(self._selected)).book if self._selected else None

    def get_selected_books(self) -> list[Book]:
        return [c.book for c in self._selected]

    def _on_click(self, book: Book):
        s = self.sender()
        if not isinstance(s, BookCard):
            return
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ControlModifier:
            # Toggle selection
            if s in self._selected:
                s.set_selected(False)
                self._selected.discard(s)
            else:
                s.set_selected(True)
                self._selected.add(s)
        else:
            # Single select
            for c in self._selected:
                c.set_selected(False)
            self._selected.clear()
            s.set_selected(True)
            self._selected.add(s)
        self.book_selected.emit(book)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.books:
            cols = max(1, (self.width() - 30) // (CARD_W + 12))
            for i, card in enumerate(self._cards):
                self.grid.addWidget(card, i // cols, i % cols)


# ═══════════════════════════════════════════════════════════════
# BookListView (container)
# ═══════════════════════════════════════════════════════════════

class BookListView(QWidget):
    book_selected = Signal(object)
    book_deleted = Signal()
    refresh_requested = Signal()

    def __init__(self, kindle_path: str = "", parent=None):
        super().__init__(parent)
        self.kindle_path = kindle_path
        self.books: list[Book] = []
        self._grid_mode = True
        self._refresh_overlay: QLabel | None = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._hide_refresh_overlay)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Header ──
        h = QHBoxLayout()
        title = QLabel("书架")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT};")
        h.addWidget(title)

        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        h.addWidget(self.count_label)

        combo_style = f"""
            QComboBox {{
                background: #fff; color: {TEXT}; border: 1px solid {BORDER};
                border-radius: 4px; padding: 3px 8px; font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox QAbstractItemView {{
                background: #fff; color: {TEXT};
                selection-background-color: {CARD_SELECTED};
            }}
        """
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["书名 A-Z", "大小 ↓", "格式", "已读优先"])
        self.sort_combo.setStyleSheet(combo_style)
        self.sort_combo.setFixedWidth(90)
        self.sort_combo.currentIndexChanged.connect(self._sort_and_filter)
        h.addWidget(self.sort_combo)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "Kindle 商店", "本地导入", "已读", "未读", "KFX", "MOBI", "AZW3"])
        self.filter_combo.setStyleSheet(combo_style)
        self.filter_combo.setFixedWidth(90)
        self.filter_combo.currentIndexChanged.connect(self._sort_and_filter)
        h.addWidget(self.filter_combo)
        h.addStretch()

        import_btn = QPushButton("+ 导入书籍")
        import_btn.setStyleSheet(_BTN)
        import_btn.clicked.connect(self._import_books)
        h.addWidget(import_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(_BTN)
        refresh_btn.clicked.connect(self._do_refresh)
        h.addWidget(refresh_btn)

        self.toggle_switch = _SlideSwitch()
        self.toggle_switch.toggled.connect(self._toggle_view)
        h.addWidget(self.toggle_switch)

        self.search_bar = SearchBar("搜索书名...")
        self.search_bar.setFixedWidth(200)
        self.search_bar.text_changed.connect(self._sort_and_filter)
        h.addWidget(self.search_bar)

        layout.addLayout(h)

        # ── Stacked views ──
        self.stack = QStackedWidget()

        self.grid_view = _BookGridWidget()
        self.grid_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid_view.customContextMenuRequested.connect(self._show_grid_menu)
        self.stack.addWidget(self.grid_view)

        self.table_view = _BookTableWidget()
        self.table_view.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.table.customContextMenuRequested.connect(self._show_table_menu)
        self.stack.addWidget(self.table_view)

        layout.addWidget(self.stack, 1)

        # forward signals
        self.grid_view.book_selected.connect(self.book_selected.emit)
        self.table_view.book_selected.connect(self.book_selected.emit)

    def set_books(self, books: list[Book]):
        self.books = books
        self._sort_and_filter()

    def _sort_and_filter(self):
        books = list(self.books)
        # Filter
        f = self.filter_combo.currentText()
        if f == "Kindle 商店":
            books = [b for b in books if not b.is_sideloaded]
        elif f == "本地导入":
            books = [b for b in books if b.is_sideloaded]
        elif f == "已读":
            books = [b for b in books if b.has_read]
        elif f == "未读":
            books = [b for b in books if not b.has_read]
        elif f in ("KFX", "MOBI", "AZW3"):
            books = [b for b in books if b.format_display == f]

        # Search
        text = self.search_bar.input.text().lower()
        if text:
            books = [b for b in books if text in b.title.lower()]

        # Sort
        s = self.sort_combo.currentText()
        if s == "书名 A-Z":
            books.sort(key=lambda b: b.title)
        elif s == "大小 ↓":
            books.sort(key=lambda b: b.file_size, reverse=True)
        elif s == "格式":
            books.sort(key=lambda b: b.format)
        elif s == "已读优先":
            books.sort(key=lambda b: (not b.has_read, b.title))

        self.grid_view.set_books(books)
        self.table_view.set_books(books)
        self.count_label.setText(f"({len(books)} 本书)")

    def _current_view(self):
        return self.grid_view if self._grid_mode else self.table_view

    def _get_book(self) -> Book | None:
        if self._grid_mode:
            return self.grid_view.get_selected_book()
        else:
            return self.table_view.get_selected_book()

    def _toggle_view(self):
        self._grid_mode = not self._grid_mode
        self.stack.setCurrentIndex(0 if self._grid_mode else 1)

    def _do_refresh(self):
        self._show_refresh_overlay()
        self.refresh_requested.emit()

    def _show_refresh_overlay(self):
        if self._refresh_overlay:
            return
        self._refresh_overlay = QLabel("⟳ 正在刷新...", self)
        self._refresh_overlay.setAlignment(Qt.AlignCenter)
        self._refresh_overlay.setStyleSheet(
            "QLabel { background: rgba(255,255,255,180); color: #7a9a7a; "
            "font-size: 20px; font-weight: bold; border-radius: 8px; }"
        )
        self._refresh_overlay.setGeometry(self.stack.geometry())
        self._refresh_overlay.show()
        self._refresh_timer.start(600)

    def _hide_refresh_overlay(self):
        if self._refresh_overlay:
            self._refresh_overlay.hide()
            self._refresh_overlay.deleteLater()
            self._refresh_overlay = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._refresh_overlay:
            self._refresh_overlay.setGeometry(self.stack.geometry())

    # ── context menus ──

    def _show_grid_menu(self, pos):
        books = self.grid_view.get_selected_books()
        if books:
            self._show_menu(self.grid_view.mapToGlobal(pos), books)

    def _show_table_menu(self, pos):
        books = self._table_selected_books()
        if books:
            self._show_menu(self.table_view.table.viewport().mapToGlobal(pos), books)

    def _table_selected_books(self) -> list[Book]:
        result = []
        for idx in self.table_view.table.selectionModel().selectedRows():
            b = idx.data(Qt.UserRole)
            if b:
                result.append(b)
        return result

    def _show_menu(self, global_pos, books: list[Book]):
        if not books:
            return
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_STYLE)

        if len(books) == 1:
            b = books[0]
            for label, handler in [
                ("打开文件位置", lambda: self._open_location(b)),
                ("复制书名", lambda: self._copy_title(b)),
            ]:
                a = QAction(label, menu)
                a.triggered.connect(handler)
                menu.addAction(a)
            if b.asin:
                a = QAction("复制 ASIN", menu)
                a.triggered.connect(lambda: self._copy_asin(b))
                menu.addAction(a)
            for label, handler in [
                ("导出本书笔记", lambda: self._export_notes(b)),
                ("属性", lambda: self._show_props(b)),
            ]:
                a = QAction(label, menu)
                a.triggered.connect(handler)
                menu.addAction(a)
            menu.addSeparator()
            a = QAction("删除书籍", menu)
            a.triggered.connect(lambda: self._delete_book(b))
            menu.addAction(a)
        else:
            a = QAction(f"批量删除 ({len(books)} 本)", menu)
            a.triggered.connect(lambda: self._batch_delete(books))
            menu.addAction(a)
            a = QAction(f"批量导出笔记 ({len(books)} 本)", menu)
            a.triggered.connect(lambda: self._batch_export(books))
            menu.addAction(a)
        menu.exec(global_pos)

    # ── actions ──

    def _open_location(self, b: Book):
        subprocess.run(["explorer", "/select,", str(b.file_path.resolve())])

    def _copy_title(self, b: Book):
        QApplication.clipboard().setText(b.title)

    def _copy_asin(self, b: Book):
        QApplication.clipboard().setText(b.asin)

    def _export_notes(self, b: Book):
        try:
            clips = parse_clippings(self.kindle_path)
            groups = group_by_book(clips)
            book_clips = groups.get(b.title, [])
        except Exception:
            book_clips = []
        if not book_clips:
            QMessageBox.information(self, "无笔记", f"《{b.title}》没有笔记。")
            return
        d = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if d:
            import tempfile
            tmp = Path(tempfile.mkdtemp())
            export_markdown(book_clips, tmp)
            src = tmp / f"{_safe_name(b.title)}.md"
            if src.exists():
                shutil.copy(src, Path(d) / f"{_safe_name(b.title)}.md")
            shutil.rmtree(tmp)
            QMessageBox.information(self, "导出完成", f"笔记已导出到:\n{d}")

    def _show_props(self, b: Book):
        QMessageBox.information(self, "书籍属性", (
            f"书名: {b.title}\n格式: {b.format_display}\n大小: {b.size_display}\n"
            f"ASIN: {b.asin or '无'}\n来源: {'本地导入' if b.is_sideloaded else 'Kindle 商店'}\n"
            f"封面: {'有' if b.cover_path else '无'}\n"
            f"阅读位置: {b.last_position or '未打开'}\n"
            f"设备高亮: {b.highlight_count} 条\n"
            f"文件路径: {b.file_path}"
        ))

    def _import_books(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要导入的电子书", "",
            "电子书 (*.epub *.mobi *.azw3 *.pdf *.txt *.azw);;所有文件 (*)",
        )
        if not files:
            return
        dest = Path(self.kindle_path) / "documents" / "Downloads" / "Items01" if self.kindle_path else None
        if not dest or not dest.exists():
            QMessageBox.warning(self, "导入失败", "未检测到 Kindle 设备，无法导入。")
            return
        imported = 0
        for src in files:
            sp = Path(src)
            if not (dest / sp.name).exists():
                try:
                    shutil.copy2(sp, dest / sp.name)
                    imported += 1
                except OSError:
                    pass
        if imported:
            self.refresh_requested.emit()
            QMessageBox.information(self, "导入完成", f"成功导入 {imported} 本书籍。")

    def _batch_delete(self, books: list[Book]):
        reply = QMessageBox.warning(
            self, "确认批量删除",
            f"确定要删除以下 {len(books)} 本书吗？\n\n" +
            "\n".join(f"  · {b.title[:40]}" for b in books) +
            "\n\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for b in books:
            for p in [b.file_path, b.sdr_path]:
                if p and p.exists():
                    try:
                        (shutil.rmtree if p.is_dir() else Path.unlink)(p)
                    except OSError:
                        pass
        self.books = [b for b in self.books if b not in books]
        self._sort_and_filter()
        self.book_deleted.emit()

    def _batch_export(self, books: list[Book]):
        d = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not d:
            return
        try:
            all_clips = parse_clippings(self.kindle_path)
        except Exception:
            all_clips = []
        exported = 0
        for b in books:
            clips = [c for c in all_clips if c.book_title == b.title]
            if not clips:
                continue
            import tempfile
            tmp = Path(tempfile.mkdtemp())
            export_markdown(clips, tmp)
            src = tmp / f"{_safe_name(b.title)}.md"
            if src.exists():
                shutil.copy(src, Path(d) / f"{_safe_name(b.title)}.md")
                exported += 1
            shutil.rmtree(tmp)
        QMessageBox.information(self, "导出完成", f"已导出 {exported} 本书的笔记到:\n{d}")

    def _delete_book(self, b: Book):
        reply = QMessageBox.warning(
            self, "确认删除",
            f"确定要删除《{b.title}》吗？\n\n"
            f"文件: {b.file_path.name}\n大小: {b.size_display}\n\n"
            "此操作将同时删除对应的 .sdr 文件夹。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for p in [b.file_path, b.sdr_path]:
            if p and p.exists():
                try:
                    (shutil.rmtree if p.is_dir() else Path.unlink)(p)
                except OSError:
                    pass
        self.books = [x for x in self.books if x.file_path != b.file_path]
        self.set_books(self.books)
        self.book_deleted.emit()


class _SlideSwitch(QWidget):
    toggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on_left = True
        self.setFixedSize(100, 30)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self._on_left = not self._on_left
        self.update()
        self.toggled.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Background pill
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e0d8c8"))
        p.drawRoundedRect(0, 2, 100, 26, 13, 13)

        # Active side
        p.setBrush(QColor(ACCENT))
        if self._on_left:
            p.drawRoundedRect(1, 3, 49, 24, 12, 12)
        else:
            p.drawRoundedRect(50, 3, 49, 24, 12, 12)

        # Labels
        p.setPen(QColor("#fff" if self._on_left else MUTED))
        p.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        p.drawText(0, 2, 49, 26, Qt.AlignCenter, "封面")

        p.setPen(QColor(MUTED if self._on_left else "#fff"))
        p.setFont(QFont("Microsoft YaHei", 10, QFont.Bold if not self._on_left else QFont.Normal))
        p.drawText(50, 2, 49, 26, Qt.AlignCenter, "列表")

        p.end()


def _safe_name(name: str) -> str:
    invalid = '<>:"/\\|?*'
    r = name[:60].strip()
    for ch in invalid:
        r = r.replace(ch, "_")
    return r
