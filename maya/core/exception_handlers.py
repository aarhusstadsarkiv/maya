"""
Custom exception handlers for the Starlette-based application.

This module defines centralized handlers for common error scenarios such as:
- 404 Not Found
- 500 Internal Server Error
- HTTP status errors raised by external API calls
- Authentication-related errors with support for both HTML and JSON responses

Each handler is responsible for logging, generating a user-friendly error page or response,
and providing relevant context to the frontend or API client.
"""

from starlette.exceptions import HTTPException
from starlette.responses import RedirectResponse, JSONResponse
from starlette.requests import Request
from maya.core.templates import templates
from maya.core.context import get_context
from maya.core.translate import translate
from maya.core.logging import get_log
from maya.core import flash
from maya.core.auth import AuthException, AuthExceptionJSON
from httpx import HTTPStatusError, TimeoutException
import traceback

HTML_404_PAGE = "404"
HTML_500_PAGE = "500"

log = get_log()


async def not_found(request: Request, exc: HTTPException):
    """
    404 Not Found error.
    """
    context_values = {
        "title": f"404 {translate('Error. Not Found')}",
        "status_code": 404,
        "human_error": "Siden du leder efter findes ikke. ",
    }

    # No need to log full exception. It's a 404
    log.warning(f"404 Not Found: {request.url}", extra={"error_code": 404, "error_url": str(request.url)})
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "errors/default.html", context, status_code=404)


async def http_status_error(request: Request, exc: HTTPStatusError):
    """
    Any HTTP status error that is not caught by the application.
    """

    exc_traceback = traceback.format_exc()
    title = f"{exc.response.status_code}. {translate('Error. Request Error')}"
    context_values = {
        "title": title,
        "status_code": exc.response.status_code,
        "human_error": (
            "Der skete en fejl, da systemet hentede data fra et API. Fejlen er blevet logget, og vi vil kigge på det hurtigst muligt."
        ),
        "exc": exc,
        "exc_traceback": exc_traceback,
    }

    extra = {"error_code": exc.response.status_code, "error_url": str(request.url)}
    log.exception(f"{exc.response.status_code} Error: {request.url}", extra=extra)
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "errors/default.html", context, status_code=exc.response.status_code)


async def http_timeout_error(request: Request, exc: TimeoutException):
    """
    Any HTTPX timeout error (connect/read/write/pool) when calling external APIs.
    """

    exc_traceback = traceback.format_exc()
    status_code = 504  # Gateway Timeout

    context_values = {
        "title": f"{status_code}. {translate('Error. Request Timeout')}",
        "status_code": status_code,
        "human_error": (
            "Der skete en fejl, da systemet hentede data fra et API. "
            "Forespørgslen tog for lang tid og blev afbrudt. Fejlen er blevet logget, "
            "og vi vil kigge på det hurtigst muligt."
        ),
        "exc": exc,
        "exc_traceback": exc_traceback,
    }

    extra = {"error_code": status_code, "error_url": str(request.url)}
    log.exception(f"{status_code} Timeout: {request.url}", extra=extra)

    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse("errors/default.html", context, status_code=status_code)


async def server_error(request: Request, exc: Exception):
    """
    Any 500 error that is not caught by the application.
    """

    exc_traceback = traceback.format_exc()
    context_values = {
        "title": f"500 {translate('Error. Server Error')}",
        "status_code": 500,
        "human_error": "Der skete en system fejl. Fejlen er blevet logget og vi vil kigge på det hurtigst muligt.",
        "exc": exc,
        "exc_traceback": exc_traceback,
    }

    extra = {"error_code": 500, "error_url": str(request.url)}
    log.exception(f"500 Error: {request.url}", extra=extra)
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "errors/default.html", context, status_code=500)


async def auth_exception_handler(request: Request, exc: AuthException):
    """
    AuthException handler for 403 Forbidden.
    """
    flash.set_message(request, exc.message, type="error")
    return RedirectResponse(url=exc.redirect_url, status_code=302)


async def auth_exception_json_handler(request: Request, exc: AuthExceptionJSON):
    """
    AuthException handler for 403 Forbidden with JSON response.
    """
    return JSONResponse({"error": True, "message": exc.message}, status_code=401)


exception_handlers = {
    404: not_found,
    500: server_error,
    HTTPStatusError: http_status_error,
    TimeoutException: http_timeout_error,
    AuthException: auth_exception_handler,
    AuthExceptionJSON: auth_exception_json_handler,
}
