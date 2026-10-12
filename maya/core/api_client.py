"""
Shared HTTP client and API profile helpers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from http.cookiejar import CookieJar, DefaultCookiePolicy
from time import perf_counter

import httpx2

from maya.core.dynamic_settings import settings

_shared_client: httpx2.AsyncClient | None = None
_request_time_used: ContextVar[dict[str, list[float]] | None] = ContextVar("api_time_used", default=None)


class _NoSharedCookies(DefaultCookiePolicy):
    def set_ok(self, cookie, request) -> bool:
        # Authentication belongs to each request, never the worker's cookie jar.
        return False


@dataclass(frozen=True)
class ApiProfile:
    name: str
    base_url: str


async def _request_start_time(request):
    """
    Custom event for httpx2. Add a start time to the request.
    """
    if _request_time_used.get() is not None:
        request.extensions["maya_start_time"] = perf_counter()


async def _request_custom_header(request: httpx2.Request):
    """
    Custom event for httpx2. Add a custom header to the request.
    """
    request.headers["x-key"] = settings["api_key"]
    request.headers["x-client"] = settings["client_name"]
    request.headers["x-client-domain-url"] = settings["client_url"]
    request.headers["Origin"] = settings["client_url"]
    return request


async def _response_httpx2_timer(response):
    """
    Custom event for httpx2. Log the time spend on the request.
    """
    request = response.request

    started = request.extensions.get("maya_start_time")
    if started is not None:
        elapsed_time = perf_counter() - started
        request_name = str(request.method) + "_" + str(request.url.path)
        set_time_used(request_name, elapsed_time)


def _create_async_client() -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        event_hooks={"request": [_request_custom_header, _request_start_time], "response": [_response_httpx2_timer]},
        timeout=7,
        cookies=CookieJar(policy=_NoSharedCookies()),
    )


@asynccontextmanager
async def client_lifespan() -> AsyncIterator[None]:
    """Own the worker's connection pool for the application lifetime."""
    global _shared_client
    async with _create_async_client() as client:
        _shared_client = client
        try:
            yield
        finally:
            _shared_client = None


@asynccontextmanager
async def get_async_client() -> AsyncIterator[httpx2.AsyncClient]:
    """Borrow the worker's client; standalone CLI calls own a temporary one."""
    if _shared_client is not None:
        yield _shared_client
    else:
        async with _create_async_client() as client:
            yield client


def set_time_used(name: str, elapsed: float) -> None:
    """
    Set response time as a state on the request in order to show API call timing.
    """
    timings = _request_time_used.get()
    if timings is not None:
        timings.setdefault(name, []).append(elapsed)


@contextmanager
def collect_timings() -> Iterator[None]:
    """Share timings with this request's child tasks, then release them."""
    token = _request_time_used.set({})
    try:
        yield
    finally:
        _request_time_used.reset(token)


def get_time_used() -> dict[str, list[float]]:
    return {name: values.copy() for name, values in (_request_time_used.get() or {}).items()}


def get_api_profile() -> ApiProfile:
    """
    Resolve the configured API profile.

    The profile selects the API used by version-specific non-auth adapters.
    Authentication always uses the v1/JWT adapter.
    """
    profile_name = str(settings.get("api_profile", "v1"))

    if profile_name == "v2":
        return ApiProfile(
            name="v2",
            base_url=str(settings["api_base_url_v2"]),
        )

    return ApiProfile(
        name="v1",
        base_url=str(settings["api_base_url"]),
    )
