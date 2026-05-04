from dataclasses import dataclass
from datetime import datetime


@dataclass
class Clipping:
    book_title: str
    author: str = ""
    clip_type: str = ""  # "highlight" | "bookmark" | "note"
    page: int = 0
    location: str = ""
    date: datetime | None = None
    content: str = ""

    @property
    def type_display(self) -> str:
        labels = {"highlight": "标注", "bookmark": "书签", "note": "笔记"}
        return labels.get(self.clip_type, self.clip_type)
