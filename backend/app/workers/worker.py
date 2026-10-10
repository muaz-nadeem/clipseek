"""Run: python -m app.workers.worker"""

from __future__ import annotations

from redis import Redis
from rq import Worker

from app.config import REDIS_URL, ensure_storage_dirs, validate_production_config
from app.database.connection import apply_schema
from app.utils.logging import configure_logging


def main() -> None:
    configure_logging()
    validate_production_config()
    ensure_storage_dirs()
    apply_schema()
    redis_conn = Redis.from_url(REDIS_URL)
    worker = Worker(["indexing"], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
