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
    "b":    ("Random",         "যেকোনো কিছু — বিষয় নির্বিশেষে আলোচনা"),
    "g":    ("Technology",     "প্রযুক্তি — হার্ডওয়্যার, সফটওয়্যার, প্রোগ্রামিং"),
    "tech": ("Tech",           "প্রযুক্তি আলোচনা"),
    "a":    ("Anime & Manga",  "অ্যানিম ও মাঙ্গা — জাপানি কার্টুন ও কমিক"),
    "mu":   ("Music",          "সঙ্গীত — শিল্পী, অ্যালবাম, গান"),
    "lit":  ("Literature",     "সাহিত্য ও বই — কবিতা, গল্প, উপন্যাস"),
    "sci":  ("Science",        "বিজ্ঞান ও গবেষণা — পদার্থবিদ্যা, জীববিদ্যা, মহাকাশ"),
    "sp":   ("Sports",         "খেলাধুলা — ক্রিকেট, ফুটবল, অন্যান্য"),
    "v":    ("Video Games",    "ভিডিও গেমস — গেমিং, কনসোল, PC"),
    "int":  ("International",  "আন্তর্জাতিক — বিশ্ব সংবাদ ও সংস্কৃতি"),
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
