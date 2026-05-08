"""
Shared request helpers for API facade and adapters.
"""

from __future__ import annotations

import typing

from starlette.requests import Request

from maya.core import api_client
from maya.core.api_error import OpenAwsException
from maya.core.api_auth import V2_REQUIRED_SESSION_COOKIE, V2_OPTIONAL_SESSION_COOKIES
from maya.core.translate import translate


def get_auth_headers(request: Request, headers: typing.Optional[dict] = None) -> dict:
    """
    Get authenticated request headers for the active API profile.
    """
    headers = headers or {}
    profile = api_client.get_api_profile()
    if profile.auth_backend == "session_cookie":
        if V2_REQUIRED_SESSION_COOKIE not in request.session:
            raise OpenAwsException(401, translate("You need to be logged in to view this page."))

        cookie_names = [V2_REQUIRED_SESSION_COOKIE]
        cookie_names.extend(name for name in V2_OPTIONAL_SESSION_COOKIES if name in request.session)
        cookies = [f"{name}={request.session[name]}" for name in cookie_names]
        headers["Cookie"] = "; ".join(cookies)
        return headers

    if "access_token" not in request.session:
        raise OpenAwsException(401, translate("You need to be logged in to view this page."))

    access_token = request.session["access_token"]
    headers["Authorization"] = f"Bearer {access_token}"
    return headers
