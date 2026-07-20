from datetime import datetime

from kindle_manager.core.clippings import _parse_date, parse_clippings, remove_clipping


def test_parses_chinese_am_pm():
    assert _parse_date("2021年11月20日星期六 下午12:21:56") == datetime(
        2021, 11, 20, 12, 21, 56
    )
    assert _parse_date("2021年11月20日星期六 上午12:21:56") == datetime(
        2021, 11, 20, 0, 21, 56
    )


def test_remove_clipping_preserves_other_raw_entry_and_creates_backup(tmp_path):
    documents = tmp_path / "documents"
    documents.mkdir()
    path = documents / "My Clippings.txt"
    first = (
        "第一本书 (作者甲)\n"
        "- 您在第 12 页（位置 #123-124）的标注 | 添加于 2021年11月20日星期六 下午12:21:56\n\n"
        "要删除的内容"
    )
    second = (
        "第二本书 (作者乙)\n"
        "- Your Highlight at page 2 | Location 20-21 | Added on Monday, February 24, 2024 8:07:47 PM\n\n"
        "Keep this exact content"
    )
    path.write_text(f"{first}\n==========\n{second}\n==========\n", encoding="utf-8-sig")

    target = parse_clippings(tmp_path)[0]
    assert remove_clipping(tmp_path, target) == 1
    remaining = path.read_text(encoding="utf-8-sig")
    assert "要删除的内容" not in remaining
    assert second in remaining
    assert path.with_suffix(".txt.bak").exists()


def test_deduplication_keeps_note_and_highlight_at_same_location(tmp_path):
    documents = tmp_path / "documents"
    documents.mkdir()
    path = documents / "My Clippings.txt"
    path.write_text(
        "Book\n- Your Highlight at page 1 | Location 10-11\n\nSame\n==========\n"
        "Book\n- Your Note at page 1 | Location 10-11\n\nSame\n==========\n",
        encoding="utf-8",
    )
    assert [item.clip_type for item in parse_clippings(tmp_path)] == ["highlight", "note"]
