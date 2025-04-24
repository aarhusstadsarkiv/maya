from stadsarkiv_client.core import api
from starlette.requests import Request
from stadsarkiv_client.core.logging import get_log
from stadsarkiv_client.core.translate import translate

log = get_log()


def _get_redirect_url(request: Request):
    next_url = request.url.path
    return f"/auth/login?next={next_url}"


def _log_401_error(request: Request, message: str):
    extra = {
        "error_url": str(request.url),
        "error_type": "Unauthorized",
        "error_code": 401,
    }
    log.error(message, extra=extra)


def _log_403_error(request: Request, message: str):
    extra = {
        "error_url": str(request.url),
        "error_code": 403,
        "error_type": "Forbidden",
    }
    log.error(message, extra=extra)


class AuthException(Exception):
    def __init__(self, request: Request, message: str = "Authentication or permission failure", redirect_url="/login"):
        self.request = request
        self.message = message
        self.redirect_url = redirect_url
        super().__init__(self.message)


class AuthExceptionJSON(Exception):
    def __init__(self, message: str = "Authentication or permission failure"):
        self.message = message
        super().__init__(self.message)


async def _check_authentication(request: Request, permissions, message, verified, json_response):

    # prevent mutation of the permissions list
    permissions = tuple(permissions)

    is_logged_in = await api.is_logged_in(request)

    if not message:
        message = translate("You need to be logged in to view this page.")

    if not is_logged_in:
        _log_401_error(request, f"401 Unauthorized: {request.url}")
        if json_response:
            raise AuthExceptionJSON(message=message)
        raise AuthException(request, message=message, redirect_url=_get_redirect_url(request))

    users_me_get = await api.users_me_get(request)

    if verified and not users_me_get["is_verified"]:
        _log_403_error(request, f"403 Forbidden: {request.url}. User {users_me_get['email']}. User is not verified")
        message = translate("You need to verify your email address to view this page.")
        if json_response:
            raise AuthExceptionJSON(message=message)
        raise AuthException(request, message=message, redirect_url="/auth/me")

    if permissions:
        user_permissions_list = await api.me_permissions(request)
        permission_granted = any(permission in user_permissions_list for permission in permissions)

        if not permission_granted:
            _log_403_error(request, f"403 Forbidden: {request.url}. User {users_me_get['email']}. Missing required permissions")
            message = translate("You do not have the required permissions to view the page.")
            if json_response:
                raise AuthExceptionJSON(message=message)
            raise AuthException(
                request,
                message=message,
                redirect_url=_get_redirect_url(request),
            )


async def is_authenticated(request: Request, permissions=[], message=None, verified=False):
    await _check_authentication(request, permissions, message, verified, json_response=False)


async def is_authenticated_json(request: Request, permissions=[], message=None, verified=False):
    await _check_authentication(request, permissions, message, verified, json_response=True)
