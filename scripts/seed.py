"""Seed default boards from SEED_BOARDS env var (comma-separated slugs)."""
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

# slug -> (display name, description)
# Descriptions are in Bangla (Bengali) and English mixed for accessibility.
DEFAULTS = {
    "random":    ("Random",     "Fao pachal thread."),
    "tech": ("Tech",           "Pojukti alap"),
    "cartoon":    ("Anime & Manga",  "katun"),
    "gaan":   ("Music",          "Gaan"),
    "golpo":  ("Literature",     "Leha pora "),
    "biggan":  ("Science",        "Big-GAYAN alap"),
    "rajniti":   ("Rajniti",         "Folitics er alap"),
    "games":    ("Video Games",    "Gamisssss"),
    "antor-jatik":  ("International"   "Bidesher alap"),
    "sundoori":  ("Sundoori"   "Sundor Cute-Cute meye "),
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
                ON CONFLICT (slug) DO UPDATE
                SET name        = EXCLUDED.name,
                    description = EXCLUDED.description
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
