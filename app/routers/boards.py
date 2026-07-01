"""Board-scoped routes: board index, catalog."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import repositories as repo
from app.config import settings
from app.util import parse_quotes

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.templates_dir))

THREADS_PER_PAGE = 10


@router.get("/{slug}/", response_class=HTMLResponse)
async def board_index(request: Request, slug: str, page: int = 1):
    board = await repo.get_board_by_slug(slug)
    if not board:
        raise HTTPException(status_code=404, detail="No such board")

    page = max(page, 1)
    offset = (page - 1) * THREADS_PER_PAGE
    threads = await repo.list_threads_on_board(board["id"], THREADS_PER_PAGE, offset)
    total = await repo.count_threads_on_board(board["id"])

    # Render OP body quotes for display
    for t in threads:
        body_html, _ = parse_quotes(t.get("op_body") or "")
        t["op_body_html"] = body_html

    pages = max(1, (total + THREADS_PER_PAGE - 1) // THREADS_PER_PAGE)
    return templates.TemplateResponse(
        request,
        "board.html",
        {
            "board": board,
            "threads": threads,
            "page": page,
            "pages": pages,
            "site_name": settings.site_name,
        },
    )


@router.get("/{slug}/catalog", response_class=HTMLResponse)
async def board_catalog(request: Request, slug: str):
    board = await repo.get_board_by_slug(slug)
    if not board:
        raise HTTPException(status_code=404, detail="No such board")

    threads = await repo.list_threads_on_board(board["id"], limit=100, offset=0)
    for t in threads:
        body_html, _ = parse_quotes(t.get("op_body") or "")
        t["op_body_html"] = body_html

    return templates.TemplateResponse(
        request,
        "catalog.html",
        {"board": board, "threads": threads, "site_name": settings.site_name},
    )
