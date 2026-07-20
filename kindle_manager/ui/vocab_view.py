from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLabel, QComboBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from kindle_manager.core.vocabulary import read_vocabulary, VocabWord
from kindle_manager.ui.widgets import SearchBar
from kindle_manager.ui.theme import BORDER, MUTED, SURFACE, SURFACE_ALT, TEXT

# Cream light palette
TABLE_BG = SURFACE
TABLE_ALT = "#F7F4EE"
HEADER_BG = SURFACE_ALT


class VocabView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.words: list[VocabWord] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        header.addWidget(self.count_label)
        header.addStretch()

        combo_style = f"""
            QComboBox {{
                background: #fff; color: {TEXT}; border: 1px solid {BORDER};
                border-radius: 4px; padding: 4px 12px; font-size: 13px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: #fff; color: {TEXT};
                selection-background-color: #dce8d8;
            }}
        """
        self.lang_filter = QComboBox()
        self.lang_filter.addItems(["全部语言", "EN (英文)", "中文", "日文", "FR", "DE"])
        self.lang_filter.setStyleSheet(combo_style)
        self.lang_filter.currentIndexChanged.connect(self._filter)
        header.addWidget(self.lang_filter)

        self.search_bar = SearchBar("搜索单词...")
        self.search_bar.setFixedWidth(200)
        self.search_bar.text_changed.connect(self._filter)
        header.addWidget(self.search_bar)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["单词", "语言", "来源书籍", "语境", "查询时间"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        hv = self.table.horizontalHeader()
        hv.setSectionResizeMode(0, QHeaderView.Fixed)
        hv.setSectionResizeMode(1, QHeaderView.Fixed)
        hv.setSectionResizeMode(2, QHeaderView.Stretch)
        hv.setSectionResizeMode(3, QHeaderView.Stretch)
        hv.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 50)
        self.table.setColumnWidth(4, 140)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {TABLE_BG}; color: {TEXT};
                border: 1px solid {BORDER}; border-radius: 4px;
                font-size: 13px; alternate-background-color: {TABLE_ALT};
            }}
            QTableWidget::item {{
                padding: 6px 10px; border-bottom: 1px solid {BORDER};
            }}
            QTableWidget::item:selected {{
                background: #dce8d8; color: {TEXT};
            }}
            QHeaderView::section {{
                background: {HEADER_BG}; color: {MUTED};
                border: none; border-bottom: 2px solid {BORDER};
                padding: 6px 10px; font-weight: bold; font-size: 12px;
            }}
        """)

        layout.addWidget(self.table)

    def load_vocab(self, kindle_path: str):
        try:
            self.set_words(read_vocabulary(kindle_path))
        except FileNotFoundError:
            self.set_words([])

    def set_words(self, words: list[VocabWord]):
        self.words = words
        self._populate_table(self.words)
        self.count_label.setText(f"{len(self.words)} 个单词" if self.words else "暂无生词")

    def _populate_table(self, words: list[VocabWord]):
        self.table.setRowCount(len(words))
        for row, w in enumerate(words):
            word_item = QTableWidgetItem(w.word)
            word_item.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            self.table.setItem(row, 0, word_item)

            lang_item = QTableWidgetItem(w.lang_display)
            lang_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, lang_item)

            self.table.setItem(row, 2, QTableWidgetItem(w.book_title))

            usage_text = w.usage[:120] + "..." if len(w.usage) > 120 else w.usage
            self.table.setItem(row, 3, QTableWidgetItem(usage_text))

            ts = w.timestamp.strftime("%Y-%m-%d %H:%M") if w.timestamp else "-"
            time_item = QTableWidgetItem(ts)
            self.table.setItem(row, 4, time_item)

    def _filter(self):
        text = self.search_bar.input.text().lower()
        lang_choice = self.lang_filter.currentText()
        filtered = self.words

        if lang_choice != "全部语言":
            lang_map = {"EN (英文)": "en", "中文": "zh", "日文": "ja", "FR": "fr", "DE": "de"}
            target = lang_map.get(lang_choice, "")
            if target:
                filtered = [w for w in filtered if w.lang == target]
        if text:
            filtered = [w for w in filtered if
                        text in w.word.lower() or text in w.stem.lower()
                        or text in w.usage.lower()]
        self._populate_table(filtered)
        self.count_label.setText(f"({len(filtered)} / {len(self.words)} 个单词)")
