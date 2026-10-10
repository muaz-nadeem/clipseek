"""PostgreSQL connection helpers."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg

from app.config import DATABASE_URL, REQUIRE_PGVECTOR

logger = logging.getLogger(__name__)

_USE_PGVECTOR: bool | None = None


def get_connection() -> psycopg.Connection:
    conn = psycopg.connect(DATABASE_URL)
    if uses_pgvector():
        from pgvector.psycopg import register_vector

        register_vector(conn)
    return conn


@contextmanager
def db_session() -> Iterator[psycopg.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def uses_pgvector() -> bool:
    global _USE_PGVECTOR
    if _USE_PGVECTOR is not None:
        return _USE_PGVECTOR
    # Default True after successful schema apply; probe if unset
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'objects' AND column_name = 'embedding'
                      AND udt_name = 'vector'
                    """
                )
                _USE_PGVECTOR = cur.fetchone() is not None
    except Exception:
        _USE_PGVECTOR = False
    return _USE_PGVECTOR


def ping() -> bool:
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False


def _try_pgvector_schema(cur: psycopg.Cursor, pgvector_sql: str) -> bool:
    cur.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    if cur.fetchone() is None:
        logger.info("pgvector extension is not installed on this server; using REAL[] embeddings")
        return False
    try:
        # One simple-protocol script runs as a single implicit transaction, so a
        # failed extension load leaves the REAL[] table untouched.
        cur.execute(pgvector_sql)
    except psycopg.Error as exc:
        logger.warning("pgvector unavailable (%s); using REAL[] embeddings", exc)
        return False
    return True


def apply_schema() -> None:
    global _USE_PGVECTOR
    root = Path(__file__).resolve().parent
    pgvector_sql = (root / "schema.sql").read_text(encoding="utf-8")
    fallback_sql = (root / "schema_fallback.sql").read_text(encoding="utf-8")
    common_sql = (root / "schema_common.sql").read_text(encoding="utf-8")

    with psycopg.connect(DATABASE_URL) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            if _try_pgvector_schema(cur, pgvector_sql):
                _USE_PGVECTOR = True
                logger.info("Applied pgvector schema")
            elif REQUIRE_PGVECTOR:
                raise RuntimeError(
                    "pgvector is required (IVS_REQUIRE_PGVECTOR=1) but failed to load."
                )
            else:
                cur.execute(fallback_sql)
                _USE_PGVECTOR = False
                logger.info("Applied fallback REAL[] schema")
            cur.execute(common_sql)
