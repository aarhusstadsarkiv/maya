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
from urllib.parse import urlencode
import asyncio

log = get_log()


USER_SORT_FIELDS = {
    "display_name": "Navn",
    "email": "E-mail",
    "id": "ID",
    "created_at": "Oprettet",
    "updated_at": "Opdateret",
    "last_login": "Seneste login",
    "is_active": "Er aktiv",
    "is_verified": "Er verificeret",
}
USER_PAGE_SIZE = 100


async def admin_users_get(request: Request):
    await is_authenticated(request, permissions=["admin"])

    params = request.query_params
    try:
        offset = max(0, int(params.get("offset", "0")))
    except ValueError:
        offset = 0
    order = params.get("order", "created_at")
    if order not in USER_SORT_FIELDS:
        order = "created_at"
    descending = params.get("descending", "true").lower() == "true"
    pattern = params.get("pattern", "").strip()
    verified_only = params.get("is_verified", "false").lower() == "true"
    query_params = {
        "limit": USER_PAGE_SIZE,
        "offset": offset,
        "order": order,
        "descending": str(descending).lower(),
        "is_active": "true",
    }
    if pattern:
        query_params["pattern"] = pattern
    if verified_only:
        query_params["is_verified"] = "true"

    users = await api.users_get(request, query_str=urlencode(query_params))
    # The API has no total count. Probe one row beyond a full page.
    has_next = False
    if len(users) == USER_PAGE_SIZE:
        next_params = {**query_params, "limit": 1, "offset": offset + USER_PAGE_SIZE}
        has_next = bool(await api.users_get(request, query_str=urlencode(next_params)))

    for user_ in users:
        permissions = user.permissions_as_list(user_["permissions"])
        user_["permission_translated"] = user.permission_translated(permissions)

    page_url = str(request.url_for("admin_users_get"))
    context_values = {
        "title": "Brugere",
        "users": users,
        "has_next": has_next,
        "next_url": page_url + "?" + urlencode({**query_params, "offset": offset + USER_PAGE_SIZE}),
        "has_previous": offset > 0,
        "prev_url": page_url + "?" + urlencode({**query_params, "offset": max(offset - USER_PAGE_SIZE, 0)}),
        "page_number": offset // USER_PAGE_SIZE + 1,
        "pattern": pattern,
        "verified_only": verified_only,
        "order": order,
        "descending": descending,
        "sort_fields": USER_SORT_FIELDS,
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


async def admin_users_get_json(request: Request):
    await is_authenticated(request, permissions=["admin"])
    user_ = await api.user_get(request)
    return JSONResponse(user_)


async def admin_config_get(request: Request):
    await is_authenticated(request, permissions=["admin"])
    dynamic_settings = settings
    return JSONResponse(dynamic_settings)
