"""Application settings. Production fails fast on missing secrets."""

from __future__ import annotations

import os
from pathlib import Path

_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
STORAGE_DIR = Path(os.environ.get("IVS_STORAGE_DIR", ROOT_DIR / "storage"))
MODELS_DIR = ROOT_DIR / "models"
SAMPLES_DIR = ROOT_DIR / "samples"
VIDEOS_DIR = STORAGE_DIR / "videos"
CLIPS_DIR = STORAGE_DIR / "clips"
THUMBS_DIR = STORAGE_DIR / "thumbs"

ENV = os.environ.get("IVS_ENV", "development").strip().lower()
IS_PRODUCTION = ENV in {"production", "prod"}
# Temporary local testing mode. Production always requires authentication.
DEV_AUTH_BYPASS = ENV == "development" and _bool("IVS_DEV_AUTH_BYPASS", False)

DATABASE_URL = os.environ.get(
    "IVS_DATABASE_URL",
    "dbname=intelligent_video_search user=postgres host=localhost",
)
REDIS_URL = os.environ.get("IVS_REDIS_URL", "redis://localhost:6379/0")
REQUIRE_REDIS = _bool("IVS_REQUIRE_REDIS", False)
REQUIRE_PGVECTOR = _bool("IVS_REQUIRE_PGVECTOR", False)

JWT_SECRET = os.environ.get("IVS_JWT_SECRET", "dev-change-me-ivs-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("IVS_JWT_EXPIRE_MINUTES", "30" if IS_PRODUCTION else "10080"))
JWT_REFRESH_DAYS = int(os.environ.get("IVS_JWT_REFRESH_DAYS", "14"))

CORS_ORIGINS = _csv(
    "IVS_CORS_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173",
)

YOLO_MODEL = os.environ.get("IVS_YOLO_MODEL", str(MODELS_DIR / "yolov8n.pt"))
CLIP_MODEL = os.environ.get("IVS_CLIP_MODEL", "openai/clip-vit-base-patch32")
# Avoid oversubscribing small CPUs; shared by YOLO and CLIP.
TORCH_THREADS = max(int(os.environ.get("IVS_TORCH_THREADS", str(min(4, os.cpu_count() or 1)))), 1)
CHANGE_THRESHOLD = float(os.environ.get("IVS_CHANGE_THRESHOLD", "0.90"))
MAX_GAP_SEC = float(os.environ.get("IVS_MAX_GAP_SEC", "15"))
CLIP_PADDING_SEC = float(os.environ.get("IVS_CLIP_PADDING_SEC", "5"))
SEARCH_MIN_SCORE = float(os.environ.get("IVS_SEARCH_MIN_SCORE", "0.23"))
SEARCH_SCORE_MARGIN = max(float(os.environ.get("IVS_SEARCH_SCORE_MARGIN", "0.04")), 0.0)
INDEX_STRIDE = max(int(os.environ["IVS_INDEX_STRIDE"]), 1) if os.environ.get("IVS_INDEX_STRIDE") else None
INDEX_TARGET_FPS = max(float(os.environ.get("IVS_INDEX_TARGET_FPS", "5")), 0.1)
CLIP_BATCH_SIZE = max(int(os.environ.get("IVS_CLIP_BATCH_SIZE", "8")), 1)
EMBED_MIN_GAP_SEC = max(float(os.environ.get("IVS_EMBED_MIN_GAP_SEC", "0.5")), 0.0)
EMBED_HEARTBEAT_SEC = max(float(os.environ.get("IVS_EMBED_HEARTBEAT_SEC", "2")), EMBED_MIN_GAP_SEC)
# Full-frame CLIP check interval; 0 disables scene embeddings.
SCENE_INTERVAL_SEC = max(float(os.environ.get("IVS_SCENE_INTERVAL_SEC", "2")), 0.0)
WARM_MODELS = _bool("IVS_WARM_MODELS", True)
MAX_INDEX_FRAMES = os.environ.get("IVS_MAX_INDEX_FRAMES")
MAX_INDEX_FRAMES_INT = int(MAX_INDEX_FRAMES) if MAX_INDEX_FRAMES else None
MAX_ACTIVE_INDEX_JOBS = int(os.environ.get("IVS_MAX_ACTIVE_INDEX_JOBS", "2"))

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_UPLOAD_BYTES = int(os.environ.get("IVS_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
MAX_DURATION_SEC = float(os.environ.get("IVS_MAX_DURATION_SEC", "600"))

S3_BUCKET = os.environ.get("IVS_S3_BUCKET", "")
S3_REGION = os.environ.get("IVS_S3_REGION", "us-east-1")
S3_ENDPOINT_URL = os.environ.get("IVS_S3_ENDPOINT_URL") or None
S3_ACCESS_KEY = os.environ.get("IVS_S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("IVS_S3_SECRET_KEY", "")
S3_PREFIX = os.environ.get("IVS_S3_PREFIX", "ivs")
USE_S3 = bool(S3_BUCKET)

SMTP_HOST = os.environ.get("IVS_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("IVS_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("IVS_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("IVS_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("IVS_SMTP_FROM", "noreply@clipseek.local")
PUBLIC_APP_URL = os.environ.get("IVS_PUBLIC_APP_URL", "http://127.0.0.1:5173")

AUTH_RATE_LIMIT = int(os.environ.get("IVS_AUTH_RATE_LIMIT", "10"))
AUTH_RATE_WINDOW_SEC = int(os.environ.get("IVS_AUTH_RATE_WINDOW_SEC", "60"))

PERSON_QUERY_WORDS = {"man", "woman", "person", "people", "boy", "girl", "human", "pedestrian"}


def validate_production_config() -> None:
    if not IS_PRODUCTION:
        return
    problems: list[str] = []
    if not JWT_SECRET or JWT_SECRET == "dev-change-me-ivs-secret" or len(JWT_SECRET) < 32:
        problems.append("IVS_JWT_SECRET must be a strong secret (32+ chars)")
    if "localhost" in DATABASE_URL and os.environ.get("IVS_ALLOW_LOCAL_DB") != "1":
        problems.append("IVS_DATABASE_URL should point at production Postgres + pgvector")
    if not CORS_ORIGINS or "*" in CORS_ORIGINS:
        problems.append("IVS_CORS_ORIGINS must be an explicit frontend origin list")
    if problems:
        raise RuntimeError("Production config invalid: " + "; ".join(problems))


def ensure_storage_dirs() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
