# banchan

A small 4chan-style image/text board. FastAPI + Postgres + server-rendered Jinja2 templates.

## What it does (MVP)

- Multiple boards by slug (`/b/`, `/g/`, ...)
- Create a thread (OP) with optional subject + optional image
- Reply to a thread with optional image
- Bump-ordered thread index, paginated
- Catalog grid view per board
- `>>123` quote parsing with clickable links + backlinks ("Replies: >>N")
- Greentext (`>like this`)
- Image upload with auto-generated thumbnails (Pillow)
- Timestamps on every post; `post_log` table for audit events (create/reply)

## Stack

- **Backend:** FastAPI (async), `asyncpg` (raw SQL, no ORM)
- **DB:** Postgres 16
- **Frontend:** Jinja2 templates + a single CSS file + a sprinkle of vanilla JS (none yet)
- **Images:** local filesystem under `uploads/` (originals + thumbs)

## Run with Docker (easiest)

```bash
cp .env.example .env
docker compose up --build
```

Then open <http://localhost:8000>. On startup the app applies `sql/schema.sql`
and seeds the boards from `SEED_BOARDS` (default `b,g,tech`).

## Run locally (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# start postgres (or use docker compose up db)
docker compose up -d db

# apply schema + seed
python scripts/init_db.py
python scripts/seed.py

# run the app
uvicorn app.main:app --reload
```

## Endpoints

| Method | Path                       | Purpose                       |
|--------|----------------------------|-------------------------------|
| GET    | `/`                        | Board list                    |
| GET    | `/{slug}/`                 | Board thread index (paginated)|
| GET    | `/{slug}/catalog`          | Catalog grid                  |
| GET    | `/thread/{id}`             | Thread + replies              |
| POST   | `/thread/new`              | Create thread (multipart)     |
| POST   | `/thread/{id}/reply`       | Reply (multipart)             |
| GET    | `/uploads/...`             | Uploaded images               |
| GET    | `/healthz`                 | Health check                  |

## Schema overview

`boards` 1--* `threads` 1--* `posts` *--1 `images`
`post_log` is an append-only audit table of post events.

See `sql/schema.sql`.

## Not in MVP (but schema-ready)

- User accounts / tripcodes (currently anonymous + optional `Name` field)
- Moderator/janitor tiers and post deletion UI
- Auto-prune of old threads (bump logic exists; prune is a cron/trigger away)
- Search
- `tripcode` parsing (`name#secret` -> hashed trip)

## Development

```bash
ruff check .          # lint
pytest                # tests (see tests/)
```
