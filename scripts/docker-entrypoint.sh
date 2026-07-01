#!/bin/sh
set -e

# --- Wait for Postgres ---
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for Postgres..."
    python3 -c "
import asyncio, asyncpg, os, sys

async def wait():
    for i in range(30):
        try:
            await asyncpg.connect(os.environ['DATABASE_URL'])
            print('DB ready')
            return
        except Exception as e:
            print(f'  waiting... ({i+1}/30): {e}')
            await asyncio.sleep(1)
    print('ERROR: DB not ready after 30s')
    sys.exit(1)

asyncio.run(wait())
"
fi

# --- Apply schema + seed boards ---
python3 /app/scripts/init_db.py
python3 /app/scripts/seed.py

# --- Start uvicorn ---
PORT="${PORT:-8000}"
RELOAD=""
if [ "${DEBUG}" = "true" ]; then
    RELOAD="--reload"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" $RELOAD
