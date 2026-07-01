"""Data access. Each function takes a connection (or uses the pool) and returns plain dicts."""
from __future__ import annotations

from typing import Any

from app.db import get_pool

# -- boards ------------------------------------------------------------------

async def list_boards() -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM boards ORDER BY slug")
        return [dict(r) for r in rows]


async def get_board_by_slug(slug: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM boards WHERE slug = $1", slug)
        return dict(row) if row else None


# -- threads -----------------------------------------------------------------

async def list_threads_on_board(board_id: int, limit: int = 10, offset: int = 0) -> list[dict]:
    """Bump-ordered thread list with the OP post + image joined in."""
    pool = get_pool()
    sql = """
        SELECT t.*,
               p.id   AS op_post_id,
               p.author_name AS op_name,
               p.body AS op_body,
               p.image_id AS op_image_id,
               img.filename  AS op_image,
               img.thumb_path AS op_thumb,
               img.original_name AS op_image_name,
               img.width AS op_image_w,
               img.height AS op_image_h
          FROM threads t
          LEFT JOIN posts p  ON p.id = (
              SELECT id FROM posts WHERE thread_id = t.id AND is_op ORDER BY id LIMIT 1
          )
          LEFT JOIN images img ON img.id = p.image_id
         WHERE t.board_id = $1
         ORDER BY t.is_sticky DESC, t.bumped_at DESC
         LIMIT $2 OFFSET $3
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, board_id, limit, offset)
        return [dict(r) for r in rows]


async def count_threads_on_board(board_id: int) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT count(*) FROM threads WHERE board_id = $1", board_id)


async def get_thread(thread_id: int) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.*, b.slug AS board_slug, b.name AS board_name
              FROM threads t
              JOIN boards b ON b.id = t.board_id
             WHERE t.id = $1
            """,
            thread_id,
        )
        return dict(row) if row else None


async def create_thread(board_id: int, subject: str) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO threads (board_id, subject) VALUES ($1, $2) RETURNING *",
            board_id,
            subject,
        )
        return dict(row)


async def bump_thread(thread_id: int) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("SELECT bump_thread($1)", thread_id)


# -- posts -------------------------------------------------------------------

async def create_post(
    thread_id: int,
    *,
    is_op: bool,
    author_name: str,
    body: str,
    image_id: int | None,
) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO posts (thread_id, is_op, author_name, body, image_id)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                thread_id,
                is_op,
                author_name,
                body,
                image_id,
            )
            await conn.execute(
                "UPDATE threads SET post_count = post_count + 1 WHERE id = $1",
                thread_id,
            )
            return dict(row)


async def list_posts_in_thread(thread_id: int) -> list[dict]:
    pool = get_pool()
    sql = """
        SELECT p.*, img.filename AS image, img.thumb_path AS thumb,
               img.original_name AS image_name, img.width AS image_w,
               img.height AS image_h, img.size_bytes AS image_size
          FROM posts p
          LEFT JOIN images img ON img.id = p.image_id
         WHERE p.thread_id = $1
         ORDER BY p.id ASC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, thread_id)
        return [dict(r) for r in rows]


# -- images ------------------------------------------------------------------

async def insert_image(cols: dict) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO images
                (filename, original_name, mime, size_bytes, width, height, thumb_path)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            RETURNING id
            """,
            cols["filename"],
            cols["original_name"],
            cols["mime"],
            cols["size_bytes"],
            cols["width"],
            cols["height"],
            cols["thumb_path"],
        )


# -- log ---------------------------------------------------------------------

async def log_event(event: str, **fields: Any) -> None:
    """Best-effort audit log. Never raises."""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO post_log (event, thread_id, post_id, board_slug, remote_addr, detail)
                VALUES ($1,$2,$3,$4,$5,$6)
                """,
                event,
                fields.get("thread_id"),
                fields.get("post_id"),
                fields.get("board_slug"),
                fields.get("remote_addr"),
                fields.get("detail"),
            )
    except Exception:
        pass


# -- backlinks (computed on read) -------------------------------------------

async def find_quoted_post_ids(thread_id: int, ids: list[int]) -> dict[int, list[int]]:
    """For a set of post ids, return which posts in the thread quote them.
    Returns {quoted_post_id: [quoting_post_id, ...]}.
    """
    if not ids:
        return {}
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, body FROM posts
             WHERE thread_id = $1 AND id = ANY($2::int[])
            """,
            thread_id,
            ids,
        )
    result: dict[int, list[int]] = {pid: [] for pid in ids}
    import re

    qre = re.compile(r">>(\d+)")
    for r in rows:
        for m in qre.finditer(r["body"]):
            target = int(m.group(1))
            if target in result:
                result[target].append(r["id"])
    return result
