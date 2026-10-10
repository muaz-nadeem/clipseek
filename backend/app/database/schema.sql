-- App schema: users, videos, objects with pgvector when available

CREATE EXTENSION IF NOT EXISTS vector;

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

-- Ensure user_id column exists on older DBs
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'videos' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE videos ADD COLUMN user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Convert objects.embedding from real[] to vector(512) in place, keeping indexed rows
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'objects'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'objects' AND column_name = 'embedding' AND udt_name = '_float4'
        ) THEN
            ALTER TABLE objects
                ALTER COLUMN embedding TYPE vector(512) USING embedding::vector(512);
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'objects' AND column_name = 'video_id' AND data_type = 'text'
        ) THEN
            DROP TABLE objects;
        END IF;
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
    embedding       vector(512) NOT NULL
);

CREATE INDEX IF NOT EXISTS objects_video_track_idx
    ON objects (video_id, track_id);

CREATE INDEX IF NOT EXISTS videos_status_idx
    ON videos (status);

CREATE INDEX IF NOT EXISTS videos_user_id_idx
    ON videos (user_id);

CREATE INDEX IF NOT EXISTS objects_embedding_hnsw_idx
    ON objects
    USING hnsw (embedding vector_cosine_ops);
