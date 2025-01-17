"""
Proxy for records endpoints
"""

from starlette.requests import Request
from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse
from stadsarkiv_client.core.templates import templates
from stadsarkiv_client.core.context import get_context
from stadsarkiv_client.core.logging import get_log
# from stadsarkiv_client.core.hooks import get_hooks
from stadsarkiv_client.core import api
from stadsarkiv_client.core import cookie
# from stadsarkiv_client.records import record_alter
# from stadsarkiv_client.records.meta_data_record import get_record_meta_data
from stadsarkiv_client.core.dataclasses import RecordPagination
import asyncio
import json
import typing
from stadsarkiv_client.endpoints.endpoints_utils import get_record_data


log = get_log()


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

    # Copy the query params and remove the size parameter
    # This is needed to generate the next and previous links
    # Only query for one record to get the next and previous record
    query_params = search_cookie.query_params.copy()
    query_params = [tuple(item) for item in query_params if item[0] != "size"]
    query_params.append(("size", "1"))

    # Calculate if there is a next and previous page
    has_next = current_page < search_cookie.total
    has_prev = current_page > 1

    # Calculate the next and previous page numbers
    next_page = current_page + 1 if has_next else 0
    prev_page = current_page - 1 if has_prev else 0

    # Create a record pagination dict
    record_pagination: dict = {}
    record_pagination["query_str_display"] = search_cookie.query_str_display
    record_pagination["total"] = search_cookie.total
    record_pagination["next_page"] = next_page
    record_pagination["prev_page"] = prev_page

    async def get_next_record() -> int:
        if next_page:
            next_query_params = query_params.copy()
            search_params = [("start", str(next_page - 1))]
            next_query_params.extend(search_params)
            records = await api.proxies_records_from_list(request, next_query_params)
            id = records["result"][0]["id"]
            return id
        else:
            return 0

    async def get_prev_record() -> int:
        if prev_page:
            prev_query_params = query_params.copy()
            search_params = [("start", str(prev_page - 1))]
            prev_query_params.extend(search_params)
            records = await api.proxies_records_from_list(request, prev_query_params)
            id = records["result"][0]["id"]
            return id
        else:
            return 0

    # Get the next and previous record
    try:
        """
        This will fail if 'list index out of range'
        This can happen if the user uses two tabs and the search result is updated in one tab.
        """
        next_record, prev_record = await asyncio.gather(get_next_record(), get_prev_record())
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

    record_id = request.path_params["record_id"]
    if not record_id.isdigit():
        raise HTTPException(404)

    permissions = await api.me_permissions(request)
    record_pagination, record = await asyncio.gather(_get_record_pagination(request), api.proxies_record_get_by_id(record_id))
    record, meta_data, record_and_types = await get_record_data(request, record, permissions)

    context_variables = {
        "is_employee": "employee" in permissions,
        "title": meta_data["title"],
        "meta_title": meta_data["meta_title"],
        "meta_description": meta_data["meta_description"],
        "meta_data": meta_data,
        "record_and_types": record_and_types,
        "record_pagination": record_pagination,
    }

    context = await get_context(request, context_variables, "record")
    return templates.TemplateResponse(request, "records/record.html", context)


async def records_get_json(request: Request):
    try:

        record_id = request.path_params["record_id"]
        type = request.path_params["type"]

        permissions = await api.me_permissions(request)
        record = await api.proxies_record_get_by_id(record_id)
        record_original = record.copy()

        record, meta_data, record_and_types = await get_record_data(request, record, permissions)

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
