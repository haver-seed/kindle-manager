import csv
import hashlib
import json
from pathlib import Path

from kindle_manager.models.clipping import Clipping
from kindle_manager.core.clippings import group_by_book


def export_markdown(clippings: list[Clipping], output_dir: str | Path) -> dict[str, Path]:
    """Export clippings as Markdown files, one per book."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    groups = group_by_book(clippings)

    names = _unique_filenames(groups.keys())
    reserved_paths: set[str] = set()
    exported: dict[str, Path] = {}
    for book_title, clips in groups.items():
        safe_name = names[book_title]
        path = _available_path(out / f"{safe_name}.md", reserved_paths)
        safe_name = path.stem
        names[book_title] = safe_name
        exported[book_title] = path
        lines = [f"# {book_title}", ""]

        # Sort by date
        clips_sorted = sorted(clips, key=lambda c: c.date or _min_date())

        for c in clips_sorted:
            date_str = c.date.strftime("%Y-%m-%d %H:%M") if c.date else "未知日期"
            if c.clip_type == "bookmark":
                lines.append(f"- **书签** | 第 {c.page} 页 | {date_str}")
            else:
                lines.append(f"> {c.content}")
                lines.append("")
                lines.append(f"  — 第 {c.page} 页, 位置 {c.location} | {date_str}")
                lines.append("")
            lines.append("---")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")

    # Write index
    index_path = _available_path(out / "Kindle Notes Index.md", reserved_paths)
    index_lines = ["# Kindle Notes Index", ""]
    for book_title in groups:
        safe_name = names[book_title]
        index_lines.append(f"- [{book_title}]({safe_name}.md)")
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    return exported


def export_csv(clippings: list[Clipping], output_path: str | Path):
    """Export all clippings to a single CSV file."""
    path = Path(output_path)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["书名", "作者", "类型", "页码", "位置", "日期", "内容"])
        for c in sorted(clippings, key=lambda c: (c.book_title, c.date or _min_date())):
            writer.writerow([
                c.book_title, c.author, c.type_display,
                c.page, c.location,
                c.date.isoformat() if c.date else "",
                c.content,
            ])


def export_json(clippings: list[Clipping], output_path: str | Path):
    """Export all clippings to a single JSON file."""
    path = Path(output_path)
    data = [
        {
            "book_title": c.book_title,
            "author": c.author,
            "type": c.clip_type,
            "page": c.page,
            "location": c.location,
            "date": c.date.isoformat() if c.date else None,
            "content": c.content,
        }
        for c in clippings
    ]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_filename(name: str) -> str:
    """Convert book title to a safe filename."""
    invalid = '<>:"/\\|?*'
    result = name[:60].strip()
    for ch in invalid:
        result = result.replace(ch, "_")
    result = result.rstrip(". ")
    result = result or "untitled"
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if result.upper() in reserved:
        result = f"_{result}"
    return result


def _unique_filenames(titles) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for title in titles:
        base = _safe_filename(title)
        candidate = base
        if candidate.casefold() in used:
            digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
            candidate = f"{base[:51]}-{digest}"
        used.add(candidate.casefold())
        result[title] = candidate
    return result


def _available_path(path: Path, reserved: set[str]) -> Path:
    candidate = path
    index = 1
    while candidate.exists() or str(candidate).casefold() in reserved:
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        index += 1
    reserved.add(str(candidate).casefold())
    return candidate


def _min_date():
    from datetime import datetime
    return datetime(2000, 1, 1)
