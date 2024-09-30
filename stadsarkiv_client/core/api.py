"""
All api calls to the webservice API is defined here.
"""

from starlette.requests import Request
from stadsarkiv_client.core.api_error import OpenAwsException, validate_passwords, validate_display_name, raise_openaws_exception
from stadsarkiv_client.core.logging import get_log
from stadsarkiv_client.core import user
from stadsarkiv_client.core.translate import translate
from stadsarkiv_client.core.dynamic_settings import settings
from stadsarkiv_client.core import query
from stadsarkiv_client.core.cache import set_cache, get_cache
from stadsarkiv_client.core.hooks import get_hooks
from urllib.parse import quote
import json
import httpx
import typing
from time import time


log = get_log()


base_url = str(settings["api_base_url"])
REQUEST_TIME_USED: dict = {}


async def _request_start_time(request):
    """
    Custom event for httpx. Add a start time to the request.
    """
    request.start_time = time()


async def _request_custom_header(request: httpx.Request):
    """
    Custom event for httpx. Add a custom header to the request.
    """
    request.headers["x-client"] = settings["client_name"]
    request.headers["x-client-domain-url"] = settings["client_url"]
    return request


async def _response_httpx_timer(response):
    """
    Custom event for httpx. Log the time spend on the request.
    """
    request = response.request

    # Calculate the elapsed time from request initiation to response reception
    elapsed_time = time() - float(request.start_time)
    request_name = str(request.method) + "_" + str(request.url.path)
    _set_time_used(request_name, elapsed_time)


def _get_async_client() -> httpx.AsyncClient:
    """
    Get an async httpx client with custom events.
    """
    return httpx.AsyncClient(
        event_hooks={"request": [_request_custom_header, _request_start_time], "response": [_response_httpx_timer]}, timeout=7
    )


def _set_time_used(name: str, elapsed: float) -> None:
    """
    Set response time as a state on the request in order to
    be able to show the time spend on each httpx request (api call).
    """
    # check if name is already in dict
    if name not in REQUEST_TIME_USED:
        REQUEST_TIME_USED[name] = [elapsed]
    else:
        REQUEST_TIME_USED[name].append(elapsed)


def get_time_used(request: Request) -> typing.Any:
    """
    Get some statistics about the time spend on the request.
    This meassures time spend in a single request. Excluded is docorators to the endpoints.
    """
    time_begin = request.state.time_begin
    time_end = time()

    total_time_request = time_end - time_begin
    time_table = {
        "api_calls": REQUEST_TIME_USED,
        "total_time_request": total_time_request,
    }

    return time_table


def _get_jwt_headers(request: Request, headers: dict = {}) -> dict:
    """
    GET headers with a jwt token. The token is stored in the session.
    """
    if "access_token" not in request.session:
        raise OpenAwsException(401, translate("You need to be logged in to view this page."))

    access_token = request.session["access_token"]
    headers["Authorization"] = f"Bearer {access_token}"
    return headers


async def auth_jwt_login_post(request: Request):
    """
    POST an email and password to the api in order to login
    """

    hooks = get_hooks(request=request)
    form = await request.form()
    username = str(form.get("email"))  # email is used as username
    password = str(form.get("password"))

    login_dict = {"username": username, "password": password}

    async with _get_async_client() as client:
        url = base_url + "/auth/jwt/login"
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}

        response = await client.post(url, data=login_dict, headers=headers)
        if response.is_success:
            json_response = response.json()
            access_token = json_response["access_token"]
            token_type = json_response["token_type"]
            user.set_user_jwt(request, access_token, token_type)
            await hooks.after_login_success(json_response)
        else:
            json_response = response.json()
            await hooks.after_login_failure(json_response)
            raise_openaws_exception(response.status_code, json_response)


async def auth_register_post(request: Request):
    """
    POST an email and password to the api in order to register a new user
    """
    await validate_display_name(request)
    await validate_passwords(request)

    form = await request.form()
    display_name = str(form.get("display_name"))
    email = str(form.get("email"))
    password = str(form.get("password"))

    async with _get_async_client() as client:
        url = base_url + "/auth/register"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        json_post = {"email": email, "password": password, "display_name": display_name}
        response = await client.post(url, json=json_post, headers=headers)

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)


