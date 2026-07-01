"""Thread-scoped routes: view thread, create thread, reply."""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse

from app import repositories as repo
from app.config import settings
from app.templates import templates
from app.util import ImageError, parse_quotes, save_upload

router = APIRouter(prefix="/thread")

MAX_BODY = 2000
MAX_SUBJECT = 100


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/{thread_id}")
async def view_thread(request: Request, thread_id: int):
    thread = await repo.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="No such thread")

    if thread["is_locked"]:
        # still show, just no reply form
        pass

    posts = await repo.list_posts_in_thread(thread_id)

    # Render bodies + collect all quoted ids for backlink resolution
    all_quoted: set[int] = set()
    for p in posts:
        html, quoted = parse_quotes(p["body"])
        p["body_html"] = html
        all_quoted.update(quoted)

    backlinks = await repo.find_quoted_post_ids(thread_id, sorted(all_quoted))
    for p in posts:
        p["backlinks"] = backlinks.get(p["id"], [])

    return templates.TemplateResponse(
        request,
        "thread.html",
        {
            "thread": thread,
            "posts": posts,
            "site_name": settings.site_name,
        },
    )


@router.post("/new")
async def create_thread(
    request: Request,
    slug: str = Form(...),
    subject: str = Form(""),
    name: str = Form(""),
    body: str = Form(""),
    image: UploadFile | None = None,
):
    board = await repo.get_board_by_slug(slug)
    if not board:
        raise HTTPException(status_code=404, detail="No such board")

    body = body.strip()
    subject = subject.strip()[:MAX_SUBJECT]
    name = (name.strip() or "Anonymous")[:50]
    if not body and not image:
        raise HTTPException(status_code=400, detail="Need text or an image to post.")

    image_id = None
    if image and image.filename:
        try:
            cols = await save_upload(image)
            image_id = await repo.insert_image(cols)
        except ImageError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    thread = await repo.create_thread(board["id"], subject)
    post = await repo.create_post(
        thread["id"], is_op=True, author_name=name, body=body, image_id=image_id
    )
    await repo.bump_thread(thread["id"])
    await repo.log_event(
        "thread_create",
        thread_id=thread["id"],
        post_id=post["id"],
        board_slug=slug,
        remote_addr=_client_ip(request),
    )
    return RedirectResponse(url=f"/thread/{thread['id']}", status_code=303)


@router.post("/{thread_id}/reply")
async def reply_thread(
    request: Request,
    thread_id: int,
    name: str = Form(""),
    body: str = Form(""),
    image: UploadFile | None = None,
):
    thread = await repo.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="No such thread")
    if thread["is_locked"]:
        raise HTTPException(status_code=403, detail="Thread is locked.")

    body = body.strip()
    name = (name.strip() or "Anonymous")[:50]
    if not body and not image:
        raise HTTPException(status_code=400, detail="Need text or an image to post.")
    if len(body) > MAX_BODY:
        raise HTTPException(status_code=400, detail="Body too long.")

    image_id = None
    if image and image.filename:
        try:
            cols = await save_upload(image)
            image_id = await repo.insert_image(cols)
        except ImageError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    post = await repo.create_post(
        thread_id, is_op=False, author_name=name, body=body, image_id=image_id
    )
    await repo.bump_thread(thread_id)
    await repo.log_event(
        "reply",
        thread_id=thread_id,
        post_id=post["id"],
        board_slug=thread["board_slug"],
        remote_addr=_client_ip(request),
    )
    return RedirectResponse(url=f"/thread/{thread_id}#p{post['id']}", status_code=303)
