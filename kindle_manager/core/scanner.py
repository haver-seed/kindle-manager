import re
from pathlib import Path
from kindle_manager.models.book import Book
from kindle_manager.core.progress import read_progress

# ASIN pattern: _B + 9-10 alphanumeric chars before extension
ASIN_PATTERN = re.compile(r"_(B[A-Z0-9]{9,})\.(kfx|azw)$")
# Sideloaded book with hex hash suffix (e.g. title{32-hex-hash}.azw3r)
SIDELOAD_HASH = re.compile(r"[a-f0-9]{32}")
# File extensions that are actual book files (not fragments)
BOOK_EXTS = {".kfx", ".azw3", ".azw", ".mobi", ".pdf", ".epub", ".txt"}
# Minimum file size to be considered a real book (filters out KFX fragments)
MIN_BOOK_SIZE = 10_000  # 10 KB


def scan_kindle(kindle_root: str | Path) -> list[Book]:
    root = Path(kindle_root)
    if not root.exists():
        raise FileNotFoundError(f"Kindle drive not found: {root}")

    documents = root / "documents"
    if not documents.is_dir():
        return []

    books: list[Book] = []
    seen: set[Path] = set()
    try:
        candidates = documents.rglob("*")
        for f in candidates:
            if not f.is_file() or f.suffix.lower() not in BOOK_EXTS:
                continue
            if any(part.lower().endswith(".sdr") for part in f.parts):
                continue
            try:
                resolved = f.resolve()
                size = f.stat().st_size
            except OSError:
                continue
            if resolved in seen or size == 0:
                continue
            # Tiny KFX/AZW files are normally metadata fragments, not books.
            if f.suffix.lower() in {".kfx", ".azw"} and size < MIN_BOOK_SIZE:
                continue
            seen.add(resolved)
            try:
                books.append(_build_book(f))
            except OSError:
                continue
    except OSError:
        # A device may disappear during traversal. Return what was found safely.
        pass

    books.sort(key=lambda b: b.title)
    return books


def _build_book(f: Path) -> Book:
    title, asin, is_sideloaded = _parse_book_filename(f)
    sdr = _find_sdr(f)
    last_pos, highlight_cnt = (0, 0)
    cover_path = None
    if sdr:
        try:
            prog = read_progress(sdr)
            last_pos = prog.last_position
            highlight_cnt = prog.highlight_count
        except (OSError, ValueError):
            pass
        cover_path = _find_cover(sdr, asin)
    return Book(
        title=title,
        asin=asin,
        format=f.suffix[1:].lower(),
        file_path=f,
        file_size=f.stat().st_size,
        sdr_path=sdr,
        has_cover=cover_path is not None,
        cover_path=cover_path,
        is_sideloaded=is_sideloaded,
        last_position=last_pos,
        highlight_count=highlight_cnt,
    )


def _parse_book_filename(f: Path) -> tuple[str, str, bool]:
    """Extract title, ASIN, and sideloaded flag from a book filename."""
    match = ASIN_PATTERN.search(f.name)
    if match:
        title = f.name[:match.start()]
        title = _clean_title(title)
        return title, match.group(1), False

    # Check for sideloaded books with hash suffix
    if SIDELOAD_HASH.search(f.stem):
        title = _clean_title(f.stem)
        return title, "", True

    title = _clean_title(f.stem)
    return title, "", True


def _clean_title(name: str) -> str:
    name = name.rstrip("_ -")
    if len(name) > 80:
        name = name[:77] + "..."
    return name


def _find_sdr(book_file: Path) -> Path | None:
    stem = book_file.stem
    for candidate in [
        book_file.parent / f"{stem}.sdr",
        book_file.parent / f"{book_file.name}.sdr",
    ]:
        if candidate.exists() and candidate.is_dir():
            return candidate
    # Prefix matching is only safe when it yields exactly one candidate.
    try:
        matches = [
            d for d in book_file.parent.iterdir()
            if d.is_dir() and d.name.endswith(".sdr") and d.name.startswith(stem[:40])
        ]
    except OSError:
        matches = []
    if len(matches) == 1:
        return matches[0]
    return None


def _find_cover(sdr: Path, asin: str = "") -> Path | None:
    """Find the cover image for a book."""
    # Check .sdr assets folder
    assets = sdr / "assets"
    if assets.exists():
        for f in assets.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
                return f
    # Check system thumbnails (named by ASIN or UUID)
    if asin:
        documents = next((p for p in sdr.parents if p.name.lower() == "documents"), None)
        thumb_dir = documents.parent / "system" / "thumbnails" if documents else None
        if thumb_dir and thumb_dir.exists():
            for f in thumb_dir.iterdir():
                if f.is_file() and asin in f.name and f.suffix.lower() in (".jpg", ".png", ".jpeg"):
                    return f
    return None
