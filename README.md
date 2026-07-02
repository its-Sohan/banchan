# banchan

A small 4chan-style image/text board. To talk shit and real. 

## What it does
Social media sucks, amgo ekta opensource news ar alap er platform dorkar onk. No algorithms spoon-feeding you engagement bait, no vanity clout-chasing, and absolutely zero corporate hand-holding. Just a raw, anonymous space to say what you actually think. Start threads, dump images, talk trash, share news, and argue with strangers. Unfiltered, fast, and completely free of social media brainrot.

## Rules?
THERE ARE NO RULES. 
(Well, almost none. We don't want the feds or hosters shutting us down, so use common sense):
1. **No illegal shit.** Keep the site online.
2. **No spamming or botting.** If you want to pitch crypto or sell products, do it on Twitter.
3. **Grow a spine.** People will talk trash. If you get offended easily, go back to your algorithmic feed. No crying.

## Development

Get the board running locally:

```bash
# 1. Clone & set up env
cp .env.example .env

# 2. Spin up the DB and app via Docker
docker-compose up --build
```

Or run it with a local python env:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
# Set up database, run migrations/seeding
python scripts/seed.py
uvicorn app.main:app --reload
```

