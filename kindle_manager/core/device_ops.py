from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from kindle_manager.models.book import Book
from kindle_manager.core.scanner import BOOK_EXTS


@dataclass(frozen=True)
class OperationResult:
    ok: bool
    message: str


def atomic_write_text(path: Path, text: str, *, backup: bool = True) -> None:
    """Write a device text file atomically and keep one recoverable backup."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def import_books(kindle_root: str | Path, sources: list[str | Path]) -> list[OperationResult]:
    root = Path(kindle_root).resolve()
    documents = root / "documents"
    if not documents.is_dir():
        return [OperationResult(False, "Kindle documents 目录不存在")]
    destination = documents / "Downloads" / "Items01"
    if not destination.is_dir():
        destination = documents

    results: list[OperationResult] = []
    for source in sources:
        src = Path(source)
        dest = destination / src.name
        partial = destination / f".{src.name}.partial"
        if not src.is_file():
            results.append(OperationResult(False, f"源文件不存在：{src.name}"))
        elif src.suffix.lower() not in BOOK_EXTS:
            results.append(OperationResult(False, f"不支持的文件格式：{src.name}"))
        elif dest.exists():
            results.append(OperationResult(False, f"已存在同名文件：{src.name}"))
        else:
            try:
                shutil.copy2(src, partial)
                os.replace(partial, dest)
                results.append(OperationResult(True, f"已导入：{src.name}"))
            except OSError as exc:
                partial.unlink(missing_ok=True)
                results.append(OperationResult(False, f"导入失败：{src.name}（{exc}）"))
    return results


def move_book_to_trash(kindle_root: str | Path, book: Book) -> OperationResult:
    """Move a book and its exact sidecar directory to a recoverable device folder."""
    root = Path(kindle_root).resolve()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    trash = root / ".kindle-manager-trash" / stamp
    targets = [p for p in (book.file_path, book.sdr_path) if p and p.exists()]
    if not targets:
        return OperationResult(False, f"未找到《{book.title}》的设备文件")

    resolved: list[Path] = []
    for target in targets:
        candidate = target.resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return OperationResult(False, f"拒绝删除 Kindle 目录之外的路径：{candidate}")
        resolved.append(candidate)

    moved: list[tuple[Path, Path]] = []
    try:
        trash.mkdir(parents=True, exist_ok=False)
        for source in resolved:
            destination = trash / source.name
            shutil.move(str(source), str(destination))
            moved.append((source, destination))
    except OSError as exc:
        for original, destination in reversed(moved):
            try:
                shutil.move(str(destination), str(original))
            except OSError:
                pass
        return OperationResult(False, f"移动《{book.title}》失败：{exc}")
    return OperationResult(True, f"《{book.title}》已移入可恢复目录 {trash.name}")
