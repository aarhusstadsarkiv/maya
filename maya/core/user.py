"""
This module provides utility functions for managing user session data and permissions
within a Starlette-based web application.

Functions:
- set_user_jwt: Stores JWT token and login metadata in the session.
- logout: Clears all session-related user data, effectively logging the user out.
- permissions_as_list: Extracts and sorts a list of permission names from a permission dictionary.
- permission_translated: Translates the highest priority permission in a list into a human-readable string.
"""

from starlette.requests import Request
from maya.core.translate import translate
from maya.core.logging import get_log


log = get_log()


def set_user_jwt(request: Request, access_token: str, token_type: str):
    """
    Set JWT token in session.
    """
    request.session["access_token"] = access_token
    request.session["token_type"] = token_type


def logout(request: Request):
    """
    Logout user by removing session variables.
    """
    request.session.pop("access_token", None)
    request.session.pop("token_type", None)


def permissions_as_list(permissions: dict) -> list[str]:
    """
    Returns a list of permissions from a dict of permissions.
    """

    # sort dict by grant_id
    permissions_sorted = sorted(permissions, key=lambda k: k["grant_id"])

    permissions_list = []
    for permission in permissions_sorted:
        permissions_list.append(permission["name"])

    return permissions_list


def permission_translated(permissions: list) -> str:
    """
    Return the highest permission from a list of permissions. Permission is returned as a translated string.
    """
    permission = permissions[0]
    return translate(f"Permission {permission}")
