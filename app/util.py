"""Shared helpers: image handling, quote parsing, time formatting."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

from app.config import settings

ALLOWED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
THUMB_MAX = 200  # px on the longest side


class ImageError(ValueError):
    pass


async def save_upload(upload: UploadFile) -> dict:
    """Validate + persist an uploaded image and generate a thumbnail.

    Returns a dict of columns for the `images` table.
    """
    if upload.content_type not in ALLOWED_MIME:
        raise ImageError(f"File type {upload.content_type!r} not allowed.")

    data = await upload.read()
    if not data:
        raise ImageError("Empty file.")
    if len(data) > settings.max_image_bytes:
        raise ImageError(f"File too large (max {settings.max_image_bytes} bytes).")

    ext = EXT_BY_MIME[upload.content_type]
    filename = f"{uuid.uuid4().hex}{ext}"
    original_name = upload.filename or filename

    originals = settings.originals_path
    originals.mkdir(parents=True, exist_ok=True)
    (originals / filename).write_bytes(data)

    width: int | None = None
    height: int | None = None
    thumb_rel: str | None = None
    try:
        with Image.open(originals / filename) as img:
            width, height = img.size
            img.thumbnail((THUMB_MAX, THUMB_MAX))
            thumbs = settings.thumbs_path
            thumbs.mkdir(parents=True, exist_ok=True)
            thumb_name = f"{Path(filename).stem}_t.png"
            img.save(thumbs / thumb_name, format="PNG")
            thumb_rel = f"thumbs/{thumb_name}"
    except Exception as e:  # noqa: BLE001
        raise ImageError(f"Could not process image: {e}") from e

    return {
        "filename": filename,
        "original_name": original_name,
        "mime": upload.content_type,
        "size_bytes": len(data),
        "width": width,
        "height": height,
        "thumb_path": thumb_rel,
    }


# NOTE: match against the *escaped* text, where > has become &gt;,
# so we run escaping before these regexes (see parse_quotes).
QUOTE_RE = re.compile(r"&gt;&gt;(\d+)")
GREENTEXT_RE = re.compile(r"^&gt;(.+)$", re.MULTILINE)


def parse_quotes(body: str) -> tuple[str, list[int]]:
    """Replace >>123 with anchor HTML and return the rendered HTML + quoted post ids."""
    quoted: list[int] = []

    def repl(m: re.Match) -> str:
        pid = int(m.group(1))
        quoted.append(pid)
        return f'<a class="quote" href="#p{pid}">&gt;&gt;{pid}</a>'

    # Escape first (XSS-safe), then match quotes/greentext on the escaped text.
    escaped = (
        body.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    out = QUOTE_RE.sub(repl, escaped)

    # Greentext lines that start with > (but not >>, which are now <a> tags)
    out = GREENTEXT_RE.sub(lambda m: f'<span class="greentext">{m.group(0)}</span>', out)
    # Preserve newlines
    out = out.replace("\n", "<br>\n")
    return out, quoted


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")
