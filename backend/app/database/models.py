"""Database access for users, videos, and objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import psycopg

from app.database.connection import uses_pgvector


@dataclass
class UserRecord:
    id: int
    email: str
    password_hash: str
    created_at: datetime


@dataclass
class VideoRecord:
    id: int
    filename: str
    stored_path: str
    status: str
    duration: float | None
    error_message: str | None
    created_at: datetime
    indexed_at: datetime | None
    user_id: int | None = None
    progress: float = 0.0
    object_count: int = 0


def _video_from_row(row: tuple) -> VideoRecord:
    return VideoRecord(
        id=row[0],
        filename=row[1],
        stored_path=row[2],
        status=row[3],
        duration=row[4],
        error_message=row[5],
        created_at=row[6],
        indexed_at=row[7],
        user_id=row[8] if len(row) > 8 else None,
        progress=float(row[9] or 0) if len(row) > 9 else 0.0,
        object_count=int(row[10] or 0) if len(row) > 10 else 0,
    )


def create_user(conn: psycopg.Connection, email: str, password_hash: str) -> UserRecord:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
            RETURNING id, email, password_hash, created_at
            """,
            (email.lower().strip(), password_hash),
        )
        row = cur.fetchone()
    return UserRecord(*row)


def get_user_by_email(conn: psycopg.Connection, email: str) -> UserRecord | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE email = %s
            """,
            (email.lower().strip(),),
        )
        row = cur.fetchone()
    return UserRecord(*row) if row else None


def get_user_by_id(conn: psycopg.Connection, user_id: int) -> UserRecord | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    return UserRecord(*row) if row else None


def create_video(
    conn: psycopg.Connection,
    filename: str,
    stored_path: str,
    *,
    user_id: int | None = None,
    status: str = "queued",
) -> VideoRecord:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO videos (filename, stored_path, status, user_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, filename, stored_path, status, duration,
                      error_message, created_at, indexed_at, user_id,
                      COALESCE(progress, 0), COALESCE(object_count, 0)
            """,
            (filename, stored_path, status, user_id),
        )
        row = cur.fetchone()
    return _video_from_row(row)


def get_video(conn: psycopg.Connection, video_id: int) -> VideoRecord | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, filename, stored_path, status, duration,
                   error_message, created_at, indexed_at, user_id,
                   COALESCE(progress, 0), COALESCE(object_count, 0)
            FROM videos
            WHERE id = %s
            """,
            (video_id,),
        )
        row = cur.fetchone()
    return _video_from_row(row) if row else None


def list_videos(
    conn: psycopg.Connection,
    limit: int = 50,
    *,
    user_id: int | None = None,
) -> list[VideoRecord]:
    with conn.cursor() as cur:
        if user_id is None:
            cur.execute(
                """
                SELECT id, filename, stored_path, status, duration,
                       error_message, created_at, indexed_at, user_id,
                       COALESCE(progress, 0), COALESCE(object_count, 0)
                FROM videos
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
        else:
            cur.execute(
                """
                SELECT id, filename, stored_path, status, duration,
                       error_message, created_at, indexed_at, user_id,
                       COALESCE(progress, 0), COALESCE(object_count, 0)
                FROM videos
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
        rows = cur.fetchall()
    return [_video_from_row(row) for row in rows]


def update_video_status(
    conn: psycopg.Connection,
    video_id: int,
    status: str,
    *,
    duration: float | None = None,
    error_message: str | None = None,
    mark_indexed: bool = False,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE videos
            SET status = %s,
                duration = COALESCE(%s, duration),
                error_message = %s,
                indexed_at = CASE WHEN %s THEN NOW() ELSE indexed_at END
            WHERE id = %s
            """,
            (status, duration, error_message, mark_indexed, video_id),
        )


def update_video_progress(
    conn: psycopg.Connection,
    video_id: int,
    progress: float,
    *,
    object_count: int | None = None,
) -> None:
    with conn.cursor() as cur:
        if object_count is None:
            cur.execute(
                "UPDATE videos SET progress = %s WHERE id = %s",
                (progress, video_id),
            )
        else:
            cur.execute(
                "UPDATE videos SET progress = %s, object_count = %s WHERE id = %s",
                (progress, object_count, video_id),
            )


def count_active_jobs(conn: psycopg.Connection, user_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM videos
            WHERE user_id = %s AND status IN ('queued', 'processing')
            """,
            (user_id,),
        )
        return int(cur.fetchone()[0])


def list_unfinished_video_ids(conn: psycopg.Connection) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM videos
            WHERE status IN ('queued', 'processing')
            ORDER BY id
            """
        )
        return [int(row[0]) for row in cur.fetchall()]


