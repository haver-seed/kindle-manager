from kindle_manager.core.exporter import export_markdown
from kindle_manager.models.clipping import Clipping


def test_colliding_long_titles_get_unique_files(tmp_path):
    prefix = "相同标题" * 15
    clips = [
        Clipping(book_title=prefix + "甲", content="内容甲"),
        Clipping(book_title=prefix + "乙", content="内容乙"),
    ]
    exported = export_markdown(clips, tmp_path)

    assert len(exported) == 2
    assert len({path.name.casefold() for path in exported.values()}) == 2
    assert all(path.exists() for path in exported.values())


def test_empty_or_windows_reserved_title_is_safe(tmp_path):
    exported = export_markdown([Clipping(book_title="...", content="text")], tmp_path)
    assert next(iter(exported.values())).name == "untitled.md"


def test_existing_export_is_not_overwritten(tmp_path):
    existing = tmp_path / "Book.md"
    existing.write_text("keep", encoding="utf-8")
    exported = export_markdown([Clipping(book_title="Book", content="new")], tmp_path)
    assert existing.read_text(encoding="utf-8") == "keep"
    assert exported["Book"].name == "Book-1.md"
