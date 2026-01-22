"""
Setup pages endpoints
These endpoints are defined in the settings.
"""

from starlette.requests import Request
from starlette.exceptions import HTTPException
from maya.core.templates import templates
from maya.core.context import get_context
from maya.core.dynamic_settings import settings
from maya.settings_types import PageSettings


async def _get_page(request: Request) -> PageSettings | None:
    pages: list[PageSettings] = settings["pages"]
    page = next((item for item in pages if item["url"] == request.url.path), None)
    return page


async def custom_page(request: Request):
    page: PageSettings | None = await _get_page(request)

    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")

    template = page["template"]

    context_values = {"title": page["title"]}
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, template, context)
