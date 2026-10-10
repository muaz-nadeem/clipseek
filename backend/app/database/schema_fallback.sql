-- Fallback schema when pgvector extension cannot be loaded

CREATE OR REPLACE FUNCTION cosine_similarity(a real[], b real[])
RETURNS real
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    dot double precision := 0;
    na  double precision := 0;
    nb  double precision := 0;
    i   integer;
    n   integer;
BEGIN
    n := array_length(a, 1);
    IF n IS NULL OR n <> array_length(b, 1) THEN
        RETURN 0;
    END IF;

    FOR i IN 1..n LOOP
        dot := dot + a[i] * b[i];
        na  := na  + a[i] * a[i];
        nb  := nb  + b[i] * b[i];
    END LOOP;

    IF na = 0 OR nb = 0 THEN
        RETURN 0;
    END IF;

    RETURN (dot / (sqrt(na) * sqrt(nb)))::real;
END;
$$;

CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS videos (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    filename        TEXT NOT NULL,
    stored_path     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'uploaded',
    duration        DOUBLE PRECISION,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    indexed_at      TIMESTAMPTZ
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'videos' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE videos ADD COLUMN user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'objects' AND column_name = 'video_id' AND data_type = 'text'
    ) THEN
        DROP TABLE objects;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS objects (
    id              BIGSERIAL PRIMARY KEY,
    video_id        BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    track_id        INTEGER NOT NULL,
    class_name      TEXT NOT NULL,
    confidence      REAL NOT NULL,
    timestamp       DOUBLE PRECISION NOT NULL,
    frame_number    INTEGER NOT NULL,
    bounding_box    REAL[4] NOT NULL,
    embedding       REAL[] NOT NULL
);

CREATE INDEX IF NOT EXISTS objects_video_track_idx
    ON objects (video_id, track_id);

CREATE INDEX IF NOT EXISTS videos_status_idx
    ON videos (status);

CREATE INDEX IF NOT EXISTS videos_user_id_idx
    ON videos (user_id);
