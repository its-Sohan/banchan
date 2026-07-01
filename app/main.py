"""FastAPI app: server-rendered image board."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import repositories as repo
from app.config import settings
from app.db import close_pool, init_pool
from app.templates import templates

from app.routers import boards, threads


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title=settings.site_name, lifespan=lifespan, debug=settings.debug)

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
