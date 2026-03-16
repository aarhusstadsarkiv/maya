"""
Proxy for records endpoints
"""

from starlette.requests import Request
from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse
from maya.core.templates import templates
from maya.core.context import get_context
from maya.core.logging import get_log
from maya.core import api
from maya.core import cookie
from maya.core.dataclasses import RecordPagination
import asyncio
import json
import typing
import copy
from maya.endpoints.endpoints_utils import get_record_data

log = get_log()


def _get_search_query_params(query_params: list) -> list:
    """Use the search query params as a stable cache key and fetch template."""
    return [tuple(item) for item in query_params if item[0] != "start"]


def _get_search_page_size(query_params: list) -> int:
    for key, value in query_params:
        if key == "size":
            try:
                return max(int(value), 1)
            except (TypeError, ValueError):
                break
    return 20


def _get_search_page_cache(request: Request, query_params: list) -> typing.Optional[dict]:
    """
    Get the internal ephemeral cache for the active search page.
    """
    try:
        cache = request.session.get("record_navigation_cache")
        assert isinstance(cache, dict)

        cached_query_params = [tuple(item) for item in cache["query_params"]]
        if cached_query_params != query_params:
            return None

        start = int(cache["start"])
        size = int(cache["size"])
        total = int(cache["total"])
        record_ids = [int(record_id) for record_id in cache["record_ids"]]

        return {
            "query_params": cached_query_params,
            "start": start,
            "size": size,
            "total": total,
            "record_ids": record_ids,
        }
    except (AssertionError, KeyError, TypeError, ValueError):
        return None


def _set_search_page_cache(request: Request, cache: dict) -> None:
    """Persist the internal ephemeral record navigation cache in the session."""
    request.session["record_navigation_cache"] = {
        "query_params": [list(item) for item in cache["query_params"]],
        "start": cache["start"],
        "size": cache["size"],
        "total": cache["total"],
        "record_ids": cache["record_ids"],
    }


async def _get_search_page_for_position(request: Request, query_params: list, total: int, position: int) -> typing.Optional[dict]:
    """
    Get the cached search page that contains the absolute search position.
    Fetch a fresh page only when navigation crosses the cached page boundaries.
    """
    size = _get_search_page_size(query_params)
    expected_start = ((position - 1) // size) * size

    cache = _get_search_page_cache(request, query_params)
    if cache and cache["start"] == expected_start and cache["size"] == size:
        return cache

    page_query_params = query_params.copy()
    page_query_params.append(("start", str(expected_start)))
    search_result = await api.proxies_records(request, page_query_params)

    try:
        cache = {
            "query_params": query_params,
            "start": int(search_result.get("start", expected_start)),
            "size": int(search_result.get("size", size)),
            "total": int(search_result.get("total", total)),
            "record_ids": [int(record["id"]) for record in search_result.get("result", []) if record.get("id")],
        }
    except (TypeError, ValueError):
        return None

    _set_search_page_cache(request, cache)
    return cache


async def _get_record_id_for_position(
    request: Request, query_params: list, total: int, position: int, cache: typing.Optional[dict] = None
) -> int:
    if position < 1 or position > total:
        return 0

    if cache:
        index = position - cache["start"] - 1
        if 0 <= index < len(cache["record_ids"]):
            return cache["record_ids"][index]

    cache = await _get_search_page_for_position(request, query_params, total, position)
    if not cache:
        return 0

    index = position - cache["start"] - 1
    if index < 0 or index >= len(cache["record_ids"]):
        return 0

    return cache["record_ids"][index]


async def _get_record_pagination(request: Request) -> typing.Optional[RecordPagination]:
    """
    Get the record pagination object or return None if not present
    """

    # 'search' as a 'get' param indicates that we came from a search.
    # It is used as the current page number in the pagination
    current_page = request.query_params.get("search", 0)

    # ensure that the current_page is an integer
    try:
        current_page = int(current_page)
    except ValueError:
        current_page = 0

    if not current_page:
        return None

    # Get the search cookie
    # If not present then the prev and next buttons should not be shown
    search_cookie = cookie.get_search_cookie(request)
    if not search_cookie.total:
        return None

    query_params = _get_search_query_params(search_cookie.query_params.copy())

    # Calculate if there is a next and previous page
    has_next = current_page < search_cookie.total
    has_prev = current_page > 1

    # Calculate the next and previous page numbers
    next_page = current_page + 1 if has_next else 0
    prev_page = current_page - 1 if has_prev else 0

    # Create a record pagination dict
    record_pagination: dict = {}
    record_pagination["search_query_str"] = search_cookie.search_query_str
    record_pagination["total"] = search_cookie.total
    record_pagination["next_page"] = next_page
    record_pagination["prev_page"] = prev_page

    # Get the next and previous record
    try:
        current_cache = await _get_search_page_for_position(request, query_params, search_cookie.total, current_page)
        next_record = await _get_record_id_for_position(request, query_params, search_cookie.total, next_page, current_cache)
        prev_record = await _get_record_id_for_position(request, query_params, search_cookie.total, prev_page, current_cache)
    except IndexError:
        return None

    # Add the next and previous record to the record pagination dict
    record_pagination["next_record"] = next_record
    record_pagination["prev_record"] = prev_record
    record_pagination["current_page"] = current_page

    # Return the record pagination object
    record_pagination_obj = RecordPagination(**record_pagination)
    return record_pagination_obj


async def records_get(request: Request):
    """
    Display a single record
    """

    record_id = request.path_params["record_id"]
    if not record_id.isdigit():
        raise HTTPException(404)

    record_pagination, record = await asyncio.gather(_get_record_pagination(request), api.proxies_record_get_by_id(record_id))
    record, meta_data, record_and_types = await get_record_data(request, record)

    context_variables = {
        "title": meta_data["title"],
        "meta_title": meta_data["meta_title"],
        "meta_description": meta_data["meta_description"],
        "meta_data": meta_data,
        "record_and_types": record_and_types,
        "record_pagination": record_pagination,
    }

    context = await get_context(request, context_variables, "record")
    return templates.TemplateResponse(request, "records/record.html", context)


async def records_get_misc(request: Request):
    """
    Miscellaneous presentations of the record data.
    Mostly JSON for debugging.
    Also some simple HTML rendering.
    """
    try:

        record_id = request.path_params["record_id"]
        type = request.path_params["type"]

        record = await api.proxies_record_get_by_id(record_id)
        record_original = copy.deepcopy(record)

        record, meta_data, record_and_types = await get_record_data(request, record)

        if type == "record_original":
            record_original_json = json.dumps(record_original, indent=4, ensure_ascii=False)
            return PlainTextResponse(record_original_json)

        elif type == "record":
            record_json = json.dumps(record, indent=4, ensure_ascii=False)
            return PlainTextResponse(record_json)

        elif type == "meta_data":
            meta_data_json = json.dumps(meta_data, indent=4, ensure_ascii=False)
            return PlainTextResponse(meta_data_json)

        elif type == "record_and_types":
            record_and_types_json = json.dumps(record_and_types, indent=4, ensure_ascii=False)
            return PlainTextResponse(record_and_types_json)

        else:
            raise HTTPException(404, detail="type not found", headers=None)

    except Exception as e:
        log.exception("Error in get_json")
        raise HTTPException(500, detail=str(e), headers=None)
