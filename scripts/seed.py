"""Seed default boards from SEED_BOARDS env var (comma-separated slugs)."""
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

DEFAULTS = {
    "b": ("Random", "Anything that doesn't belong elsewhere."),
    "g": ("Technology", "Programming, hardware, software."),
    "tech": ("Tech", "Tech talk."),
}


async def main() -> None:
    slugs = [s.strip() for s in settings.seed_boards.split(",") if s.strip()]
    conn = await asyncpg.connect(settings.database_url)
    try:
        for slug in slugs:
            name, desc = DEFAULTS.get(slug, (slug.capitalize(), ""))
            await conn.execute(
                """
                INSERT INTO boards (slug, name, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (slug) DO NOTHING
                """,
                slug,
                name,
                desc,
            )
        print(f"Seeded boards: {', '.join(slugs)}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
