from collections import Counter

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QProgressBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from kindle_manager.models.book import Book

BG = "#faf6f0"
CARD_BG = "#ffffff"
TEXT = "#3d3830"
MUTED = "#6a6058"
ACCENT = "#7a9a7a"
ACCENT2 = "#c4a56a"
ACCENT3 = "#9a8a7a"
ACCENT4 = "#8a9ab0"
BORDER = "#e5ddd0"
BAR_GREEN = "#7a9a7a"
BAR_ORANGE = "#c4a56a"
BAR_BLUE = "#8a9ab0"
BAR_PURPLE = "#9a8a7a"


class StatsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.books: list[Book] = []
        self.clipping_count: int = 0
        self.vocab_count: int = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {BG}; border: none; }}")

        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setContentsMargins(28, 20, 28, 28)
        cl.setSpacing(20)

        title = QLabel("统计")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT};")
        cl.addWidget(title)

        # Row 1: four stat cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.card_books = _StatCard("藏书总数", "—", ACCENT, "本")
        self.card_read = _StatCard("已打开", "—", ACCENT3, "本")
        self.card_notes = _StatCard("笔记 & 词汇", "—", ACCENT4, "条")
        self.card_size = _StatCard("总占用空间", "—", ACCENT2, "")
        cards_row.addWidget(self.card_books)
        cards_row.addWidget(self.card_read)
        cards_row.addWidget(self.card_notes)
        cards_row.addWidget(self.card_size)
        cl.addLayout(cards_row)

        # Row 2: format chart + size panel
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        self.format_panel = _Panel("格式分布")
        mid_row.addWidget(self.format_panel, 1)

        self.detail_panel = _Panel("详细信息")
        mid_row.addWidget(self.detail_panel, 1)
        cl.addLayout(mid_row)

        # Row 3: reading progress
        self.read_panel = _Panel("阅读排行")
        cl.addWidget(self.read_panel, 1)

        cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def set_data(self, books: list[Book], clipping_count: int, vocab_count: int):
        self.books = books
        self.clipping_count = clipping_count
        self.vocab_count = vocab_count
        self._refresh()

    def _refresh(self):
        books = self.books
        total = len(books)
        read_count = sum(1 for b in books if b.has_read)
        total_size = sum(b.file_size for b in books)

        self.card_books.set_value(str(total))
        self.card_read.set_value(f"{read_count} / {total}" if total else "—")
        self.card_notes.set_value(str(self.clipping_count + self.vocab_count))
        self.card_size.set_value(_fmt_size(total_size))

        # Format distribution with colored bars
        fmt_counter = Counter(b.format_display for b in books)
        bar_colors = [BAR_GREEN, BAR_ORANGE, BAR_BLUE, BAR_PURPLE]
        fmt_html = ""
        for i, (fmt, cnt) in enumerate(fmt_counter.most_common()):
            pct = (cnt / total * 100) if total > 0 else 0
            color = bar_colors[i % len(bar_colors)]
            bar_w = max(int(pct * 3.5), 4)
            fmt_html += (
                f"<div style='margin:6px 0;'>"
                f"<span style='color:{TEXT};'>{fmt}</span>"
                f"<span style='color:{MUTED}; font-size:12px;'> {cnt} 本 ({pct:.0f}%)</span>"
                f"<div style='background:#eee; border-radius:3px; margin-top:2px;'>"
                f"<div style='background:{color}; height:8px; border-radius:3px; width:{bar_w}px;'></div>"
                f"</div></div>"
            )
        self.format_panel.set_content(fmt_html)

        # Detail info
        amazon = [b for b in books if not b.is_sideloaded]
        side = [b for b in books if b.is_sideloaded]
        detail_html = (
            f"<p style='color:{MUTED}; font-size:13px;'>"
            f"Kindle 商店: {len(amazon)} 本 / {_fmt_size(sum(b.file_size for b in amazon))}<br>"
            f"本地导入: {len(side)} 本 / {_fmt_size(sum(b.file_size for b in side))}<br>"
            f"设备高亮: {sum(b.highlight_count for b in books)} 条<br>"
            f"未打开: {total - read_count} 本"
            f"</p>"
        )
        self.detail_panel.set_content(detail_html)

        # Reading ranking
        read_books = sorted(
            [b for b in books if b.has_read],
            key=lambda b: b.last_position, reverse=True,
        )
        rank_html = ""
        if read_books:
            max_pos = read_books[0].last_position if read_books else 1
            for i, b in enumerate(read_books[:8]):
                pct = min(b.last_position / max_pos * 100, 100) if max_pos > 0 else 0
                rank_html += (
                    f"<div style='margin:4px 0;'>"
                    f"<span style='color:{TEXT}; font-size:13px;'>{i+1}. {b.title[:30]}</span>"
                    f"<span style='color:{MUTED}; font-size:11px;'> {b.last_position//1000}K</span>"
                    f"<div style='background:#eee; border-radius:2px; margin-top:1px;'>"
                    f"<div style='background:{BAR_GREEN}; height:5px; border-radius:2px; width:{max(int(pct), 2)}%;'></div>"
                    f"</div></div>"
                )
        else:
            rank_html = f"<p style='color:{MUTED};'>暂无阅读记录</p>"
        self.read_panel.set_content(rank_html)


class _StatCard(QFrame):
    def __init__(self, label: str, value: str, color: str, unit: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            _StatCard {{
                background: {CARD_BG}; border-radius: 10px;
                border: 1px solid {BORDER}; border-left: 4px solid {color};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)

        desc = QLabel(label)
        desc.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        layout.addWidget(desc)

        if unit:
            self.unit_label = QLabel(unit)
            self.unit_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
            layout.addWidget(self.unit_label)

    def set_value(self, v: str):
        self.value_label.setText(v)


class _Panel(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            _Panel {{
                background: {CARD_BG}; border-radius: 10px;
                border: 1px solid {BORDER};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        t = QLabel(title)
        t.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        t.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(t)

        self.content = QLabel()
        self.content.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        self.content.setTextFormat(Qt.RichText)
        self.content.setWordWrap(True)
        layout.addWidget(self.content)
        layout.addStretch()

    def set_content(self, text: str):
        self.content.setText(text)


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"
