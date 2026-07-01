"""FastAPI app: server-rendered image board."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from app import repositories as repo
from app.config import settings
from app.db import close_pool, init_pool
from app.util import fmt_time, parse_quotes

from app.routers import boards, threads


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title=settings.site_name, lifespan=lifespan, debug=settings.debug)

templates = Jinja2Templates(directory=str(settings.templates_dir))
templates.env.filters["fmt_time"] = fmt_time

# Static + uploads
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
# Serve uploaded originals at /uploads/...
app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.upload_path)),
    name="uploads",
)


@app.middleware("http")
async def add_ctx(request: Request, call_next):
    request.state.site_name = settings.site_name
    return await call_next(request)


app.include_router(boards.router)
app.include_router(threads.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    boards = await repo.list_boards()
    return templates.TemplateResponse(
        request, "index.html", {"boards": boards, "site_name": settings.site_name}
    )


@app.get("/healthz")
async def healthz():
    return {"ok": True}
