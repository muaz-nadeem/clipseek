from fastapi import APIRouter, HTTPException

from app.api.schemas import HealthResponse
from app.config import ENV, REQUIRE_REDIS, USE_S3
from app.database.connection import ping, uses_pgvector
from app.workers.queue import redis_available

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ok = ping()
    redis_ok = redis_available()
    overall = "ok" if db_ok else "degraded"
    return HealthResponse(
        status=overall,
        env=ENV,
        database=db_ok,
        redis=redis_ok,
        pgvector=uses_pgvector() if db_ok else False,
        storage="s3" if USE_S3 else "local",
    )


@router.get("/ready")
def ready() -> dict:
    if not ping():
        raise HTTPException(status_code=503, detail="database unavailable")
    if REQUIRE_REDIS and not redis_available():
        raise HTTPException(status_code=503, detail="redis unavailable")
    return {"status": "ready"}
