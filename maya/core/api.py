"""
Public API facade for the external web service used by the application.

Application code should import this module rather than version-specific API
modules. Version-specific behavior belongs in focused adapters/helpers and is
selected at runtime from the configured API profile.
"""

from starlette.requests import Request
from starlette.exceptions import HTTPException
from maya.core.api_error import (
    raise_openaws_exception,
)
from maya.core.api_auth import get_auth_adapter
from maya.core.api_request import get_auth_headers
from maya.core.api_user import get_user_adapter
from maya.core import api_client
from maya.core import user
from maya.core.dynamic_settings import settings
from maya.core import query
from maya.core.logging import get_log
from maya.core.proxy_cache import proxy_cache_get, proxy_cache_set, proxy_record_cache_key
from urllib.parse import quote
import typing
from time import time
import json

log = get_log()


base_url = str(settings["api_base_url"])


def get_time_used(request: Request) -> typing.Any:
    """
    Get some statistics about the time spend on the request.\n
    This meassures time spend in a single request. Excluded is docorators to the endpoints.
    """
    time_begin = request.state.time_begin
    time_end = time()

    total_time_request = time_end - time_begin
    time_table = {
        "api_calls": api_client.REQUEST_TIME_USED,
        "total_time_request": total_time_request,
    }

    return time_table


async def auth_login_post(request: Request):
    """
    POST an email and password to the api in order to login
    """
    return await get_auth_adapter().login(request)


async def auth_register_post(request: Request):
    """
    POST an email and password to the api in order to register a new user
    """
    return await get_auth_adapter().register(request)


async def auth_verify_post(request: Request):
    """
    POST a token to the api in order to verify an email
    """
    await get_auth_adapter().verify(request)


def auth_logout(request: Request) -> None:
    """
    Clear authentication state for the active API profile.
    """
    get_auth_adapter().logout(request)


async def users_me_get(request: Request) -> dict:
    """
    GET the current user from the api. If already found in the request state
    then return the user dict without calling the API. If not then call the API
    and store the user in the request state.
    """
    return await get_user_adapter().me(request)


def update_request_state_me(request: Request, me: dict) -> dict:
    """
    Update the request state with the current user.
    """
    request.state.me = me
    return me


async def users_data_post(request: Request, id: str, data: dict):
    """
    POST user data to the api in order to update the user
    """

    async with api_client.get_async_client() as client:
        url = base_url + f"/users/{id}/data"
        headers = get_auth_headers(request, {"Content-Type": "application/json", "Accept": "application/json"})
        response = await client.post(url, json=data, headers=headers)

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)

        return response.json()


async def users_get(request: Request, query_str: str) -> dict:
    """
    GET all users from the api:
    """

    headers = get_auth_headers(request, {"Accept": "application/json"})

    url = f"{base_url}/users/?{query_str}"
    async with api_client.get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)

        return response.json()


async def users_permissions(request: Request) -> dict:
    """
    GET all permissions available from the api
    """
    headers = get_auth_headers(request, {"Accept": "application/json"})
    url = base_url + "/users/permissions"

    async with api_client.get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)

        return response.json()


async def user_get(request: Request) -> dict:
    """
    GET single user from the api by uuid
    """

    uuid = request.path_params["uuid"]
    return await user_get_by_uuid(request, uuid)


async def user_get_by_uuid(request: Request, uuid: str) -> dict:
    """
    GET single user from the api by uuid
    """

    headers = get_auth_headers(request, {"Accept": "application/json"})
    url = base_url + "/users/" + uuid

    async with api_client.get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)

        return response.json()


async def user_permissions_subset(request: Request):
    """ "
    Only a subset of permissions are editable. This function returns the editable permissions as a list.\n
     [{'name': 'read', 'grant_id': 7, 'entity_id': None}, {'name': 'hard_delete', 'grant_id': 9, 'entity_id': None}]
    """
    permissions = await users_permissions(request)
    editable_permissions: list = ["guest", "user", "researcher", "admin", "employee", "root"]
    used_permissions = [p for p in permissions if p["name"] in editable_permissions]
    used_permissions = sorted(used_permissions, key=lambda x: x["grant_id"], reverse=False)
    return used_permissions


