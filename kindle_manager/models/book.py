from dataclasses import dataclass
from pathlib import Path


@dataclass
class Book:
    title: str
    asin: str = ""
    format: str = ""
    file_path: Path | None = None
    file_size: int = 0
    sdr_path: Path | None = None
    has_cover: bool = False
    cover_path: Path | None = None
    is_sideloaded: bool = False
    last_position: int = 0
    highlight_count: int = 0

    @property
    def has_read(self) -> bool:
        return self.last_position > 0

    @property
    def size_display(self) -> str:
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

    @property
    def format_display(self) -> str:
        return self.format.upper()
