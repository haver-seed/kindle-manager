from __future__ import annotations

import shutil
import subprocess
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
CALIBRE_TARGETS = {"epub", "mobi", "azw3", "pdf", "txt"}


def find_calibre() -> str | None:
    executable = shutil.which("ebook-convert")
    if executable:
        return executable
    for base in ("C:/Program Files/Calibre2", "C:/Program Files (x86)/Calibre2"):
        candidate = Path(base) / "ebook-convert.exe"
        if candidate.exists():
            return str(candidate)
    return None


def open_calibre_download() -> None:
    webbrowser.open("https://calibre-ebook.com/download")


def convert_with_calibre(
    input_path: Path, output_path: Path, target_format: str,
) -> tuple[bool, str]:
    calibre = find_calibre()
    if not calibre:
        return False, "calibre_not_found"
    if target_format.lower() not in CALIBRE_TARGETS:
        return False, f"不支持的目标格式：{target_format}"

    try:
        result = subprocess.run(
            [calibre, str(input_path), str(output_path)],
            capture_output=True,
            timeout=300,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if result.returncode == 0 and output_path.is_file() and output_path.stat().st_size:
            size = output_path.stat().st_size
            display = f"{size / 1024:.1f} KB" if size < 1024**2 else f"{size / 1024**2:.1f} MB"
            return True, f"转换成功 → {output_path.name} ({display})"
        output_path.unlink(missing_ok=True)
        error = (result.stderr or result.stdout or b"").decode("utf-8", errors="replace")
        lines = [line.strip() for line in error.splitlines() if line.strip()]
        return False, f"Calibre 转换失败：{(lines[-1] if lines else '未知错误')[:240]}"
    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        return False, "转换超过 5 分钟，任务已停止。"
    except OSError as exc:
        output_path.unlink(missing_ok=True)
        return False, f"无法启动转换：{exc}"


def convert_ebook(
    input_path: str | Path, output_path: str | Path, target_format: str,
) -> tuple[bool, str]:
    source = Path(input_path)
    output = Path(output_path)
    target = target_format.lower().lstrip(".")

    if not source.is_file():
        return False, f"源文件不存在：{source}"
    if source.suffix.lower() not in SUPPORTED_FORMATS:
        return False, f"不支持的源格式：{source.suffix or '无扩展名'}"
    if target == source.suffix.lower().lstrip("."):
        return False, "源文件和目标格式相同。"
    if target == "kfx":
        return False, (
            "KFX 需要通过 Amazon 官方服务生成。\n"
            "请使用 Send to Kindle 或 Kindle Previewer。"
        )
    if source.suffix.lower() == ".kfx":
        return False, "KFX 文件通常受保护，无法进行可靠的本地转换。"
    if not find_calibre():
        return False, (
            "未找到 Calibre，无法进行可靠的格式转换。\n\n"
            "请安装 Calibre 后重试：https://calibre-ebook.com/download"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    return convert_with_calibre(source, output, target)


def get_target_path(input_path: Path, target_format: str) -> Path:
    target = input_path.with_suffix(f".{target_format.lower().lstrip('.')}")
    if not target.exists():
        return target
    index = 1
    while True:
        candidate = target.with_name(f"{target.stem}-converted-{index}{target.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
