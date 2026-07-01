"""Apply sql/schema.sql to the configured database. Idempotent-ish (uses IF NOT EXISTS)."""
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings


async def main() -> None:
    schema = (settings.project_root / "sql" / "schema.sql").read_text()
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(schema)
        print("Schema applied OK.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
