import pytest

psycopg = pytest.importorskip("psycopg")

from app.database.connection import _try_pgvector_schema


class FakeCursor:
    def __init__(self, extension_available: bool, schema_error: Exception | None = None):
        self.extension_available = extension_available
        self.schema_error = schema_error
        self.executed: list[str] = []

    def execute(self, sql):
        self.executed.append(sql)
        if sql == "PGVECTOR SCHEMA" and self.schema_error is not None:
            raise self.schema_error

    def fetchone(self):
        return (1,) if self.extension_available else None


def test_missing_extension_skips_pgvector_schema():
    cur = FakeCursor(extension_available=False)
    assert _try_pgvector_schema(cur, "PGVECTOR SCHEMA") is False
    assert "PGVECTOR SCHEMA" not in cur.executed


def test_extension_load_failure_falls_back():
    cur = FakeCursor(True, psycopg.Error('could not load library "vector.dll"'))
    assert _try_pgvector_schema(cur, "PGVECTOR SCHEMA") is False


def test_working_extension_applies_pgvector_schema():
    cur = FakeCursor(extension_available=True)
    assert _try_pgvector_schema(cur, "PGVECTOR SCHEMA") is True
    assert cur.executed[-1] == "PGVECTOR SCHEMA"


def test_pgvector_schema_converts_real_arrays_instead_of_dropping():
    from pathlib import Path

    import app.database.connection as connection

    sql = (Path(connection.__file__).parent / "schema.sql").read_text(encoding="utf-8")
    real_array_branch = sql.split("udt_name = '_float4'", 1)[1].split("END IF;", 1)[0]
    assert "USING embedding::vector(512)" in real_array_branch
    assert "DROP TABLE" not in real_array_branch
