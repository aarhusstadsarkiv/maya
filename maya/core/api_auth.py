"""
Version-specific authentication adapters for the external API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from starlette.requests import Request

from maya.core.api_client import get_api_profile, get_async_client
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


class AuthAdapter(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url

    @abstractmethod
    async def login(self, request: Request) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def register(self, request: Request) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def verify(self, request: Request) -> None:
        raise NotImplementedError

    @abstractmethod
    async def request_verify(self, request: Request) -> None:
        raise NotImplementedError

    @abstractmethod
    async def forgot_password(self, request: Request) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reset_password(self, request: Request) -> None:
        raise NotImplementedError

    @abstractmethod
    def logout(self, request: Request) -> None:
        raise NotImplementedError


class V1AuthAdapter(AuthAdapter):
    async def login(self, request: Request) -> dict:
        """
        Log in through the v1 `/auth/jwt/login` endpoint.
        """
        hooks = get_hooks(request=request)
        form = await request.form()
        username = str(form.get("email"))
        password = str(form.get("password"))

        if not username or not password:
            raise OpenAwsException(400, translate("Email and password are required to login."))

        login_dict = {"username": username, "password": password}

        async with get_async_client() as client:
            url = self.base_url + "/auth/jwt/login"
            headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}

            response = await client.post(url, data=login_dict, headers=headers)
            json_response = response.json()

            if response.is_success:
                access_token = json_response["access_token"]
                token_type = json_response["token_type"]
                self._store_login_state(request, access_token, token_type)
                await hooks.after_login_success(json_response)
                return json_response

            await hooks.after_login_failure(json_response)
            raise_openaws_exception(response.status_code, json_response)

    async def register(self, request: Request) -> dict:
        """
        Register through the v1 `/auth/register` endpoint.
        """
        await validate_captcha(request)
        await validate_user_name(request)
        await validate_passwords(request)

        form = await request.form()
        display_name = _get_display_name(form)
        email = str(form.get("email"))
        password = str(form.get("password"))

        async with get_async_client() as client:
            url = self.base_url + "/auth/register"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            json_post = {"email": email, "password": password, "display_name": display_name}
            response = await client.post(url, json=json_post, headers=headers)

            if not response.is_success:
                json_response = response.json()
                raise_openaws_exception(response.status_code, json_response)

            return response.json()

    async def forgot_password(self, request: Request) -> None:
        """
        Request a password reset through the v1 `/auth/forgot-password` endpoint.
        """
        form = await request.form()
        email = str(form.get("email"))

        async with get_async_client() as client:
            url = self.base_url + "/auth/forgot-password"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            response = await client.post(url, json={"email": email}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                raise_openaws_exception(response.status_code, json_response)

    async def verify(self, request: Request) -> None:
        """
        Verify an email through the v1 `/auth/verify` endpoint.
        """
        token = request.path_params["token"]

        async with get_async_client() as client:
            url = self.base_url + "/auth/verify"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            response = await client.post(url, json={"token": token}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                raise_openaws_exception(response.status_code, json_response)

    async def request_verify(self, request: Request) -> None:
        """
        Request a new verification token through the v1 `/auth/request-verify-token` endpoint.
        """
        from maya.core.api import users_me_get

        me = await users_me_get(request)
        email = me["email"]

        async with get_async_client() as client:
            url = self.base_url + "/auth/request-verify-token"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            response = await client.post(url, json={"email": email}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                raise_openaws_exception(response.status_code, json_response)

    async def reset_password(self, request: Request) -> None:
        """
        Reset a password through the v1 `/auth/reset-password` endpoint.
        """
        await validate_passwords(request)

        form = await request.form()
        password = str(form.get("password"))
        token = request.path_params["token"]

        async with get_async_client() as client:
            url = self.base_url + "/auth/reset-password"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            response = await client.post(url, json={"password": password, "token": token}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                raise_openaws_exception(response.status_code, json_response)

    def logout(self, request: Request) -> None:
        _clear_auth_session(request)

    def _store_login_state(self, request: Request, access_token: str, token_type: str) -> None:
        request.session["access_token"] = access_token
        request.session["token_type"] = token_type


class V2AuthAdapter(AuthAdapter):
    async def login(self, request: Request) -> dict:
        """
        Log in through the v2 `/users/login` endpoint.
        """
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
            log.info(f"Json payload for login: {json_post}")
            log.info(f"Logging in user {email} through v2 API at {url}")

            response = await client.post(url, json=json_post, headers=headers)
            json_response = response.json()

            if response.is_success:
                self._store_login_state(request, response)
                await hooks.after_login_success(json_response)
                return json_response

            log.info(f"Failed to login user {email} through v2 API: {json_response}")
            await hooks.after_login_failure(json_response)
            raise_openaws_exception(response.status_code, json_response)

    async def register(self, request: Request) -> dict:
        """
        Register through the v2 `/users/register` endpoint.
        """
        await validate_captcha(request)
        await validate_user_name(request)
        await validate_passwords(request)

        form = await request.form()
        name = _get_display_name(form)
        email = str(form.get("email")).strip()
        password = str(form.get("password"))

        async with get_async_client() as client:
            url = self.base_url + "/users/register"

            log.info(f"Registering user {email} through v2 API at {url}")
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            json_post = {"name": name, "email": email, "password": password}
            response = await client.post(url, json=json_post, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"Failed to register user {email} through v2 API: {json_response}")
                raise_openaws_exception(response.status_code, json_response)

            return response.json()

    async def forgot_password(self, request: Request) -> None:
        """
        Request a password reset through the v2 `/users/password-reset/request` endpoint.
        """
        form = await request.form()
        email = str(form.get("email")).strip()

        async with get_async_client() as client:
            url = self.base_url + "/users/password-reset/request"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            log.info(f"Requesting password reset for {email} through v2 API at {url}")
            response = await client.post(url, json={"email": email}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"Failed to request password reset for {email} through v2 API: {json_response}")
                raise_openaws_exception(response.status_code, json_response)

    async def verify(self, request: Request) -> None:
        """
        Verify an email through the v2 `/users/verify` endpoint.
        """
        token = request.path_params["token"]

        async with get_async_client() as client:
            url = self.base_url + "/users/verify"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            log.info(f"Verifying user through v2 API at {url}")
            response = await client.post(url, json={"token": token}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"Failed to verify user through v2 API: {json_response}")
                raise_openaws_exception(response.status_code, json_response)

    async def request_verify(self, request: Request) -> None:
        """
        Request a new verification token through the v2 `/users/verify/request` endpoint.
        """
        from maya.core.api import users_me_get

        me = await users_me_get(request)
        email = me["email"]

        async with get_async_client() as client:
            url = self.base_url + "/users/verify/request"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            log.info(f"Requesting verification token for {email} through v2 API at {url}")
            response = await client.post(url, json={"email": email}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"Failed to request verification token for {email} through v2 API: {json_response}")
                raise_openaws_exception(response.status_code, json_response)

    async def reset_password(self, request: Request) -> None:
        """
        Reset a password through the v2 `/users/password-reset` endpoint.
        """
        await validate_passwords(request)

        form = await request.form()
        password = str(form.get("password"))
        token = request.path_params["token"]

        async with get_async_client() as client:
            url = self.base_url + "/users/password-reset"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            log.info(f"Resetting password through v2 API at {url}")
            log.info(f"Using token: {token} and password of length {len(password)}")
            response = await client.post(url, json={"password": password, "token": token}, headers=headers)

            if not response.is_success:
                json_response = response.json()
                log.info(f"Failed to reset password through v2 API: {json_response}")
                raise_openaws_exception(response.status_code, json_response)

    def logout(self, request: Request) -> None:
        _clear_auth_session(request)

    def _store_login_state(self, request: Request, response) -> None:
        for cookie_name in V2_SESSION_COOKIE_NAMES:
            cookie_value = response.cookies.get(cookie_name)
            if cookie_value:
                request.session[cookie_name] = cookie_value


def get_auth_adapter() -> AuthAdapter:
    profile = get_api_profile()
    if profile.auth_backend == "session_cookie":
        return V2AuthAdapter(profile.base_url)
    return V1AuthAdapter(profile.base_url)


def _get_display_name(form) -> str:
    first_name = str(form.get("first_name")).strip()
    last_name = str(form.get("last_name")).strip()
    return f"{first_name} {last_name}".strip()


def _get_user_agent(request: Request) -> str:
    user_agent = request.headers.get("user-agent", "").strip()
    if not user_agent:
        raise OpenAwsException(400, translate("User-Agent header is required to login."))
    return user_agent


def _clear_auth_session(request: Request) -> None:
    request.session.pop("access_token", None)
    request.session.pop("token_type", None)
    request.session.pop("session", None)
    request.session.pop("client", None)
    request.session.pop("domain", None)