def delete_video(conn: psycopg.Connection, video_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM objects WHERE video_id = %s", (video_id,))
        cur.execute("DELETE FROM videos WHERE id = %s", (video_id,))


def delete_user(conn: psycopg.Connection, user_id: int) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT stored_path FROM videos WHERE user_id = %s", (user_id,))
        paths = [row[0] for row in cur.fetchall()]
        cur.execute("DELETE FROM videos WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    return paths


def create_refresh_token(
    conn: psycopg.Connection,
    user_id: int,
    token_hash: str,
    expires_at,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user_id, token_hash, expires_at),
        )


def get_refresh_token(conn: psycopg.Connection, token_hash: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, expires_at, revoked
            FROM refresh_tokens
            WHERE token_hash = %s
            """,
            (token_hash,),
        )
        return cur.fetchone()


def revoke_refresh_token(conn: psycopg.Connection, token_hash: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE token_hash = %s",
            (token_hash,),
        )


def revoke_user_refresh_tokens(conn: psycopg.Connection, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = %s",
            (user_id,),
        )


def create_password_reset(
    conn: psycopg.Connection,
    user_id: int,
    token_hash: str,
    expires_at,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user_id, token_hash, expires_at),
        )


def consume_password_reset(conn: psycopg.Connection, token_hash: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, expires_at, used
            FROM password_reset_tokens
            WHERE token_hash = %s
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        token_id, user_id, expires_at, used = row
        if used:
            return None
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            return None
        cur.execute("UPDATE password_reset_tokens SET used = TRUE WHERE id = %s", (token_id,))
        return int(user_id)


def update_password(conn: psycopg.Connection, user_id: int, password_hash: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, user_id),
        )


def delete_objects_for_video(conn: psycopg.Connection, video_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM objects WHERE video_id = %s", (video_id,))


def insert_object(
    conn: psycopg.Connection,
    *,
    video_id: int,
    track_id: int,
    class_name: str,
    confidence: float,
    timestamp: float,
    frame_number: int,
    bounding_box: list[float],
    embedding: np.ndarray,
) -> int:
    emb = embedding.astype(np.float32)
    if uses_pgvector():
        from pgvector.psycopg import Vector

        emb_param: Any = Vector(emb.tolist())
    else:
        emb_param = emb.tolist()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO objects (
                video_id, track_id, class_name, confidence,
                timestamp, frame_number, bounding_box, embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                video_id,
                track_id,
                class_name,
                confidence,
                timestamp,
                frame_number,
                bounding_box,
                emb_param,
            ),
        )
        return int(cur.fetchone()[0])


def search_objects_by_embedding(
    conn: psycopg.Connection,
    query_embedding: np.ndarray,
    *,
    top_k: int = 20,
    video_id: int | None = None,
    class_names: list[str] | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    emb = query_embedding.astype(np.float32)
    filters = []
    params: list[Any] = []

    if uses_pgvector():
        from pgvector.psycopg import Vector

        query_param: Any = Vector(emb.tolist())
        score_expr = "1 - (embedding <=> %s)"
        order_expr = "embedding <=> %s"
    else:
        query_param = emb.tolist()
        score_expr = "cosine_similarity(embedding, %s::real[])"
        order_expr = "cosine_similarity(embedding, %s::real[]) DESC"

    # score param, then optional filters, then order param, then limit
    select_sql = f"""
        SELECT
            o.id, o.video_id, o.track_id, o.class_name, o.confidence,
            o.timestamp, o.frame_number, o.bounding_box,
            {score_expr} AS similarity
        FROM objects o
        JOIN videos v ON v.id = o.video_id
    """
    params.append(query_param)

    if video_id is not None:
        filters.append("o.video_id = %s")
        params.append(video_id)
    if class_names:
        filters.append("o.class_name = ANY(%s)")
        params.append(class_names)
    if user_id is not None:
        filters.append("v.user_id = %s")
        params.append(user_id)

    where_sql = (" WHERE " + " AND ".join(filters)) if filters else ""
    if uses_pgvector():
        order_sql = f" ORDER BY {order_expr} LIMIT %s"
        params.extend([query_param, top_k])
    else:
        order_sql = f" ORDER BY {order_expr} LIMIT %s"
        params.extend([query_param, top_k])

    with conn.cursor() as cur:
        cur.execute(select_sql + where_sql + order_sql, params)
        rows = cur.fetchall()

    results = []
    for row in rows:
        results.append(
            {
                "object_id": row[0],
                "video_id": row[1],
                "track_id": row[2],
                "class_name": row[3],
                "confidence": float(row[4]),
                "timestamp": float(row[5]),
                "frame_number": int(row[6]),
                "bounding_box": list(row[7]),
                "score": float(row[8]),
            }
        )
    return results
