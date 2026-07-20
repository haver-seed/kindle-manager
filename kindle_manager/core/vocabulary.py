import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class VocabWord:
    word: str
    stem: str
    lang: str
    book_title: str
    authors: str
    usage: str
    timestamp: datetime | None = None

    @property
    def lang_display(self) -> str:
        labels = {"en": "EN", "zh": "中文", "ja": "日文", "fr": "FR", "de": "DE"}
        return labels.get(self.lang, self.lang.upper())


def read_vocabulary(kindle_root: str | Path) -> list[VocabWord]:
    root = Path(kindle_root)
    db_path = root / "system" / "vocabulary" / "vocab.db"
    if not db_path.exists():
        raise FileNotFoundError(f"vocab.db not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT
                w.word, w.stem, w.lang, w.timestamp,
                b.title as book_title, b.authors,
                l.usage
            FROM WORDS w
            LEFT JOIN LOOKUPS l ON l.word_key = w.id
            LEFT JOIN BOOK_INFO b ON b.id = l.book_key
            ORDER BY w.timestamp DESC
        """).fetchall()

        words: list[VocabWord] = []
        seen: set[str] = set()
        for r in rows:
            word = r["word"] or ""
            if word in seen:
                continue
            seen.add(word)

            ts = r["timestamp"]
            if ts and ts > 0:
                # Display timestamps in the user's local timezone.
                dt = datetime.fromtimestamp(ts / 1000)
            else:
                dt = None

            words.append(VocabWord(
                word=word,
                stem=r["stem"] or word,
                lang=r["lang"] or "unknown",
                book_title=r["book_title"] or "",
                authors=r["authors"] or "",
                usage=r["usage"] or "",
                timestamp=dt,
            ))
        return words
    finally:
        conn.close()
