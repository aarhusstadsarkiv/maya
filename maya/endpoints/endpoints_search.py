"""
Proxy for search records endpoints
"""

from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import JSONResponse
from maya.core.templates import templates, get_icon
from maya.core.context import get_context
from maya.core.translate import translate
from maya.core.logging import get_log
from maya.core.dynamic_settings import settings
from maya.core import api
import json
from maya.records.normalize_facets import NormalizeFacets
from maya.core import query
from maya.core.hooks import get_hooks
from maya.records import normalize_dates
from maya.settings_query_params import settings_query_params
from maya.core.object_storage import set_presigned_urls_search

log = get_log()


def get_api_acceptable_query_params() -> list:
    api_accept_query_params = []
    for key, value in settings_query_params.items():
        if value.get("search_filter"):
            api_accept_query_params.append(key)

        if value.get("negatable"):
            api_accept_query_params.append(f"-{key}")

    return api_accept_query_params


def _get_search_pagination_data(request: Request, query_str_pagination, total: int):

    result = {}

    size, _, _ = get_size_sort_view(request)
    size = int(str(size))
    result["size"] = size

    result["query_str"] = query_str_pagination

    if total > 10000:
        total = 10000

    result["total"] = total

    start_ = request.query_params.get("start", "0")
    if not start_.isdigit():
        start_ = "0"

    start = int(start_)
    result["start"] = start

    total_pages = (total // size) + (1 if total % size != 0 else 0)
    result["total_pages"] = total_pages

    current_page = (start // size) + 1
    result["current_page"] = current_page

    return result


def _get_dates(request: Request):
    """
    Get dates from request. Used in date search form
    """
    dates = {}
    dates_from = request.query_params.get("date_from", None)
    dates_to = request.query_params.get("date_to", None)

    # split dates. From format: yyyymmdd and not yyyy-mm-dd
    if dates_from:
        dates["from_year"], dates["from_month"], dates["from_day"] = dates_from[:4], dates_from[4:6], dates_from[6:]

    if dates_to:
        dates["to_year"], dates["to_month"], dates["to_day"] = dates_to[:4], dates_to[4:6], dates_to[6:]

    return dates


def get_size_sort_view(request: Request):
    """
    Get size and sort from request. If not set in request, then get from cookies.
    If not set in cookie use some default values
    """
    size = request.query_params.get("size", request.cookies.get("size", "20"))

    # only accept size between 1 and 1000
    if not size.isdigit():
        size = "20"

    if int(size) < 1:
        size = "1"

    if int(size) > 1000:
        size = "1000"

    sort_default = settings.get("search_default_sort", "date_from")
    view_default = settings.get("search_default_view", "list")

    sort = request.query_params.get("sort", request.cookies.get("sort", sort_default))
    view = request.query_params.get("view", request.cookies.get("view", view_default))

    return size, sort, view


def _get_default_query_params(request: Request):
    """
    Get default query_params for records search as list of tuples:
    size, sort, direction
    """
    size, sort, view = get_size_sort_view(request)
    add_list_items = [("size", size), ("sort", sort), ("view", view)]

    direction = None
    if sort == "date_to":
        direction = request.query_params.get("direction", "desc")

    if sort == "date_from":
        direction = request.query_params.get("direction", "asc")

    if sort == "created_at":
        direction = request.query_params.get("direction", "desc")

    if direction:
        add_list_items.append(("direction", direction))

    start = request.query_params.get("start", None)
    if start:

        if not start.isdigit():
            start = "0"

        add_list_items.append(("start", start))

    return add_list_items


def _check_series(query_params: list) -> list:
    """
    Check if a collection is set in query params.
    If not then remove series from query params
    """
    collection = None
    for key, value in query_params:
        if key == "collection":
            collection = True

    for key, value in query_params:
        if key == "series" and not collection:
            query_params.remove((key, value))

    return query_params


def _clean_amp(query_params_before_search: list) -> list:
    """
    Remove amp; from query params
    """

    for i, (key, value) in enumerate(query_params_before_search):
        query_params_before_search[i] = (key.replace("amp;", ""), value)

    query_params_before_search = [(key, value) for key, value in query_params_before_search if value]
    return query_params_before_search


def _clean_query_params(query_params: list) -> list:
    query_params = _check_series(query_params)
    query_params = _clean_amp(query_params)

    # If key equals collection then remove left padded zeros
    query_params = [(key, value.lstrip("0")) if key == "collection" else (key, value) for key, value in query_params]

    # remove duplicate query params
    seen = set()
    deduped = []
    for pair in query_params:
        if pair not in seen:
            seen.add(pair)
            deduped.append(pair)

    return deduped


def _get_facets_and_filters(request: Request, search_result: dict, query_params=[], query_str=""):
    """
    Get facets and filters from a search result
    """
    normalized_facets = NormalizeFacets(
        request=request,
        search_result=search_result,
        query_params=query_params,
        query_str=query_str,
    )

    facets = normalized_facets.get_transformed_facets()
    facets_enabled = settings["facets_enabled"]

    # only use facets that are enabled in settings left menu
    facets = {key: value for key, value in facets.items() if key in facets_enabled}

    # sort by facets_enabled order
    facets = {key: facets[key] for key in facets_enabled}

    facets_filters = normalized_facets.get_filters()

    return facets, facets_filters


def set_response_cookie(response: Response, context: dict):
    """
    Set cookies for search page
    This is a public function so it can be used in other endpoints where a search may be performed
    It is based on the context values used in the search page, e.g. size, sort and view
    """

    size = context.get("size")
    sort = context.get("sort")
    view = context.get("view")

    # assert size, sort and view are ints
    assert isinstance(size, str)
    assert isinstance(sort, str)
    assert isinstance(view, str)

    pagination_data = context.get("pagination_data", {})
    search_cookie_value = {
        # Use site specific query params set before search
        "query_str_display": context.get("query_str_display"),
        "query_params": context.get("query_params_before_search"),
        "total": pagination_data["total"],
        "q": context.get("q"),
    }

    response.set_cookie(key="search", value=json.dumps(search_cookie_value), httponly=True)
    response.set_cookie(key="size", value=size, httponly=True)
    response.set_cookie(key="sort", value=sort, httponly=True)
    response.set_cookie(key="view", value=view, httponly=True)

    return response


async def _normalize_search_result(records: dict):
    """
    Normalize date
    Get collection and content_type from facets_resolved
    These are displayed in the search result
    """
    facets_resolved = records["facets_resolved"]

    for record in records["result"]:

        if settings.get("boto3_presigned_urls", False):
            record = await set_presigned_urls_search(record)

        record = normalize_dates.split_date_strings(record)
        record = normalize_dates.normalize_dates(record)

        # Add collection as string
        if "collection_id" in record and record["collection_id"]:
            record["collection"] = facets_resolved["collection"].get(record["collection_id"]).get("display_label", None)

        if "content_types" in record:

            if not record["content_types"]:
                # Log in order to set a content-type as this is required
                log.error(f"Content types is empty for record: {record['id']}")
                continue

            content_type = record["content_types"][-1]
            record["content_type"] = facets_resolved["content_types"].get(content_type).get("display_label", None)

        record["show_image"] = False
        if record.get("thumbnail") and record.get("availability", None) == "4":
            record["show_image"] = True

    return records


async def get_search_context_values(request: Request, extra_query_params: list = []) -> dict:
    """
    Get all context values used on the search page
    extra_query_params: list of tuples that will be added to the query params before search
    """
    hooks = get_hooks(request)

    q = query.get_search(request)
    size, sort, view = get_size_sort_view(request)

    api_accept_query_params = get_api_acceptable_query_params()

    # date_to, date_from, created_at, start, direction are read from query params
    default_query_params = _get_default_query_params(request)
    default_query_params.extend(extra_query_params)

    query_params_before_search = query.get_list(
        request,
        accept_keys=api_accept_query_params,
        default_query_params=default_query_params,
    )

    query_params_before_search = _clean_query_params(query_params_before_search)

    # Alter query params before search
    # E.g. You may want to remove all collections and add a single collection before search
    query_params_before_search = await hooks.before_get_search(query_params=query_params_before_search)
    query_str_search = query.get_str_from_list(query_params_before_search)

    # Call api and get search results
    search_result = await api.proxies_records(request, query_params_before_search)
    search_result = await _normalize_search_result(search_result)

    # Alter query params after search
    # You may want to remove all curators except one after search results are obtained
    query_params_after_search = await hooks.after_get_search(query_params=query_params_before_search)
    query_str_display = query.get_str_from_list(query_params_after_search, remove_keys=["start"])

    # Get facets and filters
    facets, facets_filters = _get_facets_and_filters(
        request,
        search_result,
        query_params=query_params_after_search,
        query_str=query_str_display,
    )

    pagination_data = _get_search_pagination_data(request, query_str_display, search_result["total"])

    context_values = {
        "q": q,
        "title": translate("Search"),
        "search_result": search_result,
        "query_params_before_search": query_params_before_search,
        "query_params": query_params_after_search,
        "query_str_search": query_str_search,
        "query_str_display": query_str_display,
        "sort": sort,
        "size": size,
        "view": view,
        "facets": facets,
        "facets_filters": facets_filters,
        "dates": _get_dates(request),
        "pagination_data": pagination_data,
        "meta_tags": {
            "robots": "noindex, follow",
        },
    }

    return context_values


async def search_get(request: Request):

    items = request.query_params.multi_items()

    # check if tuple ('view', 'ids') is in items as this is a special case
    if ("view", "ids") in items:
        view_ids_json = await api.proxies_view_ids(request)
        return JSONResponse(view_ids_json)

    context_values = await get_search_context_values(request)
    context = await get_context(request, context_values=context_values)

    if context_values["view"] == "list":
        response = templates.TemplateResponse(request, "search/search.html", context)
    elif context_values["view"] == "gallery" or context_values["view"] == "grid":
        response = templates.TemplateResponse(request, "search/search_gallery.html", context)
    else:
        response = templates.TemplateResponse(request, "search/search.html", context)

    set_response_cookie(response, context)

    return response


async def search_get_json(request: Request):
    context_values = await get_search_context_values(request)
    response = JSONResponse(context_values)
    set_response_cookie(response, context_values)

    return response


def _normalize_auto_complete_results(results: list):
    """
    Collection is weird so normalize it a bit. All other domains has the same 'search_query' as 'domain path', e.g.
    /people/120169 -> search?people=120169

    But collections is different:

    /collections/7 -> /search?collection=7

    """

    for result in results:
        if result["domain"] == "collections":
            result["search_query"] = "collection"
        else:
            result["search_query"] = result["domain"]

        # Get domain and look up the label in settings_query_params
        domain = result["domain"]
        if domain in settings_query_params:
            result["domain_human"] = settings_query_params[domain]["label"]

        # Clean up sub_display if poluted with domain name
        if domain == "organisations":
            result["icon"] = get_icon("organisation", size=16)
            if result["sub_display"].startswith("Organisation, "):
                result["sub_display"] = result["sub_display"].replace("Organisation, ", "")

        elif domain == "locations":
            result["icon"] = get_icon("address", size=16)
            if result["sub_display"].startswith("Sted, "):
                result["sub_display"] = result["sub_display"].replace("Sted, ", "")
        elif domain == "people":
            result["icon"] = get_icon("person", size=16)
            if result["sub_display"].startswith("Person, "):
                result["sub_display"] = result["sub_display"].replace("Person, ", "")
        elif domain == "events":
            result["icon"] = get_icon("event", size=16)
            if result["sub_display"].startswith("Begivenhed, "):
                result["sub_display"] = result["sub_display"].replace("Begivenhed, ", "")
        elif domain == "collections":
            result["icon"] = get_icon("collection", size=16)
            result["sub_display"] = result["sub_display"].replace("Samling, ", "")
        elif domain == "collectors":
            result["icon"] = get_icon("collection", size=16)
        else:
            result["icon"] = ""

    return results


async def records_auto_complete_search(request: Request):
    """
    Auto complete for search
    """
    hooks = get_hooks(request)
    query_params: list = []
    query_params = await hooks.before_get_auto_complete(query_params=query_params)

    results = await api.proxies_auto_complete(request, query_params=query_params)
    results = _normalize_auto_complete_results(results)

    query_params = await hooks.after_get_auto_complete(query_params=query_params)

    return JSONResponse(results)


async def records_auto_complete_relations(request: Request):
    """
    Auto complete for search.
    Notice: There is no before and after hooks for this endpoint.
    """
    query_params: list = []
    query_params.append(("limit", "25"))

    result = await api.proxies_auto_complete(request, query_params=query_params)

    return JSONResponse(result)
