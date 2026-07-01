-- banchan schema
-- Boards -> threads -> posts. Images are referenced by posts.
-- post_log is a lightweight audit trail of post events (your "logging").

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid() if needed later

CREATE TABLE IF NOT EXISTS boards (
    id            SERIAL PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    is_imageboard BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS images (
    id            SERIAL PRIMARY KEY,
    filename      TEXT NOT NULL UNIQUE,        -- stored filename on disk (e.g. <uuid>.jpg)
    original_name TEXT NOT NULL,
    mime          TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    width         INTEGER,
    height        INTEGER,
    thumb_path    TEXT,                         -- relative path to thumbnail
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS threads (
    id          SERIAL PRIMARY KEY,
    board_id    INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    subject     TEXT NOT NULL DEFAULT '',
    is_sticky   BOOLEAN NOT NULL DEFAULT FALSE,
    is_locked   BOOLEAN NOT NULL DEFAULT FALSE,
    post_count  INTEGER NOT NULL DEFAULT 0,
    bumped_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_threads_board_bumped
    ON threads (board_id, is_sticky DESC, bumped_at DESC);

CREATE TABLE IF NOT EXISTS posts (
    id            SERIAL PRIMARY KEY,
    thread_id     INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    is_op         BOOLEAN NOT NULL DEFAULT FALSE,
    author_name   TEXT NOT NULL DEFAULT 'Anonymous',
    body          TEXT NOT NULL DEFAULT '',
    image_id      INTEGER REFERENCES images(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_posts_thread_created
    ON posts (thread_id, created_at ASC);

-- Lightweight event log for moderation / debugging.
-- (Not the same as app stdout logging; this is queryable audit history.)
CREATE TABLE IF NOT EXISTS post_log (
    id          BIGSERIAL PRIMARY KEY,
    event       TEXT NOT NULL,                 -- 'thread_create' | 'reply' | 'delete' | ...
    thread_id   INTEGER REFERENCES threads(id) ON DELETE SET NULL,
    post_id     INTEGER REFERENCES posts(id) ON DELETE SET NULL,
    board_slug  TEXT,
    remote_addr TEXT,
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_post_log_created ON post_log (created_at DESC);

-- Helpful views / functions -------------------------------------------------

-- Bump a thread (called when a reply is posted).
CREATE OR REPLACE FUNCTION bump_thread(p_thread_id INTEGER)
RETURNS void AS $$
    UPDATE threads
       SET bumped_at = now()
     WHERE id = p_thread_id
       AND is_locked = FALSE;
$$ LANGUAGE sql;
