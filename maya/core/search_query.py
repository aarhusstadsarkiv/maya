"""Prepare search parameters consistently for the API and search state."""

from collections.abc import Mapping

from starlette.requests import Request

from maya.core.dynamic_settings import settings
from maya.core.hooks import get_hooks
from maya.core.hooks_spec import HooksSpec
from maya.core.search_validation import ALLOWED_SEARCH_SORTS, ALLOWED_SEARCH_VIEWS, SearchQueryError, validate_search_query
from maya.settings_query_params import settings_query_params

SearchItems = list[tuple[str, str]]
SEARCH_OPTIONS = frozenset({"size", "start", "sort", "direction", "view"})


def prepare_search_query(items: SearchItems, *, ids_view: bool = False) -> SearchItems:
    """Validate and return a new list of canonical, supported parameters.

    Normalize numeric IDs before label lookup, link building, or persistence.
    Repeated filters retain their order; equivalent values collapse, while
    conflicting singleton values are rejected. Text and cursors are untouched.
    """
    # Repair HTML-escaped parameter separators before selecting/validating keys.
    cleaned = []
    for key, value in items:
        while key.startswith("amp;"):
            key = key.removeprefix("amp;")
        cleaned.append((key, value))
    validate_search_query(cleaned, ids_view=ids_view)

    result = []
    seen: set[tuple[str, str]] = set()
    singletons: dict[str, str] = {}
    options = SEARCH_OPTIONS | ({"cursor"} if ids_view else set())
    for key, value in cleaned:
        name = key.removeprefix("-")
        spec = settings_query_params.get(name)
        if spec is None or (key.startswith("-") and not spec.get("negatable")):
            continue
        if not (spec["search_filter"] or key in options) or not value:
            continue
        if spec["type"] in {"object", "integer"}:
            value = value.lstrip("0") or "0"
        if not spec["repeatable"]:
            if key in singletons and singletons[key] != value:
                raise SearchQueryError(key, "must have only one value")
            singletons[key] = value
        pair = (key, value)
        if pair not in seen:
            result.append(pair)
            seen.add(pair)

    return result


def _without_orphan_series(items: SearchItems) -> SearchItems:
    if any(key == "collection" for key, value in items):
        return list(items)
    return [(key, value) for key, value in items if key != "series"]


def _get_size_sort_view(params: Mapping[str, str], cookies: Mapping[str, str]) -> tuple[str, str, str]:
    """Resolve preferences; bad stored cookies/configuration use safe defaults."""
    size = params.get("size", cookies.get("size", "20"))
    try:
        size_number = int(size) if size.isascii() and size.isdigit() else 20
    except ValueError:
        size_number = 20
    size = str(min(max(size_number, 1), 1000))

    sort_default = str(settings.get("search_default_sort", "date_from"))
    view_default = str(settings.get("search_default_view", "list"))
    if sort_default not in ALLOWED_SEARCH_SORTS:
        sort_default = "date_from"
    if view_default not in ALLOWED_SEARCH_VIEWS:
        view_default = "list"
    sort = params.get("sort", cookies.get("sort", sort_default))
    view = params.get("view", cookies.get("view", view_default))
    return size, sort if sort in ALLOWED_SEARCH_SORTS else sort_default, view if view in ALLOWED_SEARCH_VIEWS else view_default


def get_size_sort_view(request: Request) -> tuple[str, str, str]:
    """Public preference helper used by search and resource-page hooks."""
    return _get_size_sort_view(request.query_params, request.cookies)


def _with_preferences(items: SearchItems, cookies: Mapping[str, str]) -> SearchItems:
    values = dict(items)
    size, sort, view = _get_size_sort_view(values, cookies)
    items = [(key, value) for key, value in items if key not in {"size", "sort", "view", "direction"}]
    items.extend([("size", size), ("sort", sort), ("view", view)])
    if sort != "_score":
        items.append(("direction", values.get("direction", "asc" if sort == "date_from" else "desc")))
    return items


async def prepare_search_request(
    request: Request,
    extra_query_params: SearchItems | None = None,
    *,
    ids_view: bool = False,
    hooks: HooksSpec | None = None,
) -> SearchItems:
    """Validate input, apply site overrides/preferences, then prepare hook output.

    Site-supplied singleton parameters override URL values and cookie defaults;
    repeatable filters are appended. Validate each source before merging so an
    override cannot conceal malformed or conflicting user input.
    """
    items = prepare_search_query(request.query_params.multi_items(), ids_view=ids_view)
    extras = prepare_search_query(extra_query_params or [], ids_view=ids_view)
    overrides = {key for key, value in extras if not settings_query_params[key.removeprefix("-")]["repeatable"]}
    items = prepare_search_query([(key, value) for key, value in items if key not in overrides] + extras, ids_view=ids_view)
    if not ids_view:
        items = _with_preferences(items, request.cookies)

    hooks = hooks or get_hooks(request)
    items = await hooks.before_get_search(query_params=items)
    items = prepare_search_query(items, ids_view=ids_view)
    if not ids_view:
        # A hook may remove preferences; keep API and displayed options aligned.
        items = _with_preferences(items, request.cookies)
    return _without_orphan_series(items)


def get_api_search_query(items: SearchItems, *, ids_view: bool = False) -> SearchItems:
    """Apply API-only limits to a copy, preserving the user's search state."""
    items = _without_orphan_series(prepare_search_query(items, ids_view=ids_view))
    # Keep a one-character query in the form/cookie, but avoid the API's 400.
    items = [(key, "" if key == "q" and len(value) == 1 else value) for key, value in items]
    values = dict(items)
    if not ids_view and "size" in values and "start" in values:
        remaining = 10000 - int(values["start"])
        if int(values["size"]) > remaining:
            items = [(key, str(remaining) if key == "size" else value) for key, value in items]
    return items
