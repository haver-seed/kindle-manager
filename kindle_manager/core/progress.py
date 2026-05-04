import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReadingProgress:
    book_title: str = ""
    last_position: int = 0
    highlight_count: int = 0
    has_read: bool = False


def read_progress(sdr_path: Path) -> ReadingProgress:
    """Extract reading progress from a .sdr directory's yjf/yjr files."""
    progress = ReadingProgress()

    yjf_files = list(sdr_path.glob("*.yjf"))
    if yjf_files:
        _parse_yjf(yjf_files[0], progress)

    yjr_files = list(sdr_path.glob("*.yjr"))
    if yjr_files:
        _parse_yjr(yjr_files[0], progress)

    progress.has_read = progress.last_position > 0
    return progress


def _parse_yjf(path: Path, progress: ReadingProgress):
    """Extract fpr (furthest page read) position from .yjf binary."""
    data = path.read_bytes()
    # Find fpr field and the position that follows it
    # Pattern: fpr .... position_id:location_number
    match = re.search(rb"fpr.{1,20}?([A-Z][a-z0-9A-Z]{2,}A{2,}[A-Za-z0-9]*:(\d+))", data)
    if match:
        try:
            progress.last_position = int(match.group(2))
        except (ValueError, IndexError):
            pass

    # Fallback: look for page.history.record positions
    if progress.last_position == 0:
        positions = re.findall(rb"page\.history\.record.{1,30}?[A-Z][a-z0-9A-Z]{2,}A{2,}[A-Za-z0-9]*:(\d+)", data)
        if positions:
            try:
                progress.last_position = int(positions[-1])
            except (ValueError, IndexError):
                pass


def _parse_yjr(path: Path, progress: ReadingProgress):
    """Extract annotation count from .yjr binary."""
    data = path.read_bytes()
    highlights = re.findall(rb"annotation\.personal\.highlight", data)
    progress.highlight_count = len(highlights)

    # If we didn't get fpr from yjf, try sync_lpr from yjr
    if progress.last_position == 0:
        match = re.search(rb"sync_lpr.{1,20}?[A-Z][a-z0-9A-Z]{2,}A{2,}[A-Za-z0-9]*:(\d+)", data)
        if match:
            try:
                progress.last_position = int(match.group(1))
            except (ValueError, IndexError):
                pass
