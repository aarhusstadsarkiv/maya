"""
Middleware for the application
"""

from starsessions import CookieStore, SessionMiddleware, SessionAutoloadMiddleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from maya.core.dynamic_settings import settings
from maya.core.logging import get_log, get_access_log
from maya.core import api
import os
import json
from time import time
from maya.core.hooks import get_hooks


log = get_log()
access_log = get_access_log()


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


class StaticPathSkippingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)
        return await call_next(request)


class ResponseTimeLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        total_response_time = api.get_time_used(request)
        log.debug(json.dumps(total_response_time, indent=4, ensure_ascii=False))
        api.REQUEST_TIME_USED = {}
        return response


class NoCacheMiddleware(BaseHTTPMiddleware):
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


class BeforeResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):

        hooks = get_hooks(request)
        response = await call_next(request)
        response = await hooks.before_response(response)
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):

        # Log request details
        method = request.method
        path = request.url.path
        query_string = request.url.query  # Extract the query string
        if query_string:
            query_string = f"?{query_string}"

        # Handle cases where request.client might be None
        if request.client:
            client_ip = request.client.host
            client_port = request.client.port
        else:
            client_ip = "unknown"
            client_port = "unknown"

        start_time = time()

        # Process the request and get the response
        response = await call_next(request)

        # Log response details after it's processed
        status_code = response.status_code
        duration = time() - start_time

        # Log the access information to access.log, including client IP and port
        access_log.info(f'{client_ip}:{client_port} - "{method} {path}{query_string}" {status_code} {duration:.4f}s')

        return response


# Variables for cookie handling
secret_key = str(os.getenv("SECRET"))
session_store: CookieStore = CookieStore(secret_key=secret_key)
lifetime = settings["cookie"]["lifetime"]  # type: ignore
cookie_httponly = settings["cookie"]["httponly"]  # type: ignore


middleware = []
middleware.append(Middleware(CORSMiddleware, allow_origins=settings["cors_allow_origins"]))
middleware.append(Middleware(RequestBeginMiddleware))
middleware.append(Middleware(SessionMiddleware, store=session_store, cookie_https_only=cookie_httponly, lifetime=lifetime))
middleware.append(Middleware(SessionAutoloadMiddleware, paths=["/"]))
middleware.append(Middleware(BeforeResponseMiddleware))
middleware.append(Middleware(StaticPathSkippingMiddleware))

if settings["log_api_calls"]:
    middleware.append(Middleware(ResponseTimeLoggingMiddleware))

middleware.append(Middleware(NoCacheMiddleware))
middleware.append(Middleware(AccessLogMiddleware))
middleware.append(Middleware(GZipMiddleware, minimum_size=1))
