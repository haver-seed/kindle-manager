from kindle_manager.core.scanner import scan_kindle


def test_scans_documents_recursively_and_supports_txt(tmp_path):
    documents = tmp_path / "documents"
    nested = documents / "Personal"
    nested.mkdir(parents=True)
    (nested / "Short Note.txt").write_text("hello", encoding="utf-8")
    (nested / "Novel.mobi").write_bytes(b"x" * 100)
    ignored = nested / "Novel.sdr"
    ignored.mkdir()
    (ignored / "fragment.mobi").write_bytes(b"x" * 100)
    (nested / "tiny.kfx").write_bytes(b"x" * 20)

    books = scan_kindle(tmp_path)
    assert {book.title for book in books} == {"Novel", "Short Note"}
    assert next(book for book in books if book.title == "Novel").sdr_path == ignored


def test_ambiguous_prefix_sidecars_are_not_associated(tmp_path):
    documents = tmp_path / "documents"
    documents.mkdir()
    stem = "A" * 50
    book = documents / f"{stem}.mobi"
    book.write_bytes(b"x" * 100)
    (documents / f"{stem}-one.sdr").mkdir()
    (documents / f"{stem}-two.sdr").mkdir()

    assert scan_kindle(tmp_path)[0].sdr_path is None
