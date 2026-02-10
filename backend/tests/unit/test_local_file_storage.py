from app.infrastructure.storage.local_file_storage import LocalFileStorage


def test_delete_removes_file_inside_upload_dir(tmp_path) -> None:
    upload_dir = tmp_path / "uploads"
    storage = LocalFileStorage(upload_dir=str(upload_dir))
    target = upload_dir / "inside.txt"
    target.write_text("ok", encoding="utf-8")

    storage.delete(storage_path=str(target))

    assert not target.exists()


def test_delete_ignores_file_outside_upload_dir(tmp_path) -> None:
    upload_dir = tmp_path / "uploads"
    storage = LocalFileStorage(upload_dir=str(upload_dir))
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")

    storage.delete(storage_path=str(outside))

    assert outside.exists()
