import struct
import subprocess
import shutil
import webbrowser
from pathlib import Path

SUPPORTED_FORMATS = {
    ".azw3": "KF8 (Kindle Format 8)",
    ".azw": "MOBI (Kindle legacy)",
    ".kfx": "KFX (Kindle Format 10)",
    ".mobi": "MOBI",
    ".epub": "EPUB",
    ".pdf": "PDF",
    ".txt": "Plain Text",
}

TARGET_FORMATS = ["epub", "mobi", "azw3", "pdf", "txt", "kfx"]


# ── Calibre engine ──────────────────────────────────────────────

def find_calibre() -> str | None:
    exe = shutil.which("ebook-convert")
    if exe:
        return exe
    for base in ["C:/Program Files/Calibre2", "C:/Program Files (x86)/Calibre2"]:
        path = Path(base) / "ebook-convert.exe"
        if path.exists():
            return str(path)
    return None


def open_calibre_download():
    webbrowser.open("https://calibre-ebook.com/download")


def convert_with_calibre(input_path: Path, output_path: Path, target_format: str) -> tuple[bool, str]:
    calibre = find_calibre()
    if not calibre:
        return False, "calibre_not_found"

    src_fmt = input_path.suffix.lower()
    if src_fmt == ".kfx":
        return False, (
            "KFX 格式受 DRM 保护，Calibre 也无法直接转换。\n"
            "请安装 Calibre 的 KFX Input 和 DeDRM 插件后重试。"
        )

    try:
        result = subprocess.run(
            [calibre, str(input_path), str(output_path)],
            capture_output=True, timeout=300,
        )
        if result.returncode == 0 and output_path.exists():
            size = output_path.stat().st_size
            sz = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"
            return True, f"转换成功 → {output_path.name} ({sz})"
        else:
            err = (result.stderr or result.stdout or b"").decode("utf-8", errors="replace")
            lines = [l for l in err.splitlines() if l.strip()]
            short = lines[-1] if lines else err
            return False, f"Calibre 转换失败: {short[:200]}"
    except subprocess.TimeoutExpired:
        return False, "转换超时，文件可能过大。"
    except Exception as e:
        return False, f"转换出错: {e}"


# ── Pure Python MOBI/AZW3 → EPUB fallback ────────────────────────

def convert_mobi_to_epub_python(input_path: Path, output_path: Path) -> tuple[bool, str]:
    """Pure Python MOBI/AZW3 → EPUB using raw PalmDB + HTML extraction."""
    try:
        data = input_path.read_bytes()
    except Exception as e:
        return False, f"无法读取文件: {e}"

    if len(data) < 78:
        return False, "文件太小，不是有效的 MOBI 文件"

    html = _extract_mobi_html(data, input_path)
    if not html:
        return False, "无法从 MOBI 文件中提取 HTML 内容"

    try:
        from ebooklib import epub
    except ImportError:
        return False, "缺少 ebooklib 库，请运行: pip install ebooklib"

    try:
        book = epub.EpubBook()
        book.set_identifier(str(input_path.stem))
        book.set_title(input_path.stem)
        book.set_language("zh")
        book.add_author("Unknown")

        # Wrap HTML properly for epub
        if "<body" not in html.lower():
            html = f"<html><body>{html}</body></html>"

        chapter = epub.EpubHtml(
            title="Content",
            file_name="content.xhtml",
            lang="zh",
        )
        chapter.content = html.encode("utf-8")

        book.add_item(chapter)
        book.toc = [epub.Link("content.xhtml", "Content", "content")]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", chapter]

        epub.write_epub(str(output_path), book)

        if output_path.exists():
            size = output_path.stat().st_size
            sz = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"
            return True, f"转换成功 → {output_path.name} ({sz})"
        return False, "EPUB 文件未生成"
    except Exception as e:
        return False, f"EPUB 构建失败: {e}"


def _extract_mobi_html(data: bytes, path: Path) -> str:
    """Extract HTML from MOBI/AZW3 by scanning records for HTML content."""
    if len(data) < 78:
        return ""

    num_records = struct.unpack_from(">H", data, 76)[0]
    if num_records < 2 or num_records > 20000:
        return ""

    # Build record offsets
    offsets: list[int] = []
    for i in range(num_records):
        off = struct.unpack_from(">I", data, 78 + i * 8)[0]
        offsets.append(off)
    offsets.append(len(data))

    # Find which record starts with HTML content
    html_start_idx = 1
    for i in range(1, min(num_records, 50)):
        start = offsets[i]
        end = min(start + 200, offsets[i + 1])
        preview = data[start:end]
        try:
            peek = preview.decode("utf-8", errors="ignore").lower()
        except Exception:
            continue
        if "<html" in peek or "<body" in peek or "<div" in peek:
            html_start_idx = i
            break

    # Concatenate all records from the HTML start to the end
    parts: list[bytes] = []
    for i in range(html_start_idx, num_records - 1):
        parts.append(data[offsets[i]:offsets[i + 1]])

    full = b"".join(parts)

    # Detect encoding from HTML meta tag or use UTF-8
    encoding = "utf-8"
    head = full[:2000]
    if b"charset=gb" in head.lower() or b"charset=GB" in head:
        encoding = "gb2312"
    elif b"charset=big5" in head.lower():
        encoding = "big5"

    return full.decode(encoding, errors="replace")


# ── Main conversion API ─────────────────────────────────────────

def convert_ebook(input_path: str | Path, output_path: str | Path, target_format: str) -> tuple[bool, str]:
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        return False, f"源文件不存在: {input_path}"

    src_fmt = input_path.suffix.lower()
    tgt_fmt = target_format.lower()

    # KFX is Amazon's proprietary output-only format
    if tgt_fmt == "kfx":
        return False, (
            "KFX 是 Amazon 专有格式，只能通过官方工具生成。\n\n"
            "推荐方法：使用 Send to Kindle 服务\n"
            "1. 将 EPUB 文件上传到 Send to Kindle\n"
            "2. Amazon 服务器自动转为 KFX 并同步到你的 Kindle\n"
            "3. 登录 Amazon 账户即可使用：\n"
            "   https://www.amazon.com/sendtokindle\n\n"
            "也可以安装 Kindle Previewer 在本地生成 KFX：\n"
            "   https://www.amazon.com/KindlePreviewer"
        )

    # Try Calibre first for all conversions
    calibre = find_calibre()
    if calibre:
        if src_fmt == ".kfx":
            return False, (
                "KFX 格式受 DRM 保护，无法直接转换。\n"
                "请确保 Calibre 已安装 KFX Input 和 DeDRM 插件。"
            )
        return convert_with_calibre(input_path, output_path, target_format)

    # No Calibre — use pure Python fallback for MOBI/AZW3 → EPUB
    if src_fmt in (".mobi", ".azw", ".azw3") and tgt_fmt == "epub":
        return convert_mobi_to_epub_python(input_path, output_path)

    # No Calibre and no fallback available
    return False, (
        "未找到 Calibre，且当前格式组合不支持内置转换。\n\n"
        "建议安装 Calibre 以获得完整的格式转换支持：\n"
        "https://calibre-ebook.com/download\n\n"
        "内置引擎支持: MOBI/AZW3 → EPUB"
    )


def get_target_path(input_path: Path, target_format: str) -> Path:
    return input_path.with_suffix(f".{target_format}")
