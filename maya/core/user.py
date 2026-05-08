"""
This module provides utility functions for managing user session data and permissions
within a Starlette-based web application.

Functions:
- permissions_as_list: Extracts and sorts a list of permission names from a permission dictionary.
- permission_translated: Translates the highest priority permission in a list into a human-readable string.
"""

from maya.core.translate import translate
from maya.core.logging import get_log

log = get_log()


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


def permissions_from_me(me: dict) -> list:
    """
    Return a list of permissions for the user based on the "me" endpoint response.
    """
    user_permissions: dict = me.get("permissions", {})
    user_permissions_list = permissions_as_list(user_permissions)
    return user_permissions_list


def has_permission(me: dict, permission: str) -> bool:
    """
    Check if the user has the required permission.
    The function will return True if the user has the specified permission.
    """
    user_permissions_list: list = permissions_from_me(me)
    return permission in user_permissions_list
