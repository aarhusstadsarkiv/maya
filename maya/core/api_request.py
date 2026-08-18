"""
Shared request helpers for API facade and adapters.
"""

from __future__ import annotations

import typing

from starlette.requests import Request

from maya.core.api_error import OpenAwsException
from maya.core.translate import translate


def get_auth_headers(request: Request, headers: typing.Optional[dict] = None) -> dict:
    """
    Get authenticated request headers for the v1 JWT authentication backend.
    """
    headers = headers or {}
    if "access_token" not in request.session:
        raise OpenAwsException(401, translate("You need to be logged in to view this page."))

    access_token = request.session["access_token"]
    headers["Authorization"] = f"Bearer {access_token}"
    return headers
