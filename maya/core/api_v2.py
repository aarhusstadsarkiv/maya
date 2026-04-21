"""
V2 API interactions with the external web service.

This module now delegates to the v2 auth adapter. Most application code should
continue to use maya.core.api as the stable facade while endpoint groups migrate.
"""

from starlette.requests import Request

from maya.core.api_auth import get_v2_auth_adapter


async def auth_login_post(request: Request) -> dict:
    """
    Log in through the v2 `/users/login` endpoint.
    """
    return await get_v2_auth_adapter().login(request)


async def auth_register_post(request: Request) -> dict:
    """
    Register a new user through the v2 `/users/register` endpoint.
    """
    return await get_v2_auth_adapter().register(request)
