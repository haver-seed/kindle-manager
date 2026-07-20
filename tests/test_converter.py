from kindle_manager.core import converter


def test_get_target_path_never_overwrites(tmp_path):
    source = tmp_path / "book.mobi"
    source.write_bytes(b"book")
    (tmp_path / "book.epub").write_bytes(b"old")

    assert converter.get_target_path(source, "epub").name == "book-converted-1.epub"


def test_conversion_fails_cleanly_without_calibre(tmp_path, monkeypatch):
    source = tmp_path / "book.mobi"
    source.write_bytes(b"book")
    monkeypatch.setattr(converter, "find_calibre", lambda: None)

    ok, message = converter.convert_ebook(source, tmp_path / "book.epub", "epub")
    assert not ok
    assert "Calibre" in message
