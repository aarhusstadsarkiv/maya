"""
Inactive v2 authentication adapter retained for possible future use.

This module is deliberately not imported by the active authentication path.
Restoring it also requires session-cookie request handling; see the note in
``maya.core.api_auth``.
"""

from __future__ import annotations

from starlette.requests import Request

from maya.core.api_client import get_async_client
from maya.core.api_error import (
    OpenAwsException,
    raise_openaws_exception,
    validate_captcha,
    validate_passwords,
    validate_user_name,
)
from maya.core.hooks import get_hooks
from maya.core.logging import get_log
from maya.core.translate import translate

log = get_log()

V2_REQUIRED_SESSION_COOKIE = "session"
V2_OPTIONAL_SESSION_COOKIES = ("client", "domain")
V2_SESSION_COOKIE_NAMES = (V2_REQUIRED_SESSION_COOKIE, *V2_OPTIONAL_SESSION_COOKIES)


class V2AuthAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def login(self, request: Request) -> dict:
        """Log in through the v2 ``/users/login`` endpoint."""
        hooks = get_hooks(request=request)
        form = await request.form()
        email = str(form.get("email", "")).strip()
        password = str(form.get("password", ""))

        if not email or not password:
            raise OpenAwsException(400, translate("Email and password are required to login."))

        async with get_async_client() as client:
            url = self.base_url + "/users/login"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": _get_user_agent(request),
            }
            json_post = {"email": email, "password": password}
            log.info(f"User login attempt: email={email} backend=v2")

            response = await client.post(url, json=json_post, headers=headers)
            json_response = response.json()

            if response.is_success:
                self._store_login_state(request, response)
                log.info(f"User login success: email={email} backend=v2")
                await hooks.after_login_success(json_response)
                return json_response

            log.info(f"User login failed: email={email} backend=v2 status_code={response.status_code}")
            await hooks.after_login_failure(json_response)
            raise_openaws_exception(response.status_code, json_response)

    async def register(self, request: Request) -> dict:
        """Register through the v2 ``/users/register`` endpoint."""
        await validate_captcha(request)
        await validate_user_name(request)
        await validate_passwords(request)

        form = await request.form()
        name = _get_display_name(form)
        email = str(form.get("email")).strip()
        password = str(form.get("password"))

        async with get_async_client() as client:
            url = self.base_url + "/users/register"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            json_post = {"name": name, "email": email, "password": password}
            log.info(f"User registration attempt: email={email} backend=v2")
            response = await client.post(url, json=json_post, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"User registration failed: email={email} backend=v2 status_code={response.status_code}")
                raise_openaws_exception(response.status_code, json_response)

            log.info(f"User registration success: email={email} backend=v2")
            return response.json()

    async def forgot_password(self, request: Request) -> None:
        """Request a password reset through ``/users/password-reset/request``."""
        form = await request.form()
        email = str(form.get("email")).strip()

        async with get_async_client() as client:
            url = self.base_url + "/users/password-reset/request"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            log.info(f"User password reset request attempt: email={email} backend=v2")
            response = await client.post(url, json={"email": email}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"User password reset request failed: email={email} backend=v2 status_code={response.status_code}")
                raise_openaws_exception(response.status_code, json_response)

            log.info(f"User password reset request success: email={email} backend=v2")

    async def verify(self, request: Request) -> None:
        """Verify an email through the v2 ``/users/verify`` endpoint."""
        token = request.path_params["token"]

        async with get_async_client() as client:
            url = self.base_url + "/users/verify"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            log.info("User verification attempt: backend=v2")
            response = await client.post(url, json={"token": token}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"User verification failed: backend=v2 status_code={response.status_code}")
                raise_openaws_exception(response.status_code, json_response)

            log.info("User verification success: backend=v2")

    async def request_verify(self, request: Request) -> None:
        """Request a new token through the v2 ``/users/verify/request`` endpoint."""
        from maya.core.api import users_me_get

        me = await users_me_get(request)
        email = me["email"]

        async with get_async_client() as client:
            url = self.base_url + "/users/verify/request"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            log.info(f"User verification request attempt: email={email} backend=v2")
            response = await client.post(url, json={"email": email}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"User verification request failed: email={email} backend=v2 status_code={response.status_code}")
                raise_openaws_exception(response.status_code, json_response)

            log.info(f"User verification request success: email={email} backend=v2")

    async def reset_password(self, request: Request) -> None:
        """Reset a password through the v2 ``/users/password-reset`` endpoint."""
        await validate_passwords(request)

        form = await request.form()
        password = str(form.get("password"))
        token = request.path_params["token"]

        async with get_async_client() as client:
            url = self.base_url + "/users/password-reset"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            log.info("User password reset attempt: backend=v2")
            response = await client.post(url, json={"password": password, "token": token}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"User password reset failed: backend=v2 status_code={response.status_code}")
                raise_openaws_exception(response.status_code, json_response)

            log.info("User password reset success: backend=v2")

    def logout(self, request: Request) -> None:
        log.info("User logout: backend=v2")
        _clear_auth_session(request)

    def _store_login_state(self, request: Request, response) -> None:
        for cookie_name in V2_SESSION_COOKIE_NAMES:
            cookie_value = response.cookies.get(cookie_name)
            if cookie_value:
                request.session[cookie_name] = cookie_value


def _get_user_agent(request: Request) -> str:
    user_agent = request.headers.get("user-agent", "").strip()
    if not user_agent:
        raise OpenAwsException(400, translate("User-Agent header is required to login."))
    return user_agent


def _get_display_name(form) -> str:
    first_name = str(form.get("first_name")).strip()
    last_name = str(form.get("last_name")).strip()
    return f"{first_name} {last_name}".strip()


def _clear_auth_session(request: Request) -> None:
    for cookie_name in V2_SESSION_COOKIE_NAMES:
        request.session.pop(cookie_name, None)
