"""
Version-specific user adapters for the external API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from starlette.requests import Request

from maya.core.api_client import get_api_profile, get_async_client
from maya.core.api_error import OpenAwsException
from maya.core.translate import translate


class UserAdapter(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url

    @abstractmethod
    async def me(self, request: Request) -> dict:
        raise NotImplementedError


class V1UserAdapter(UserAdapter):
    async def me(self, request: Request) -> dict:
        """
        Get the current user through the v1 `/users/me` endpoint.
        """
        return await _fetch_me(request, self.base_url)


class V2UserAdapter(UserAdapter):
    async def me(self, request: Request) -> dict:
        """
        Get the current user through the v2 `/users/me` endpoint.
        """
        return await _fetch_me(request, self.base_url)


def get_user_adapter() -> UserAdapter:
    profile = get_api_profile()
    if profile.name == "v2":
        return V2UserAdapter(profile.base_url)
    return V1UserAdapter(profile.base_url)


async def _fetch_me(request: Request, base_url: str) -> dict:
    from maya.core.api import _get_auth_headers

    if hasattr(request.state, "me"):
        return request.state.me

    headers = _get_auth_headers(request, {"Accept": "application/json"})
    url = base_url + "/users/me"

    async with get_async_client() as client:
        response = await client.get(
            url=url,
            follow_redirects=True,
            headers=headers,
        )

        if response.is_success:
            request.state.me = response.json()
            return response.json()

    raise OpenAwsException(
        422,
        translate("You need to be logged in to view this page."),
    )
