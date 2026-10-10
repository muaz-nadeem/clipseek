"""Existing database paths still resolve after relocating local media."""

from app.services import storage


def test_legacy_path_resolves_and_deletes_relocated_video(tmp_path, monkeypatch):
    videos = tmp_path / "storage" / "videos"
    videos.mkdir(parents=True)
    uploaded = videos / "upload.mp4"
    uploaded.write_bytes(b"video")
    old_path = str(tmp_path / "old-app" / "storage" / "videos" / uploaded.name)
    monkeypatch.setattr(storage, "VIDEOS_DIR", videos)
    media = storage.LocalStorage()
    assert media.local_path(old_path) == uploaded
    assert media.exists(old_path)
    media.delete(old_path)
    assert not uploaded.exists()
    assert not media.exists(old_path)
