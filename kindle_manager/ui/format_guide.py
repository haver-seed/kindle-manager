from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QComboBox, QPushButton, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, Signal, QThreadPool
from PySide6.QtGui import QFont
from pathlib import Path

from kindle_manager.core.converter import (
    TARGET_FORMATS, find_calibre, convert_ebook,
    get_target_path, open_calibre_download,
)
from kindle_manager.ui.workers import TaskWorker
from kindle_manager.ui.theme import ACCENT, BG, BORDER, MUTED, SURFACE, TEXT

CARD_BG = SURFACE

GUIDE_HTML = f"""
<div style="font-family: 'Microsoft YaHei', sans-serif; color:{TEXT}; line-height:1.8;">

<h2 style="color:{ACCENT};">Kindle 支持的格式</h2>

<table style="width:100%; border-collapse:collapse; margin:10px 0;">
<tr style="background:#f0ebe0;">
  <th style="padding:8px 12px; text-align:left; border:1px solid {BORDER};">格式</th>
  <th style="padding:8px 12px; text-align:left; border:1px solid {BORDER};">说明</th>
  <th style="padding:8px 12px; text-align:left; border:1px solid {BORDER};">推荐度</th>
</tr>
<tr>
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>KFX</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">Kindle Format 10，Amazon 官方最新格式。支持增强排版、页码、X-Ray 等高级功能。</td>
  <td style="padding:8px 12px; border:1px solid {BORDER}; color:#7a9a7a;">★★★★★</td>
</tr>
<tr style="background:#faf6f0;">
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>AZW3 (KF8)</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">Kindle Format 8，支持自定义字体、CSS 排版，兼容性好。Calibre 转换的首选目标格式。</td>
  <td style="padding:8px 12px; border:1px solid {BORDER}; color:#7a9a7a;">★★★★☆</td>
</tr>
<tr>
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>MOBI</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">Kindle 最老的电子书格式。不支持自定义字体和增强排版，但兼容所有 Kindle 设备。</td>
  <td style="padding:8px 12px; border:1px solid {BORDER}; color:#c4a56a;">★★★☆☆</td>
</tr>
<tr style="background:#faf6f0;">
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>AZW</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">MOBI 的 Amazon 专有变体，通常带 DRM 保护。Kindle 词典多使用此格式。</td>
  <td style="padding:8px 12px; border:1px solid {BORDER}; color:#c4a56a;">★★★☆☆</td>
</tr>
<tr>
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>PDF</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">Kindle 原生支持 PDF，但固定版式在小屏上阅读体验一般。</td>
  <td style="padding:8px 12px; border:1px solid {BORDER}; color:#c06050;">★★☆☆☆</td>
</tr>
<tr style="background:#faf6f0;">
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>TXT</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">纯文本格式，可以打开但无法跳转章节、无图片，排版简陋。</td>
  <td style="padding:8px 12px; border:1px solid {BORDER}; color:#c06050;">★★☆☆☆</td>
</tr>
</table>

<h2 style="color:{ACCENT}; margin-top:24px;">Kindle 不支持的格式</h2>

<table style="width:100%; border-collapse:collapse; margin:10px 0;">
<tr style="background:#f0ebe0;">
  <th style="padding:8px 12px; text-align:left; border:1px solid {BORDER};">格式</th>
  <th style="padding:8px 12px; text-align:left; border:1px solid {BORDER};">说明</th>
</tr>
<tr>
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>EPUB</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">最通用的电子书格式，但 <b>Kindle 不支持直接阅读</b>。需转换后导入。</td>
</tr>
<tr style="background:#faf6f0;">
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>DJVU</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">扫描版电子书格式，常用于学术文献。</td>
</tr>
<tr>
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>CBZ / CBR</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">漫画格式（ZIP/RAR 图片包），Kindle 不支持。</td>
</tr>
<tr style="background:#faf6f0;">
  <td style="padding:8px 12px; border:1px solid {BORDER};"><b>DOC / DOCX</b></td>
  <td style="padding:8px 12px; border:1px solid {BORDER};">Word 文档，Kindle 不直接支持，需转换。</td>
</tr>
</table>

<h2 style="color:{ACCENT}; margin-top:24px;">关于 KFX 格式</h2>
<p style="color:{MUTED};">
<b>KFX</b>（Kindle Format 10）是 Amazon 的专有格式，具有增强排版、页码显示、X-Ray 等高级功能，
是 Kindle 设备上阅读体验最好的格式。但 <b>KFX 只能通过 Amazon 官方服务生成</b>，任何第三方工具（包括 Calibre）
都无法直接输出 KFX 格式。
</p>
<p style="color:{MUTED};">
<b>获取 KFX 的途径：</b>
</p>
<ul style="color:{MUTED};">
  <li><b>Kindle 商店购买</b> — 从 Amazon 购买的书默认以 KFX 格式下载到设备</li>
  <li><b>Send to Kindle</b> — 上传 EPUB/PDF/DOCX 到 Amazon 服务，服务器自动转为 KFX 并同步</li>
  <li><b>Kindle Previewer</b> — Amazon 官方桌面工具，可在本地将 EPUB 转为 KFX 用于预览</li>
</ul>

</div>
"""


