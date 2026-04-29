"""
Shared HTTP client and API profile helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import time

import httpx

from maya.core.dynamic_settings import settings

REQUEST_TIME_USED: dict = {}


@dataclass(frozen=True)
class ApiProfile:
    name: str
    base_url: str
    auth_backend: str


async def _request_start_time(request):
    """
    Custom event for httpx. Add a start time to the request.
    """
    request.start_time = time()


async def _request_custom_header(request: httpx.Request):
    """
    Custom event for httpx. Add a custom header to the request.
    """
    request.headers["x-key"] = settings["api_key"]
    request.headers["x-client"] = settings["client_name"]
    request.headers["x-client-domain-url"] = settings["client_url"]
    request.headers["Origin"] = settings["client_url"]
    return request


async def _response_httpx_timer(response):
    """
    Custom event for httpx. Log the time spend on the request.
    """
    request = response.request

    elapsed_time = time() - float(request.start_time)
    request_name = str(request.method) + "_" + str(request.url.path)
    set_time_used(request_name, elapsed_time)


def get_async_client() -> httpx.AsyncClient:
    """
    Get an async httpx client with custom events.
    """
    return httpx.AsyncClient(
        event_hooks={"request": [_request_custom_header, _request_start_time], "response": [_response_httpx_timer]},
        timeout=7,
    )


def set_time_used(name: str, elapsed: float) -> None:
    """
    Set response time as a state on the request in order to show API call timing.
    """
    if name not in REQUEST_TIME_USED:
        REQUEST_TIME_USED[name] = [elapsed]
    else:
        REQUEST_TIME_USED[name].append(elapsed)


def reset_time_used() -> None:
    """
    Reset API call timing for the current request lifecycle.
    """
    REQUEST_TIME_USED.clear()


def get_api_profile() -> ApiProfile:
    """
    Resolve the configured API profile.

    The default keeps the existing v1/JWT behavior. Setting api_profile to "v2"
    switches auth endpoints to v2/session-cookie behavior while the rest of the
    public facade can be migrated endpoint by endpoint.
    """
    profile_name = str(settings.get("api_profile", "v1"))

    if profile_name == "v2":
        return ApiProfile(
            name="v2",
            base_url=str(settings["api_base_url_v2"]),
            auth_backend="session_cookie",
        )

    return ApiProfile(
        name="v1",
        base_url=str(settings["api_base_url"]),
        auth_backend="jwt",
    )
