"""
Middleware configuration module for the application.

This module defines and registers a set of custom and third-party middleware
components used in a Starlette-based web application. The middleware stack
enhances the request/response lifecycle by adding features such as:

- Request timing and performance logging
- Session management with secure cookies
- CORS support for cross-origin requests
- Static file and cache handling
- Response preprocessing via hooks
- Access logging for auditing
- GZip compression for efficient payload delivery

Custom Middleware:
- RequestBeginMiddleware: Records the start time of a request to track performance.
- StaticPathSkippingMiddleware: Bypasses unnecessary logic for static file requests.
- ResponseTimeLoggingMiddleware: Logs the time used for request handling.
- NoCacheMiddleware: Controls caching behavior based on URL patterns.
- BeforeResponseMiddleware: Applies custom logic to the response before it is sent.
- AccessLogMiddleware: Logs detailed access information for each request.

Third-party Middleware:
- CORSMiddleware: Manages Cross-Origin Resource Sharing (CORS) policies.
- SessionMiddleware: Manages user sessions using secure cookies.
- SessionAutoloadMiddleware: Automatically loads session data on specified paths.
- GZipMiddleware: Compresses responses using GZip to reduce payload size.

The middleware list is assembled dynamically based on application settings.
"""

import asyncio
import json
import os
from time import time

from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from maya.core.dynamic_settings import settings
from maya.core.logging import get_log, get_access_log
from maya.core.logging_context import get_request_client_ip, reset_client_ip, set_client_ip
from maya.core import api, api_client
from maya.core.hooks import get_hooks
from maya.core.api_error import OpenAwsException
from maya.settings_types import ConcurrencyLimitSettings
from starlette.responses import JSONResponse, PlainTextResponse

log = get_log()
access_log = get_access_log()


class _ConcurrencyLimitRule:
    def __init__(self, config: ConcurrencyLimitSettings):
        if config["max"] < 1:
            raise ValueError("max must be at least 1")
        if not config["paths"]:
            raise ValueError("paths must contain at least one path")

        self.paths = config["paths"]
        self.exclude_paths = config.get("exclude_paths", [])

        for path in self.paths + self.exclude_paths:
            if "*" in path and path != "*" and (path.count("*") > 1 or not path.endswith("*")):
                raise ValueError("wildcards are only supported as '*' or at the end of a path")

        self.max_concurrency = config["max"]
        self.retry_after = config["retry_after"]
        self.active_requests = 0

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        for pattern in patterns:
            if pattern == "*" or pattern == path:
                return True
            if pattern.endswith("*") and path.startswith(pattern[:-1]):
                return True
        return False

    def matches(self, path: str) -> bool:
        return self._matches_any(path, self.paths) and not self._matches_any(path, self.exclude_paths)


class ConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    """
    Apply independent, overlapping concurrency limits within this process.

    Exact paths, trailing wildcards such as ``/records/*``, and the global ``*``
    wildcard are supported for included and excluded paths. A request counts
    against every matching rule and is rejected when any matching rule is
    exhausted.
    """

    def __init__(self, app, limits: list[ConcurrencyLimitSettings]):
        super().__init__(app)

        if not limits:
            raise ValueError("limits must contain at least one concurrency limit")

        self._limits = [_ConcurrencyLimitRule(config) for config in limits]
        self._counter_lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        matching_limits = [limit for limit in self._limits if limit.matches(request.url.path)]
        if not matching_limits:
            return await call_next(request)

        async with self._counter_lock:
            exhausted_limits = [limit for limit in matching_limits if limit.active_requests >= limit.max_concurrency]
            if exhausted_limits:
                return PlainTextResponse(
                    "Too Many Requests",
                    status_code=429,
                    headers={
                        "Retry-After": str(max(limit.retry_after for limit in exhausted_limits)),
                        "Cache-Control": "no-store",
                    },
                )

            for limit in matching_limits:
                limit.active_requests += 1

        try:
            return await call_next(request)
        finally:
            async with self._counter_lock:
                for limit in matching_limits:
                    limit.active_requests -= 1


class RequestBeginMiddleware(BaseHTTPMiddleware):
    """
    Used to set time_begin on request state in order to calculate time used on request
    """

    async def dispatch(self, request: Request, call_next):
        """
        Set time_begin on request state and add token to response header
        """
        request.state.time_begin = time()
        response = await call_next(request)

        return response


class ApiLogMiddleware(BaseHTTPMiddleware):
    """
    Logs time spent on all API calls made during the request
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # ignore /static
        path = request.url.path
        if path.startswith("/static"):
            return response

        total_response_time = api.get_time_used(request)
        log.debug(json.dumps(total_response_time, indent=4, ensure_ascii=False))
        api_client.reset_time_used()
        return response


class NoCacheMiddleware(BaseHTTPMiddleware):
    """
    Control caching behavior based on URL patterns
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        path = request.url.path
        ignore_paths = ["/records", "/search"]
        for ignore_path in ignore_paths:
            if path.startswith(ignore_path):
                # Default cache. No cache directives are sent, so the browser
                # will cache the response as it sees fit.
                return response

        # cache static files for 1 year. There should be versioning on the static files
        # so they will be reloaded when version is changed
        if path.startswith("/static"):
            response.headers["Cache-Control"] = "public, max-age=31536000"
            return response

        # Ensure no cache. Do not store any part of the response in the cache
        # Will force the browser to always request a new version of the page
        response.headers["Cache-Control"] = "no-store"
        return response