async def users_patch_permissions(request: Request) -> typing.Any:
    """
    PATCH a user from the api
    """
    used_permissions = await user_permissions_subset(request)
    data = await request.form()

    uuid = request.path_params["uuid"]
    grant_id = data.get("grant_id", "0")

    # assert grant_id is a string. To satisfy mypy
    assert isinstance(grant_id, str)

    user_permission = [p for p in used_permissions if p["grant_id"] == int(grant_id)]
    headers = get_auth_headers(request, {"Content-Type": "application/json", "Accept": "application/json"})
    url = base_url + "/users/" + uuid + "/permissions"

    async with api_client.get_async_client() as client:
        response = await client.patch(
            url=url,
            follow_redirects=True,
            headers=headers,
            json=user_permission,
        )

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def users_delete(request: Request) -> typing.Any:
    """
    DELETE a user from the api
    """
    uuid = request.path_params["uuid"]

    async with api_client.get_async_client() as client:
        url = base_url + "/users/" + uuid
        headers = get_auth_headers(request, {"Accept": "application/json"})
        response = await client.delete(url, headers=headers)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def auth_forgot_password(request: Request) -> None:
    """
    POST an email to the api in order to reset the password
    """
    await get_auth_adapter().forgot_password(request)


async def auth_reset_password_post(request: Request) -> None:
    """
    POST a new password to the api in order to reset the password
    """
    await get_auth_adapter().reset_password(request)


async def auth_request_verify_post(request: Request) -> None:
    """
    Sends an email with a token to the user. Used to verify email.
    """
    await get_auth_adapter().request_verify(request)


async def is_logged_in(request: Request) -> bool:
    """
    Check if the current user is logged in.
    """
    try:
        await users_me_get(request)
        return True

    except Exception:
        return False


async def me_get(request: Request) -> dict:
    """
    GET the user data if logged in. Or except and return an empty user dict.\n
    This is used when we need to know if a user is logged in or not - wihtout\n
    raising an exception
    """
    try:
        me: dict = await users_me_get(request)
        return me

    except Exception:
        return {}


async def me_permissions(request: Request) -> list[str]:
    """
    GET a list of permissions that the current user has.\n
    ['root', 'admin', 'employee', 'user', 'guest'] and\n
    ['soft_delete', 'researcher', 'hard_delete', 'read', 'update', 'create', 'restore', 'scoped_read',]
    """
    try:
        me = await users_me_get(request)
        return user.permissions_from_me(me)
    except Exception:
        return []


async def me_verified(request: Request) -> bool:
    try:
        me = await users_me_get(request)
        verified = me["is_verified"]
        if verified:
            return True
    except Exception:
        pass
    return False


async def has_permission(request: Request, permission: str) -> bool:
    """
    Check if the current user has a specific permission.
    """
    user_permissions_list = await me_permissions(request)
    return permission in user_permissions_list


async def proxies_record_get_by_id(request: Request, record_id: str) -> typing.Any:
    """
    GET a record from the api if not logged in
    """

    logged_in = await is_logged_in(request)
    cache_key = proxy_record_cache_key(record_id)
    if not logged_in:
        cached_record = await proxy_cache_get(cache_key)
        if cached_record is not None:
            return cached_record

    async with api_client.get_async_client() as client:
        url = base_url + "/proxy/records/" + record_id
        headers = {"Accept": "application/json"}
        response = await client.get(url, headers=headers)

        if response.is_success:
            record = response.json()
            if not logged_in:
                await proxy_cache_set(cache_key, record)
            return record
        else:

            if response.status_code == 404:
                raise HTTPException(404)

            response.raise_for_status()


def _check_query_params(query_params_before_search: list) -> list:
    # get size and start from query_params_before_search, e.g.  [("size", "100"), ("start", "1000")]
    # it is only possible make search results that takes up 10000 records.
    # So if start + size exceeds 10000 then minimize size to 10000 - start

    size = [value for key, value in query_params_before_search if key == "size"]
    start = [value for key, value in query_params_before_search if key == "start"]

    max_size = None
    if size and start:
        size_val = size[0]
        start_val = start[0]

        if int(size_val) + int(start_val) > 10000:
            max_size = 10000 - int(start_val)

    if max_size:
        query_params_before_search = [(key, value) for key, value in query_params_before_search if key != "size"]
        query_params_before_search.append(("size", str(max_size)))

    return query_params_before_search


async def proxies_records(request: Request, query_params_before_search: typing.Optional[list] = None) -> typing.Any:
    """
    GET search results from the api

    """
    query_params_before_search = query_params_before_search or []
    query_params_before_search = _check_query_params(query_params_before_search)

    query_str = query.get_str_from_list(query_params_before_search)
    query_str = quote(query_str)

    async with api_client.get_async_client() as client:
        url = base_url + "/proxy/records?params=" + query_str
        response = await client.get(url)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def proxies_get_resource(request, type: str, id: str) -> typing.Any:
    """
    GET a resource from the api
    """
    async with api_client.get_async_client() as client:
        url = base_url + f"/proxy/{type}/{id}"
        response = await client.get(url)

        if response.is_success:
            json = response.json()
            return json

        else:

            if response.status_code == 404:
                raise HTTPException(404)

            response.raise_for_status()


