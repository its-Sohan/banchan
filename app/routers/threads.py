"""Thread-scoped routes: view thread, create thread, reply."""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse

from app import repositories as repo
from app.config import settings
from app.templates import templates
from app.util import ImageError, has_meaningful_body, parse_quotes, save_upload

router = APIRouter(prefix="/thread")

MAX_BODY = 2000
MAX_SUBJECT = 100


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _has_image(upload: UploadFile | None) -> bool:
    """True if a file was actually selected in the form.

    FastAPI hands us an empty UploadFile (filename="") when the form has
    a file input but no file is chosen, so we must check the filename.
    """
    return upload is not None and bool(upload.filename)


@router.get("/{thread_id}")
async def view_thread(request: Request, thread_id: int):
    thread = await repo.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="No such thread")

    posts = await repo.list_posts_in_thread(thread_id)

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

    has_image = _has_image(image)
    has_content = has_meaningful_body(body)

    if not has_content and not has_image:
        return await _render_board_with_error(
            request, board, subject, name, body,
            "Posting requires at least some text or an image.",
        )

    if len(body) > MAX_BODY:
        return await _render_board_with_error(
            request, board, subject, name, body,
            f"Body too long (max {MAX_BODY} characters).",
        )

    image_id = None
    if has_image:
        try:
            cols = await save_upload(image)  # type: ignore[arg-type]
            image_id = await repo.insert_image(cols)
        except ImageError as e:
            return await _render_board_with_error(
                request, board, subject, name, body, str(e),
            )

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

    has_image = _has_image(image)
    has_content = has_meaningful_body(body)

    if not has_content and not has_image:
        return await _render_thread_with_error(
            request, thread, name, body,
            "Reply requires at least some text or an image.",
        )

    if len(body) > MAX_BODY:
        return await _render_thread_with_error(
            request, thread, name, body,
            f"Body too long (max {MAX_BODY} characters).",
        )

    image_id = None
    if has_image:
        try:
            cols = await save_upload(image)  # type: ignore[arg-type]
            image_id = await repo.insert_image(cols)
        except ImageError as e:
            return await _render_thread_with_error(
                request, thread, name, body, str(e),
            )

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


# --- helpers ---------------------------------------------------------------

async def _render_board_with_error(
    request: Request, board: dict, subject: str, name: str, body: str, error: str
):
    """Re-render the board page with an inline error and the form's input preserved."""
    from app.config import settings as _s  # local import to avoid cycle in type hints
    threads = await repo.list_threads_on_board(board["id"], limit=10, offset=0)
    for t in threads:
        body_html, _ = parse_quotes(t.get("op_body") or "")
        t["op_body_html"] = body_html
    return templates.TemplateResponse(
        request,
        "board.html",
        {
            "board": board,
            "threads": threads,
            "page": 1,
            "pages": 1,
            "error": error,
            "form": {"name": name, "subject": subject, "body": body},
            "site_name": _s.site_name,
        },
        status_code=400,
    )


async def _render_thread_with_error(
    request: Request, thread: dict, name: str, body: str, error: str
):
    posts = await repo.list_posts_in_thread(thread["id"])
    all_quoted: set[int] = set()
    for p in posts:
        html, quoted = parse_quotes(p["body"])
        p["body_html"] = html
        all_quoted.update(quoted)
    backlinks = await repo.find_quoted_post_ids(thread["id"], sorted(all_quoted))
    for p in posts:
        p["backlinks"] = backlinks.get(p["id"], [])
    return templates.TemplateResponse(
        request,
        "thread.html",
        {
            "thread": thread,
            "posts": posts,
            "error": error,
            "form": {"name": name, "body": body},
            "site_name": settings.site_name,
        },
        status_code=400,
    )
