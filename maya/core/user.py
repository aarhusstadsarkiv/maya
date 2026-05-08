"""
This module provides utility functions for managing user session data and permissions
within a Starlette-based web application.

Functions:
- permissions_as_list: Extracts and sorts a list of permission names from a permission dictionary.
- permission_translated: Translates the highest priority permission in a list into a human-readable string.
"""

from enum import IntEnum

from maya.core.translate import translate
from maya.core.logging import get_log

log = get_log()


class V2UserRole(IntEnum):
    VIEWER = 0
    EDITOR = 10
    MANAGER = 20
    ADMIN = 30


def permissions_as_list(permissions: list[dict]) -> list[str]:
    """
    Return a sorted list of permission names from the v1 permission payload.
    """
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
    if "permissions" in me:
        user_permissions = me.get("permissions", [])
        return permissions_as_list(user_permissions)

    if "role" in me:
        return _permissions_from_v2_role(me.get("role"))

    return []


def has_permission(me: dict, permission: str) -> bool:
    """
    Check if the user has the required permission.
    The function will return True if the user has the specified permission.
    """
    user_permissions_list: list = permissions_from_me(me)
    return permission in user_permissions_list


def _permissions_from_v2_role(role: int | None) -> list[str]:
    if role is None:
        return []

    if role == V2UserRole.ADMIN:
        return ["admin", "employee", "user"]

    if role in (V2UserRole.EDITOR, V2UserRole.MANAGER):
        return ["employee", "user"]

    if role == V2UserRole.VIEWER:
        return ["user"]

    log.warning(f"Unknown v2 role value in /users/me payload: {role}")
    return []