async def proxies_get_relations(request: Request, type: str, id: str) -> typing.Any:
    """
    GET relations from the api
    """

    async with api_client.get_async_client() as client:
        url = base_url + f"/proxy/{type}/{id}/relations"
        response = await client.get(url)
        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def proxies_post_relations(request: Request):
    """
    POST a new relation
    """

    form_data = await request.form()

    async with api_client.get_async_client() as client:
        url = base_url + "/proxy/relations"
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        headers = get_auth_headers(request, headers)

        response = await client.post(url, data=form_data, headers=headers)
        if response.is_success:
            return response.json()
        else:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)


async def proxies_delete_relations(request: Request):
    """
    DELETE a relation
    """
    rel_id = request.path_params.get("rel_id", "")

    async with api_client.get_async_client() as client:
        url = base_url + "/proxy/relations/" + rel_id

        headers = get_auth_headers(request, {"Accept": "application/json"})
        response = await client.delete(url, headers=headers)
        if response.is_success:
            return response.json()
        else:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)


async def proxies_records_from_list(request, query_params) -> typing.Any:
    """
    GET search results from the api
    """
    query_str = query.get_str_from_list(query_params)
    query_str = quote(query_str)

    async with api_client.get_async_client() as client:
        url = base_url + "/proxy/records?params=" + query_str
        response = await client.get(url)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def proxies_auto_complete(request: Request, query_params: list = []) -> typing.Any:
    """
    Fetch auto complete data from the api\n
    Test data is used for now
    """

    q = request.query_params["q"]
    query_params.append(("t", q))

    query_str = query.get_str_from_list(query_params)
    auto_complete_url = f"https://aarhusiana.appspot.com/autocomplete_v3?{query_str}"

    async with api_client.get_async_client() as client:
        response = await client.get(auto_complete_url)
        if response.is_success:
            return response.json()["result"]
        else:
            response.raise_for_status()


async def proxies_resolve(request: Request, ids=[]) -> typing.Any:
    """
    Resolve directly from a proxy endpoint\n
    This means only getting some record data, but for multiple records
    """

    # zfill to 9 digits
    ids = [str(i).zfill(9) for i in ids]

    # ids needs to be a list dumped to json
    ids = json.dumps(ids)

    url = "https://openaws.appspot.com/resolve_records_v2"
    data = {"view": "record", "oasid": ids}

    async with api_client.get_async_client() as client:
        response = await client.post(url, data=data)

        if response.is_success:
            result_json = response.json()
            if "result" not in result_json:
                return []

            result = result_json["result"]

            # The result is not sorted by the order of the initial given ids
            # Sort the result by the order of the initial given ids
            # This does not fail if the id is not found in the result
            result = sorted(result, key=lambda x: ids.index(x["id"]))
            return result
        else:
            response.raise_for_status()


async def proxies_view_ids(request: Request) -> typing.Any:
    """
    Endpoint for getting ids from the api
    E.g. http://localhost:5555/search?content_types=100&view=ids&size=1000
    Given is also a cursor:
    http://localhost:5555/search?cursor=Vdpe3o4YQW9KK3pNeERLVEF3TURBd05URTFOZz098gc&view=ids
    Output is JSON with the ids:
    {"result":["000110308","000249018"],"next_cursor":"VVeIkIMYQW9KMXR1TXRLVEF3TURJME9UQXhPQT09Cg","status_code":0}


    """
    items = request.query_params.multi_items()
    return await proxies_view_ids_from_list(items)


async def proxies_view_ids_from_list(items: list) -> typing.Any:
    """
    Get all ids from the api
    """
    query_str = ""
    for key, value in items:
        query_str += f"{key}={value}&"

    query_str = quote(query_str)

    async with api_client.get_async_client() as client:
        url = base_url + "/proxy/records?params=" + query_str
        response = await client.get(url)

        if response.is_success:
            records = response.json()
            records["status_code"] = 0
            return records
        else:
            response.raise_for_status()


async def mail_post(data: dict) -> typing.Any:
    """
    POST /v1/operations/mail
    """

    if settings.get("send_mail_disabled"):
        log.info("send_mail_disabled is set to True. Mail was NOT sent.")
        return

    async with api_client.get_async_client() as client:
        url = base_url + "/operations/mail"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = await client.post(url, json=data, headers=headers)

        if response.is_success:
            return response.json()
        else:

            # TODO: Check for error message in response
            log.error(response.json())
            response.raise_for_status()
