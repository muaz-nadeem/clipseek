"""One-time helper: verify embedding column type after schema apply."""

from __future__ import annotations

import psycopg

from app.config import DATABASE_URL
from app.database.connection import apply_schema, uses_pgvector


def main() -> None:
    apply_schema()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT udt_name
                FROM information_schema.columns
                WHERE table_name = 'objects' AND column_name = 'embedding'
                """
            )
            row = cur.fetchone()
    print(f"objects.embedding type: {row[0] if row else 'missing'}")
    print(f"uses_pgvector: {uses_pgvector()}")


if __name__ == "__main__":
    main()