async def auth_verify_post(request: Request):
    """
    POST a token to the api in order to verify an email
    """
    token = request.path_params["token"]

    async with _get_async_client() as client:
        url = base_url + "/auth/verify"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = await client.post(url, json={"token": token}, headers=headers)

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)


async def users_me_get(request: Request, allow_request_state=True) -> dict:
    """
    GET the current user from the api.
    The user is stored in the request state in order to avoid multiple api calls.
    """

    if allow_request_state:
        if hasattr(request.state, "me"):
            return request.state.me

    headers = _get_jwt_headers(request, {"Accept": "application/json"})

    url = base_url + "/users/me"

    async with _get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if response.is_success:
            request.state.me = response.json()
            return response.json()
        else:
            raise OpenAwsException(
                422,
                translate("You need to be logged in to view this page."),
            )


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

    async with _get_async_client() as client:
        url = base_url + f"/users/{id}/data"
        headers = _get_jwt_headers(request, {"Content-Type": "application/json", "Accept": "application/json"})
        response = await client.post(url, json=data, headers=headers)

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)

        return response.json()


async def users_get(request: Request) -> dict:
    """
    GET all users from the api
    """

    headers = _get_jwt_headers(request, {"Accept": "application/json"})
    url = base_url + "/users/"

    async with _get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if response.is_success:
            return response.json()
        else:
            raise OpenAwsException(
                422,
                translate("You need to be logged in to view this page."),
            )


async def users_permissions(request: Request) -> dict:
    """
    GET all permissions available from the api
    """
    headers = _get_jwt_headers(request, {"Accept": "application/json"})
    url = base_url + "/users/permissions"

    async with _get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if response.is_success:
            return response.json()
        else:
            raise OpenAwsException(
                422,
                translate("You need to be logged in to view this page."),
            )


async def user_get(request: Request) -> dict:
    """
    GET single user from the api by uuid
    """

    uuid = request.path_params["uuid"]

    headers = _get_jwt_headers(request, {"Accept": "application/json"})
    url = base_url + "/users/" + uuid

    async with _get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if response.is_success:
            return response.json()
        else:
            raise OpenAwsException(
                422,
                translate("You need to be logged in to view this page."),
            )


