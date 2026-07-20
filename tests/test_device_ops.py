from kindle_manager.core.device_ops import import_books, move_book_to_trash
from kindle_manager.models.book import Book


def test_import_falls_back_to_documents_root(tmp_path):
    root = tmp_path / "kindle"
    (root / "documents").mkdir(parents=True)
    source = tmp_path / "book.mobi"
    source.write_bytes(b"book")

    result = import_books(root, [source])
    assert result[0].ok
    assert (root / "documents" / "book.mobi").read_bytes() == b"book"


def test_delete_moves_book_and_sidecar_to_recoverable_trash(tmp_path):
    root = tmp_path / "kindle"
    documents = root / "documents"
    documents.mkdir(parents=True)
    file_path = documents / "book.mobi"
    file_path.write_bytes(b"book")
    sidecar = documents / "book.sdr"
    sidecar.mkdir()
    (sidecar / "state").write_text("state")
    book = Book(title="Book", file_path=file_path, sdr_path=sidecar)

    result = move_book_to_trash(root, book)
    assert result.ok
    assert not file_path.exists()
    trash = next((root / ".kindle-manager-trash").iterdir())
    assert (trash / "book.mobi").exists()
    assert (trash / "book.sdr" / "state").exists()


def test_delete_rejects_path_outside_device(tmp_path):
    root = tmp_path / "kindle"
    (root / "documents").mkdir(parents=True)
    outside = tmp_path / "outside.mobi"
    outside.write_bytes(b"book")

    result = move_book_to_trash(root, Book(title="Outside", file_path=outside))
    assert not result.ok
    assert outside.exists()
