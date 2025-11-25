from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from maya.core.templates import templates
from maya.core.context import get_context
from maya.core.auth import is_authenticated
from maya.core.logging import get_log
from maya.core import api
from maya.core import user
from maya.core.dynamic_settings import settings
from maya.core import flash
from maya.core.translate import translate
from maya.core import query
import asyncio

log = get_log()


def _get_pagination(request: Request):
    limit = "1000"
    offset = int(request.query_params.get("offset", "0"))
    next_offset = str(offset + int(limit))
    prev_offset = str(max(offset - int(limit), 0))

    return limit, str(offset), next_offset, prev_offset


async def admin_users_get(request: Request):
    """
    http://localhost:5555/admin/users?limit=10&descending=true&order=email&is_active=true
    http://localhost:5555/admin/users?limit=10&descending=true&order=email&is_active=true
    http://localhost:5555/admin/users?limit=10&descending=true&order=timestamp&is_active=true

    order: id, email, timestamp

    """
    await is_authenticated(request, permissions=["admin"])

    limit, offset, next_offset, prev_offset = _get_pagination(request)

    query_params = [
        ("limit", limit),
        ("offset", offset),
        ("descending", "true"),
        # ("order", "created_at"),
        ("is_active", "true"),
        # ("pattern", "gmail"),
    ]
    query_params_next = [
        ("limit", limit),
        ("offset", next_offset),
        ("descending", "true"),
        # ("order", "created_at"),
        ("is_active", "true"),
        # ("pattern", "gmail"),
    ]

    query_str = query.get_str_from_list(query_params)
    query_str_next = query.get_str_from_list(query_params_next)

    users, users_next = await asyncio.gather(api.users_get(request, query_str=query_str), api.users_get(request, query_str=query_str_next))

    has_next = bool(users_next)
    has_previous = int(offset) > 0

    for user_ in users:
        permissions = user.permissions_as_list(user_["permissions"])
        user_["permission_translated"] = user.permission_translated(permissions)

    context_values = {
        "title": "Brugere",
        "users": users,
        "has_next": has_next,
        "next_offset": next_offset,
        "has_previous": has_previous,
        "prev_offset": prev_offset,
    }

    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "admin/users.html", context)


async def admin_users_get_single(request: Request):
    await is_authenticated(request, permissions=["admin"])

    single_user, used_permissions = await asyncio.gather(
        api.user_get(request),
        api.user_permissions_subset(request),
    )

    permissions_user = user.permissions_as_list(single_user["permissions"])
    permission_translated = user.permission_translated(permissions_user)
    single_user["permission_translated"] = permission_translated

    context_values = {"title": "Bruger", "user": single_user, "permissions": used_permissions}
    context = await get_context(request, context_values=context_values)

    return templates.TemplateResponse(request, "admin/user_update.html", context)


async def admin_users_patch(request: Request):
    await is_authenticated(request, permissions=["admin"])

    uuid = request.path_params.get("uuid")
    redirect_url = request.url_for("admin_users_get_single", uuid=uuid)

    try:
        await api.users_patch_permissions(request)
        flash.set_message(request, translate("User has been updated"), type="success")
        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception:
        log.exception("Error in admin_users_patch")
        flash.set_message(request, translate("User could not be updated."), type="error")
        return RedirectResponse(url=redirect_url, status_code=302)


async def admin_users_delete(request: Request):
    await is_authenticated(request, permissions=["admin"])

    try:
        await api.users_delete(request)
        flash.set_message(request, translate("User has been deleted"), type="success")
        json_message = {"message": "User has been deleted."}
        return JSONResponse(json_message)
    except Exception:
        log.exception("Error in admin_users_delete")

        error = {
            "error": True,
            "message": "User could not be deleted.",
        }

        return JSONResponse(error)


async def admin_test(request: Request):
    pass


async def admin_users_get_json(request: Request):
    await is_authenticated(request, permissions=["admin"])
    user_ = await api.user_get(request)
    return JSONResponse(user_)


async def admin_config_get(request: Request):
    await is_authenticated(request, permissions=["admin"])
    dynamic_settings = settings
    return JSONResponse(dynamic_settings)