class CSPMiddleware(BaseHTTPMiddleware):
    """
    Content Security Policy middleware.
    Adds a Content-Security-Policy header to each response.
    """

    async def dispatch(self, request: Request, call_next):
        # Set nonce on request state for use in templates
        nonce = os.urandom(16).hex()
        request.state.csp_nonce = nonce

        response = await call_next(request)

        asset_src = [
            "'self'",
            "data:",
            "https://storage.googleapis.com",
            "https://acastorage.blob.core.windows.net",
            "https://nbg1.your-objectstorage.com",
        ]

        csp_policy = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"script-src-elem 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            f"img-src {' '.join(asset_src)}; "
            f"media-src {' '.join(asset_src)}; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://analytics.aarhusstadsarkiv.dk;"
        )

        response.headers["Content-Security-Policy"] = csp_policy
        return response


class BeforeResponseMiddleware(BaseHTTPMiddleware):
    """
    Apply before_response hooks to the response before sending it to the client
    """

    async def dispatch(self, request, call_next):

        response = await call_next(request)
        hooks = get_hooks(request)
        response = await hooks.before_response(response)
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Log all access information for each request
    """

    async def dispatch(self, request, call_next):

        # Generate logging info from request
        method = request.method
        path = request.url.path
        query_string = request.url.query
        if query_string:
            query_string = f"?{query_string}"
        user_agent = request.headers.get("user-agent", "-")

        if request.client:
            client_ip = request.client.host
            client_port = request.client.port
        else:
            client_ip = "unknown"
            client_port = "unknown"

        client_ip_token = set_client_ip(client_ip)
        try:
            start_time = time()

            # Process the request and get the response
            response = await call_next(request)

            # Log response details after it's processed
            status_code = response.status_code
            duration = time() - start_time

            # Log the access information to access.log, including client IP and port
            access_log.info(
                f'{client_ip}:{client_port} - "{method} {path}{query_string}" ' f'{status_code} {duration:.4f}s ua="{user_agent}'
            )

            return response
        finally:
            reset_client_ip(client_ip_token)


class SameOriginMiddleware(BaseHTTPMiddleware):
    """
    Control same-origin policy for state-changing requests
    """

    def __init__(
        self,
        app,
        allowed_origins: list | None = None,
        allow_same_origin: bool = True,
        exempt_path_prefixes: list | None = None,
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins or []
        self.allow_same_origin = allow_same_origin
        self.exempt_path_prefixes = exempt_path_prefixes or []

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if any(request.url.path.startswith(prefix) for prefix in self.exempt_path_prefixes):
                return await call_next(request)

            origin = request.headers.get("origin")

            try:
                if not origin or origin == "null":
                    raise OpenAwsException(403, "Forbidden. Bad Origin.")

                allowed = set(self.allowed_origins)
                if self.allow_same_origin:
                    same_origin = f"{request.url.scheme}://{request.url.netloc}"
                    allowed.add(same_origin)

                if origin not in allowed:
                    raise OpenAwsException(403, "Forbidden. Bad Origin.")
            except OpenAwsException as exc:
                extra = {
                    "client_ip": get_request_client_ip(request),
                    "error_code": exc.status_code,
                    "error_url": str(request.url),
                }
                log.exception(f"Forbidden request from origin: {origin}", extra=extra)
                return JSONResponse({"error": True, "message": exc.message}, status_code=exc.status_code)

        return await call_next(request)


middleware = []

middleware.append(Middleware(AccessLogMiddleware))
middleware.append(
    Middleware(
        ConcurrencyLimitMiddleware,
        limits=settings["concurrency_limits"],
    )
)
middleware.append(Middleware(RequestBeginMiddleware))

if settings["log_api_calls"]:
    middleware.append(Middleware(ApiLogMiddleware))

middleware.append(Middleware(GZipMiddleware))

# Indicate what domains the client browser should permit reading responses from. E.g. using fetch API calls
middleware.append(Middleware(CORSMiddleware, allow_origins=settings["cors_allow_origins"]))

# Instruct what resources and connections the client browser should permit
middleware.append(Middleware(CSPMiddleware))

# Instruct what origins the client browser should permit for state-changing requests
middleware.append(
    Middleware(
        SameOriginMiddleware,
        allowed_origins=settings["same_origin_allow_origins"],
        allow_same_origin=True,
        exempt_path_prefixes=settings["same_origin_exempt_path_prefixes"],
    )
)

# Session management with secure cookies
secret_key = str(os.getenv("SECRET"))
session_cookie = settings["cookie"]["name"]  # type: ignore
lifetime = settings["cookie"]["lifetime"]  # type: ignore
cookie_httponly = settings["cookie"]["httponly"]  # type: ignore
same_site = settings["cookie"]["samesite"]  # type: ignore

middleware.append(
    Middleware(
        SessionMiddleware,
        session_cookie=session_cookie,
        secret_key=secret_key,
        https_only=cookie_httponly,
        max_age=lifetime,
        same_site=same_site,
    )
)
middleware.append(Middleware(BeforeResponseMiddleware))
middleware.append(Middleware(NoCacheMiddleware))
