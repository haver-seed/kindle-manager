import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from kindle_manager.models.clipping import Clipping


def parse_clippings(kindle_root: str | Path) -> list[Clipping]:
    root = Path(kindle_root)
    path = root / "documents" / "My Clippings.txt"
    if not path.exists():
        raise FileNotFoundError(f"My Clippings.txt not found in {root}")

    text = path.read_text(encoding="utf-8-sig")
    entries = text.split("==========")
    clippings: list[Clipping] = []

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        c = _parse_entry(entry)
        if c:
            clippings.append(c)

    # Deduplicate (Kindle appends the same highlight multiple times)
    seen: set[tuple[str, str, str]] = set()
    deduped: list[Clipping] = []
    for c in clippings:
        key = (c.book_title, c.author, c.clip_type, c.location, c.content)
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def group_by_book(clippings: list[Clipping]) -> dict[str, list[Clipping]]:
    groups: dict[str, list[Clipping]] = defaultdict(list)
    for c in clippings:
        groups[c.book_title].append(c)
    return dict(groups)


def remove_clipping(kindle_root: str | Path, target: Clipping) -> int:
    """Remove matching raw entries while preserving every unrelated entry verbatim."""
    from kindle_manager.core.device_ops import atomic_write_text

    path = Path(kindle_root) / "documents" / "My Clippings.txt"
    text = path.read_text(encoding="utf-8-sig")
    entries = text.split("==========")
    target_key = _clipping_key(target)
    kept: list[str] = []
    removed = 0
    for raw in entries:
        parsed = _parse_entry(raw.strip()) if raw.strip() else None
        if parsed and _clipping_key(parsed) == target_key:
            removed += 1
        elif raw.strip():
            kept.append(raw.strip("\r\n"))
    if not removed:
        return 0
    output = "\n==========\n".join(kept)
    if output:
        output += "\n==========\n"
    atomic_write_text(path, output, backup=True)
    return removed


def _clipping_key(c: Clipping) -> tuple[str, str, str, str, str]:
    return c.book_title, c.author, c.clip_type, c.location, c.content


def _parse_entry(entry: str) -> Clipping | None:
    lines = entry.strip().splitlines()
    if len(lines) < 2:
        return None

    # Line 1: "Book Title (Author)" (strip BOM that can appear mid-file)
    title, author = _parse_title_author(lines[0].strip().lstrip("﻿"))

    # Line 2: "- Your Type at page X | Location #A-B | Added on ..."
    meta = lines[1].strip()
    clip_type, page, location, date = _parse_meta(meta)

    # Content: everything after the first blank line
    content_start = 2
    while content_start < len(lines) and not lines[content_start].strip():
        content_start += 1
    content = "\n".join(lines[content_start:]).strip()
    if not content and clip_type == "highlight":
        return None

    return Clipping(
        book_title=title,
        author=author,
        clip_type=clip_type,
        page=page,
        location=location,
        date=date,
        content=content,
    )


def _parse_title_author(line: str) -> tuple[str, str]:
    """Parse 'Book Title (Author)' into (title, author)."""
    # The author is the last parenthesized segment
    match = re.search(r"\(([^)]+)\)$", line)
    if match:
        author = match.group(1)
        title = line[:match.start()].strip()
        # Some titles end with a space before the author paren
        title = title.rstrip()
        return title, author
    return line, ""


def _parse_meta(line: str) -> tuple[str, int, str, datetime | None]:
    """Parse metadata line into (type, page, location, date)."""
    line = line.strip()
    # Remove leading "- Your "
    line = re.sub(r"^-\s*Your\s+", "", line)

    # Determine type
    if "Highlight" in line or "标注" in line:
        clip_type = "highlight"
    elif "Bookmark" in line or "书签" in line:
        clip_type = "bookmark"
    elif "Note" in line or "笔记" in line:
        clip_type = "note"
    else:
        clip_type = "highlight"

    # Extract page
    page_match = re.search(r"page\s+(\d+)", line)
    if not page_match:
        page_match = re.search(r"第\s*(\d+)\s*页", line)
    page = int(page_match.group(1)) if page_match else 0

    # Extract location
    loc_match = re.search(r"Location\s+([\d,\-]+)", line)
    if not loc_match:
        loc_match = re.search(r"位置\s+#?([\d,\-]+)", line)
    location = loc_match.group(1) if loc_match else ""

    # Extract date
    date = None
    # Format: "Added on Monday, February 24, 2024 8:07:47 PM"
    date_match = re.search(r"Added on (.+)$", line)
    if not date_match:
        date_match = re.search(r"添加于 (.+)$", line)
    if date_match:
        date_str = date_match.group(1)
        date = _parse_date(date_str)

    return clip_type, page, location, date


def _parse_date(date_str: str) -> datetime | None:
    """Parse a Kindle date string into datetime."""
    # Python's %p is locale-dependent and normally cannot parse 上午/下午.
    chinese_period = None
    if "上午" in date_str:
        chinese_period = "am"
        date_str = date_str.replace("上午", "")
    elif "下午" in date_str:
        chinese_period = "pm"
        date_str = date_str.replace("下午", "")

    # Remove weekday prefix in Chinese (e.g. "2021年11月20日星期六")
    date_str = re.sub(r"星期[一二三四五六日天]", " ", date_str)
    # Remove weekday in English (e.g. "Monday,")
    date_str = re.sub(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", "", date_str, flags=re.IGNORECASE)
    date_str = date_str.replace(",", " ").strip()
    # Collapse spaces
    date_str = re.sub(r"\s+", " ", date_str)

    formats = [
        "%Y年%m月%d日 %H:%M:%S",
        # English: "November 20, 2021 12:21:56 PM"
        "%B %d %Y %I:%M:%S %p",
        # English: "Nov 20, 2021 12:21:56 PM"
        "%b %d %Y %I:%M:%S %p",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if chinese_period:
                hour = parsed.hour
                if chinese_period == "pm" and hour < 12:
                    hour += 12
                elif chinese_period == "am" and hour == 12:
                    hour = 0
                parsed = parsed.replace(hour=hour)
            return parsed
        except ValueError:
            continue
    return None
