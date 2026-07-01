"""Shared Jinja2Templates instance with filters registered."""
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.util import fmt_time

templates = Jinja2Templates(directory=str(settings.templates_dir))
templates.env.filters["fmt_time"] = fmt_time
