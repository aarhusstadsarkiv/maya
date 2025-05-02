"""
Auth endpoints.
"""

from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from stadsarkiv_client.core.templates import templates
from stadsarkiv_client.core.context import get_context
from stadsarkiv_client.core.auth import is_authenticated
from stadsarkiv_client.core import flash
from stadsarkiv_client.core.translate import translate
from stadsarkiv_client.core import user
from stadsarkiv_client.core.logging import get_log
from stadsarkiv_client.core.api import OpenAwsException
from stadsarkiv_client.core import api
from stadsarkiv_client.endpoints import auth_data
from stadsarkiv_client.core import cookie
import urllib.parse

log = get_log()


async def auth_login_get(request: Request):
    is_logged_in = await api.is_logged_in(request)

    post_url = "/auth/login"
    next_url = request.query_params.get("next")

    if next_url:
        encoded_next_url = urllib.parse.quote_plus(next_url)
        post_url = f"/auth/login?next={encoded_next_url}"
    else:
        next_url = f"/search?{cookie.get_query_str_display(request)}"
        encoded_next_url = urllib.parse.quote_plus(next_url)
        post_url = f"/auth/login?next={encoded_next_url}"

    context_values = {
        "title": translate("Login"),
        "post_url": post_url,
        "is_logged_in": is_logged_in,
    }
    context = await get_context(request, context_values=context_values)

    return templates.TemplateResponse(request, "auth/login.html", context)


async def auth_login_post(request: Request):
    next_url = request.query_params.get("next")

    try:
        await api.auth_jwt_login_post(request)
        flash.set_message(request, translate("You have been logged in."), type="success")

        if next_url:
            return JSONResponse({"error": False, "redirect": next_url})
        else:
            return JSONResponse({"error": False, "redirect": "/search"})

    except OpenAwsException as e:
        return JSONResponse({"message": str(e), "error": True})

    except Exception:
        log.exception("Error in auth_login_post")
        return JSONResponse(
            {
                "message": "Beklager, men noget gik galt. Fejlen er logget og vil blive undersøgt. Prøv igen senere",
                "error": True,
            }
        )


async def auth_logout_get(request: Request):

    try:
        user.logout(request)
        flash.set_message(request, translate("You have been logged out."), type="success")

    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_logout_post")
        flash.set_message(request, str(e), type="error")

    return RedirectResponse(url="/", status_code=302)


async def auth_logout_post(request: Request):
    try:
        user.logout(request)
        flash.set_message(request, translate("You have been logged out."), type="success")

    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_logout_post")
        flash.set_message(request, str(e), type="error")

    return RedirectResponse(url="/auth/login", status_code=302)


async def auth_set_cooke(request: Request):

    # get all POST variables
    post_data = await request.json()
    cookie_name = post_data.get("cookie_name")
    cookie_value = post_data.get("cookie_value")

    if cookie_name == "dark_theme":
        response = JSONResponse({})

        # 10 years
        MAX_AGE = 10 * 365 * 24 * 60 * 60
        if cookie_value:
            flash.set_message(request, message=translate("Dark theme enabled."), type="success")
            response.set_cookie(cookie_name, cookie_value, max_age=MAX_AGE, httponly=True)
        else:
            response.delete_cookie(cookie_name)
            flash.set_message(request, message=translate("Dark theme disabled."), type="success")
        return response
    else:
        return JSONResponse({})


async def auth_register_get(request: Request):

    context_values = {
        "title": translate("Register new user"),
        "register_done": request.query_params.get("register_done"),
    }
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "auth/register.html", context)


async def auth_register_post(request: Request):
    try:
        await api.auth_register_post(request)
        flash.set_message(
            request,
            translate("You have been registered. Check your email to confirm your account."),
            type="success",
        )

        return JSONResponse({"error": False})
    except OpenAwsException as e:
        return JSONResponse({"message": str(e), "error": True})
    except Exception as e:
        log.exception("Error in auth_register_post")
        return JSONResponse({"message": str(e), "error": True})


async def auth_verify(request: Request):
    try:
        await api.auth_verify_post(request)
        flash.set_message(
            request,
            translate("You have been verified."),
            type="success",
        )

        return RedirectResponse(url="/auth/login", status_code=302)
    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_verify")
        flash.set_message(request, str(e), type="error", use_settings=True)

    return RedirectResponse(url="/auth/login", status_code=302)


async def me_permission_translated(request: Request):
    permission_list = await api.me_permissions(request)
    permissions_translated = []

    for permission in permission_list:
        permissions_translated.append(translate(f"Permission {permission}"))

    return permissions_translated[-1]


async def auth_me_get(request: Request):
    await is_authenticated(request)
    try:

        # Check if "sent_mail" is in the query params
        sent_mail = request.query_params.get("sent_mail")

        me = await api.users_me_get(request)
        me["token"] = request.session["access_token"]
        permissions = await api.me_permissions(request)
        permission_translated = user.permission_translated(permissions)

        context_values = {
            "title": translate("Profile"),
            "me": me,
            "permission_translated": permission_translated,
            "sent_mail": sent_mail,
        }
        context = await get_context(request, context_values=context_values)

        return templates.TemplateResponse(request, "auth/me.html", context)
    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_me_get")
        flash.set_message(request, str(e), type="error")
        return RedirectResponse(url="/auth/login", status_code=302)


async def auth_search_results(request: Request):
    await is_authenticated(request)
    try:
        me = await api.users_me_get(request)
        context_values = {"title": translate("Your search results"), "me": me, "search_results": auth_data.api_search_results}
        context = await get_context(request, context_values=context_values)

        return templates.TemplateResponse(request, "auth/search_results.html", context)
    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_search_results")
        flash.set_message(request, str(e), type="error")
        return RedirectResponse(url="/auth/login", status_code=302)


async def auth_forgot_password_get(request: Request):
    context_values = {"title": translate("Forgot your password")}
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "auth/forgot_password.html", context)


async def auth_forgot_password_post(request: Request):
    try:
        await api.auth_forgot_password(request)
        flash.set_message(
            request,
            translate("An email has been sent to you with instructions on how to reset your password."),
            type="success",
        )
    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_forgot_password_post")
        flash.set_message(request, str(e), type="error", use_settings=True)

    return RedirectResponse(url="/auth/forgot-password", status_code=302)


async def auth_reset_password_get(request: Request):
    token = request.path_params["token"]
    context_values = {"title": translate("Enter new password"), "token": token}
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "auth/reset_password.html", context)


async def auth_reset_password_post(request: Request):
    try:
        await api.auth_reset_password_post(request)
        flash.set_message(
            request,
            translate("Your password has been reset. You can now login."),
            type="success",
        )
        return RedirectResponse(url="/auth/login", status_code=302)

    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_reset_password_post")
        flash.set_message(request, str(e), type="error", use_settings=True)

    token = request.path_params["token"]
    return RedirectResponse(url="/auth/reset-password/" + token, status_code=302)


async def auth_send_verify_email(request: Request):
    try:
        await api.auth_request_verify_post(request)
        flash.set_message(
            request,
            translate("A verify link has been sent to your email. You may verify your account now by clicking the link."),
            type="success",
        )

    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_send_verify_email")
        flash.set_message(request, str(e), type="error", use_settings=True)

    return RedirectResponse(url="/auth/me?sent_mail=1", status_code=302)


async def auth_user_info(request: Request):
    is_logged_in = await api.is_logged_in(request)
    return JSONResponse({"is_logged_in": is_logged_in})