async def user_permissions_subset(request: Request):
    """ "
    Only a subset of permissions are editable. This function returns the editable permissions as a list.
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
    headers = _get_jwt_headers(request, {"Content-Type": "application/json", "Accept": "application/json"})
    url = base_url + "/users/" + uuid + "/permissions"

    async with _get_async_client() as client:
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


async def auth_forgot_password(request: Request) -> None:
    """
    POST an email to the api in order to reset the password
    """
    form = await request.form()
    email = str(form.get("email"))

    async with _get_async_client() as client:
        url = base_url + "/auth/forgot-password"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        response = await client.post(url, json={"email": email}, headers=headers)

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)


async def auth_reset_password_post(request: Request) -> None:
    """
    POST a new password to the api in order to reset the password
    """
    await validate_passwords(request)

    form = await request.form()
    password = str(form.get("password"))
    token = request.path_params["token"]

    async with _get_async_client() as client:
        url = base_url + "/auth/reset-password"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = await client.post(url, json={"password": password, "token": token}, headers=headers)

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)


async def auth_request_verify_post(request: Request) -> None:
    """
    Sends an email with a token to the user. Used to verify email.
    """
    me = await users_me_get(request)
    email = me["email"]

    async with _get_async_client() as client:
        url = base_url + "/auth/request-verify-token"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = await client.post(url, json={"email": email}, headers=headers)

        if not response.is_success:
            json_response = response.json()
            raise_openaws_exception(response.status_code, json_response)


async def is_logged_in(request: Request) -> bool:
    """
    Check if the current user is logged in. Return True if the user is logged in.
    """
    try:
        await users_me_get(request)
        return True

    except Exception:
        return False


async def me_get(request: Request, allow_request_state=True) -> dict:
    """
    Check if the current user is logged in. Return True if the user is logged in.
    """
    try:
        me: dict = await users_me_get(request, allow_request_state)
        return me

    except Exception:
        return {}


async def me_permissions(request: Request) -> list[str]:
    """
    GET a list of permissions that the current user has.
    ['root', 'admin', 'employee', 'user', 'guest'] and
    ['soft_delete', 'researcher', 'hard_delete', 'read', 'update', 'create', 'restore', 'scoped_read',]
    """
    try:
        me = await users_me_get(request)
        user_permissions: dict = me.get("permissions", {})
        user_permissions_list = user.permissions_as_list(user_permissions)
        return user_permissions_list
    except Exception:
        return []


async def schemas(request: Request) -> typing.Any:
    """
    GET all schemas from the api
    """
    async with _get_async_client() as client:
        url = base_url + "/schemas/?offset=0&limit=100000"
        headers = {"Accept": "application/json"}
        response = await client.get(url, headers=headers)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


def schema_get_name_version_from_entity(entity: dict):
    """
    GET schema name and version from an entity.
    """
    schema_name = entity["schema_name"]
    schema_version = schema_name.split("_")[1]
    schema_name = schema_name.split("_")[0]
    return schema_name, schema_version


async def schema_get(request: Request) -> typing.Any:
    """
    GET latest schema from the api
    """
    schema_type = request.path_params["schema_type"]
    return await schema_get_latest(request, schema_type)


async def schema_get_latest(request: Request, schema_type: str) -> typing.Any:
    """
    GET latest schema from the api
    """
    async with _get_async_client() as client:
        url = base_url + "/schemas/" + schema_type
        headers = {"Accept": "application/json"}
        response: httpx.Response = await client.get(url, headers=headers)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


ONE_YEAR = 60 * 60 * 24 * 365


async def schema_get_by_name_version(request: Request, schema_name: str, schema_version: int) -> typing.Any:
    """
    GET schema by name and version from the api
    """
    if get_cache(ONE_YEAR, [schema_name, schema_version]):
        return get_cache(ONE_YEAR, [schema_name, schema_version])

    async with _get_async_client() as client:
        url = base_url + "/schemas/" + schema_name + "?version=" + str(schema_version)
        headers = {"Accept": "application/json"}
        response = await client.get(url, headers=headers)

        if response.is_success:
            result = response.json()
            set_cache(result, [schema_name, schema_version])
            return result
        else:
            response.raise_for_status()


async def schema_create(request: Request) -> typing.Any:
    """
    POST a schema to the api in order to create a new schema
    """
    form = await request.form()
    schema_type = str(form.get("type"))
    data = str(form.get("data"))

    data_dict = {}
    data_dict["type"] = schema_type
    data_dict["data"] = json.loads(data)

    async with _get_async_client() as client:
        url = base_url + "/schemas/"
        headers = _get_jwt_headers(request, {"Content-Type": "application/json", "Accept": "application/json"})
        response = await client.post(url, json=data_dict, headers=headers)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def entity_post(request: Request) -> typing.Any:
    """
    POST an entity to the api in order to create a new entity
    """
    json_dict = await request.json()
    json_data = json_dict["data"]

    json_data = {"data": json_data, "schema_name": json_dict["schema_name"]}
    headers = _get_jwt_headers(request, {"Content-Type": "application/json", "Accept": "application/json"})
    url = base_url + "/entities/"

    async with _get_async_client() as client:
        response = await client.post(
            url=url,
            follow_redirects=True,
            headers=headers,
            json=json_data,
        )

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def entity_patch(request: Request) -> typing.Any:
    """
    PATCH an entity to the api in order to update a entity
    """
    uuid = request.path_params["uuid"]
    json_data = await request.json()
    headers = _get_jwt_headers(request, {"Content-Type": "application/json", "Accept": "application/json"})
    url = base_url + "/entities/" + uuid

    async with _get_async_client() as client:
        response = await client.patch(
            url=url,
            follow_redirects=True,
            headers=headers,
            json=json_data,
        )

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def entity_delete(request: Request, entity_type: str) -> typing.Any:
    """
    DELETE an entity to the api in order to delete a entity
    """
    entity_id = request.path_params["uuid"]

    async with _get_async_client() as client:
        url = base_url + "/entities/" + entity_id + "/" + entity_type
        headers = _get_jwt_headers(request, {"Accept": "application/json"})
        response = await client.delete(url, headers=headers)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def entities_get(request: Request) -> typing.Any:
    """
    GET all entities from the api
    """
    headers = _get_jwt_headers(request)
    headers["Accept"] = "application/json"
    url = base_url + "/entities/" + "?offset=0&limit=100000"

    async with _get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def entity_get(request: Request) -> typing.Any:
    """
    GET an entity from the api
    """
    entity_id = request.path_params["uuid"]

    async with _get_async_client() as client:
        url = base_url + "/entities/" + entity_id
        headers = {"Accept": "application/json"}
        response = await client.get(url, headers=headers)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def proxies_record_get_by_id(request: Request, record_id: str) -> typing.Any:
    """
    GET a record from the api
    """
    async with _get_async_client() as client:
        url = base_url + "/proxy/records/" + record_id
        headers = {"Accept": "application/json"}
        response = await client.get(url, headers=headers)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def proxies_records(request: Request, query_str: str) -> typing.Any:
    """
    GET search results from the api
    """
    query_str = quote(query_str)

    async with _get_async_client() as client:
        url = base_url + "/proxy/records?params=" + query_str
        response = await client.get(url)

        if response.is_success:
            records = response.json()
            return records
        else:
            response.raise_for_status()


async def proxies_get_resource(request, type: str, id: str) -> typing.Any:
    """
    GET a resource from the api
    """
    async with _get_async_client() as client:
        url = base_url + f"/proxy/{type}/{id}"
        response = await client.get(url)

        if response.is_success:
            json = response.json()
            return json

        else:
            response.raise_for_status()


async def proxies_get_relations(request: Request, type: str, id: str) -> typing.Any:
    """
    GET relations from the api
    """
    async with _get_async_client() as client:
        url = base_url + f"/proxy/{type}/{id}/relations"
        response = await client.get(url)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def proxies_post_relations(request: Request):
    """
    POST e a new relation
    """

    form_data = await request.form()

    async with _get_async_client() as client:
        url = base_url + "/proxy/relations"
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}

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

    async with _get_async_client() as client:
        url = base_url + "/proxy/relations/" + rel_id

        response = await client.delete(url)
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

    async with _get_async_client() as client:
        url = base_url + "/proxy/records?params=" + query_str
        response = await client.get(url)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def internal_api_get(request: Request, path: str) -> typing.Any:
    """
    GET data from an internal api
    """

    client_url = await _get_server_url(request)
    url = f"{client_url}{path}"

    async with _get_async_client() as client:
        response = await client.get(url)

        if response.is_success:
            return response.json()
        else:
            response.raise_for_status()


async def _get_server_url(request):
    scheme = request.url.scheme
    host = request.url.hostname
    port = request.url.port

    # Construct base URL
    server_url = f"{scheme}://{host}"
    if port:
        server_url += f":{port}"

    return server_url


async def proxies_auto_complete(request: Request, query_params: list = []) -> typing.Any:
    """
    Fetch auto complete data from the api
    Test data is used for now
    """

    q = request.query_params["q"]
    query_params.append(("t", q))

    query_str = query.get_str_from_list(query_params)
    auto_complete_url = f"https://aarhusiana.appspot.com/autocomplete_v3?{query_str}"

    async with _get_async_client() as client:
        response = await client.get(auto_complete_url)
        if response.is_success:
            return response.json()["result"]
        else:
            response.raise_for_status()


async def proxies_resolve(request: Request, ids=[]) -> typing.Any:
    """ "
    Resolve directly from a proxy endpoint
    """

    # zfill to 9 digits
    ids = [str(i).zfill(9) for i in ids]

    # ids needs to be a list dumped to json
    ids = json.dumps(ids)

    url = "https://openaws.appspot.com/resolve_records_v2"
    data = {"view": "record", "oasid": ids}

    async with _get_async_client() as client:
        response = await client.post(url, data=data)

        if response.is_success:
            result_json = response.json()
            if "result" not in result_json:
                return []

            return result_json["result"]
        else:
            response.raise_for_status()
