"""Local disk or S3-compatible object storage."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import (
    CLIPS_DIR,
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_PREFIX,
    S3_REGION,
    S3_SECRET_KEY,
    THUMBS_DIR,
    USE_S3,
    VIDEOS_DIR,
)

logger = logging.getLogger(__name__)


class MediaStorage:
    def put_bytes(self, key: str, data: bytes) -> str:
        raise NotImplementedError

    def put_file(self, key: str, path: Path) -> str:
        raise NotImplementedError

    def local_path(self, stored_path: str, kind: str = "videos") -> Path:
        raise NotImplementedError

    def delete(self, stored_path: str) -> None:
        raise NotImplementedError

    def exists(self, stored_path: str) -> bool:
        raise NotImplementedError


class LocalStorage(MediaStorage):
    def _dir(self, kind: str) -> Path:
        if kind == "clips":
            return CLIPS_DIR
        if kind == "thumbs":
            return THUMBS_DIR
        return VIDEOS_DIR

    def put_bytes(self, key: str, data: bytes) -> str:
        kind, name = key.split("/", 1) if "/" in key else ("videos", key)
        dest = self._dir(kind) / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    def put_file(self, key: str, path: Path) -> str:
        kind, name = key.split("/", 1) if "/" in key else ("videos", key)
        dest = self._dir(kind) / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != dest.resolve():
            dest.write_bytes(path.read_bytes())
        return str(dest)

    def local_path(self, stored_path: str, kind: str = "videos") -> Path:
        path = Path(stored_path)
        if path.exists():
            return path
        candidate = self._dir(kind) / Path(stored_path).name
        return candidate

    def delete(self, stored_path: str) -> None:
        # Older database rows may point at the pre-reorganization media directory.
        path = self.local_path(stored_path)
        if path.exists():
            path.unlink()

    def exists(self, stored_path: str) -> bool:
        return self.local_path(stored_path).exists()


class S3Storage(MediaStorage):
    def __init__(self) -> None:
        import boto3

        kwargs = {"region_name": S3_REGION}
        if S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = S3_ENDPOINT_URL
        if S3_ACCESS_KEY and S3_SECRET_KEY:
            kwargs["aws_access_key_id"] = S3_ACCESS_KEY
            kwargs["aws_secret_access_key"] = S3_SECRET_KEY
        self.client = boto3.client("s3", **kwargs)
        self.local = LocalStorage()

    def _s3_key(self, key: str) -> str:
        return f"{S3_PREFIX}/{key}".replace("//", "/")

    def put_bytes(self, key: str, data: bytes) -> str:
        s3_key = self._s3_key(key)
        self.client.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=data)
        return f"s3://{S3_BUCKET}/{s3_key}"

    def put_file(self, key: str, path: Path) -> str:
        s3_key = self._s3_key(key)
        self.client.upload_file(str(path), S3_BUCKET, s3_key)
        return f"s3://{S3_BUCKET}/{s3_key}"

    def local_path(self, stored_path: str, kind: str = "videos") -> Path:
        if not stored_path.startswith("s3://"):
            return self.local.local_path(stored_path, kind)
        name = Path(stored_path).name
        dest = self.local._dir(kind) / name
        if dest.exists():
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        _, _, rest = stored_path.partition("s3://")
        _, _, key = rest.partition("/")
        self.client.download_file(S3_BUCKET, key, str(dest))
        return dest

    def delete(self, stored_path: str) -> None:
        if stored_path.startswith("s3://"):
            _, _, rest = stored_path.partition("s3://")
            _, _, key = rest.partition("/")
            try:
                self.client.delete_object(Bucket=S3_BUCKET, Key=key)
            except Exception as exc:
                logger.warning("S3 delete failed for %s: %s", stored_path, exc)
            local = self.local._dir("videos") / Path(stored_path).name
            if local.exists():
                local.unlink()
            return
        self.local.delete(stored_path)

    def exists(self, stored_path: str) -> bool:
        if not stored_path.startswith("s3://"):
            return self.local.exists(stored_path)
        _, _, rest = stored_path.partition("s3://")
        _, _, key = rest.partition("/")
        try:
            self.client.head_object(Bucket=S3_BUCKET, Key=key)
            return True
        except Exception:
            return False


_storage: MediaStorage | None = None


def get_storage() -> MediaStorage:
    global _storage
    if _storage is None:
        _storage = S3Storage() if USE_S3 else LocalStorage()
        logger.info("Media storage: %s", "s3" if USE_S3 else "local")
    return _storage