class FormatGuideView(QWidget):
    conversion_done = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.books = []
        self._local_file = ""
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {BG}; border: none; }}")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 16, 24, 24)
        container_layout.setSpacing(20)

        # ── Conversion tool ──
        converter = QFrame()
        converter.setStyleSheet(f"""
            QFrame {{
                background: {CARD_BG};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        conv_layout = QVBoxLayout(converter)
        conv_layout.setContentsMargins(20, 16, 20, 16)
        conv_layout.setSpacing(10)

        conv_title = QLabel("格式转换")
        conv_title.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        conv_title.setStyleSheet(f"color: {TEXT};")
        conv_layout.addWidget(conv_title)

        # Calibre status
        calibre_ok = find_calibre() is not None
        status_text = ("Calibre 已就绪 · 支持可靠的多格式转换" if calibre_ok
                       else "未检测到 Calibre · 安装后可启用格式转换")
        calibre_status = QLabel(status_text)
        calibre_status.setStyleSheet(
            f"color: {'#7a9a7a' if calibre_ok else '#c4a56a'}; font-size: 12px;"
        )
        conv_layout.addWidget(calibre_status)

        # Row: source book + target format + convert button
        row = QHBoxLayout()
        row.setSpacing(12)

        row.addWidget(QLabel("源文件:"))
        self.book_combo = QComboBox()
        self.book_combo.setMinimumWidth(300)
        self.book_combo.setStyleSheet(f"""
            QComboBox {{
                background: #fff; color: {TEXT};
                border: 1px solid {BORDER}; border-radius: 4px;
                padding: 5px 12px; font-size: 13px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: #fff; color: {TEXT};
                selection-background-color: #dce8d8;
            }}
        """)
        self.book_combo.currentIndexChanged.connect(self._on_book_source_changed)
        row.addWidget(self.book_combo)

        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: #fff; color: {TEXT}; border: 1px solid {BORDER};
                border-radius: 4px; padding: 5px 12px; font-size: 12px;
            }}
            QPushButton:hover {{ background: #f0ebe0; }}
        """)
        browse_btn.clicked.connect(self._browse_file)
        row.addWidget(browse_btn)

        row.addWidget(QLabel("目标格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(TARGET_FORMATS)
        self.format_combo.setStyleSheet(self.book_combo.styleSheet())
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        row.addWidget(self.format_combo)

        btn_style = f"""
            QPushButton {{
                background: {ACCENT}; color: #fff; border: none;
                border-radius: 4px; padding: 7px 20px;
                font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background: #8aae8a; }}
            QPushButton:disabled {{ background: #c0c0c0; }}
        """
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setStyleSheet(btn_style)
        self.convert_btn.clicked.connect(self._do_convert)
        row.addWidget(self.convert_btn)

        if not calibre_ok:
            install_btn = QPushButton("安装 Calibre")
            install_btn.setStyleSheet("""
                QPushButton {{
                    background: #c4a56a; color: #fff; border: none;
                    border-radius: 4px; padding: 7px 16px;
                    font-size: 13px;
                }}
                QPushButton:hover {{ background: #d4b57a; }}
            """)
            install_btn.clicked.connect(open_calibre_download)
            row.addWidget(install_btn)

        row.addStretch()
        conv_layout.addLayout(row)

        container_layout.addWidget(converter)

        # ── Format guide (HTML) ──
        guide = QLabel(GUIDE_HTML)
        guide.setWordWrap(True)
        guide.setOpenExternalLinks(True)
        guide.setTextFormat(Qt.RichText)
        guide.setStyleSheet("""
            QLabel {{
                background: transparent;
                padding: 8px 0;
                font-size: 14px;
            }}
        """)
        container_layout.addWidget(guide)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def set_books(self, books):
        self.books = books
        self._local_file = ""
        self.book_combo.clear()
        self.book_combo.addItem("— 选择 Kindle 上的书籍 —", None)
        for b in books:
            label = f"{b.title[:50]}  [{b.format_display}]"
            self.book_combo.addItem(label, b)

    def _on_book_source_changed(self, index: int):
        if index > 0:
            self._local_file = ""
            self.book_combo.setToolTip("")

    def _browse_file(self):
        from PySide6.QtWidgets import QFileDialog
        f, _ = QFileDialog.getOpenFileName(
            self, "选择要转换的文件", "",
            "电子书 (*.epub *.mobi *.azw3 *.azw *.kfx *.pdf *.txt);;所有文件 (*)",
        )
        if f:
            self.book_combo.setCurrentIndex(0)
            self._local_file = f
            self.book_combo.setItemText(0, f"本地文件 · {Path(f).name}")
            self.book_combo.setToolTip(f"已选择本地文件: {f}")

    def _on_format_changed(self, fmt: str):
        if fmt == "kfx":
            self.convert_btn.setText("使用 Send to Kindle")
            self.convert_btn.setToolTip(
                "KFX 是 Amazon 专有格式，需要通过 Send to Kindle 服务转换"
            )
        else:
            self.convert_btn.setText("开始转换")
            self.convert_btn.setToolTip("")

    def _do_convert(self):
        target = self.format_combo.currentText()

        # Determine source file path
        src_path = self._local_file
        book = None
        if not src_path:
            idx = self.book_combo.currentIndex()
            book = self.book_combo.itemData(idx) if idx > 0 else None
            if book and book.file_path:
                src_path = str(book.file_path)

        if not src_path:
            QMessageBox.warning(self, "提示", "请选择一本书或浏览本地文件。")
            return

        from pathlib import Path
        src_path = Path(src_path)

        # KFX: redirect to Send to Kindle
        if target == "kfx":
            QMessageBox.information(
                self, "转换为 KFX",
                "KFX 是 Amazon 的专有格式，只能通过官方服务生成。\n\n"
                "推荐使用 Send to Kindle：\n"
                "1. 将 EPUB 文件上传到 Send to Kindle\n"
                "2. Amazon 自动转为 KFX 并同步到你的 Kindle\n\n"
                "即将打开 Send to Kindle 页面..."
            )
            import webbrowser
            webbrowser.open("https://www.amazon.com/sendtokindle")
            return

        if target == src_path.suffix[1:].lower():
            QMessageBox.information(self, "提示", "源文件和目标格式相同。")
            return

        output = get_target_path(src_path, target)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("转换中...")
        self._worker = TaskWorker(convert_ebook, src_path, output, target)
        self._worker.signals.result.connect(self._conversion_finished)
        self._worker.signals.error.connect(self._conversion_error)
        QThreadPool.globalInstance().start(self._worker)

    def _conversion_finished(self, result):
        ok, msg = result
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("开始转换")

        if ok:
            self.conversion_done.emit()
            QMessageBox.information(self, "转换完成", msg)
        else:
            if "未找到 Calibre" in msg or "建议安装 Calibre" in msg:
                reply = QMessageBox.question(
                    self, "需要 Calibre",
                    msg + "\n\n是否打开 Calibre 下载页面？",
                )
                if reply == QMessageBox.Yes:
                    open_calibre_download()
            else:
                QMessageBox.warning(self, "转换失败", msg)

    def _conversion_error(self, details: str):
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("开始转换")
        QMessageBox.critical(self, "转换异常", details.splitlines()[-1] if details else "未知错误")
