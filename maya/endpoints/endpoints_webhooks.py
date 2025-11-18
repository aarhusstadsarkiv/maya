"""
Webhook endpoints
"""

from starlette.responses import JSONResponse
from starlette.requests import Request
from maya.core.logging import get_log
from maya.core.templates import get_template_content
from maya.core import api
from maya.core.dynamic_settings import settings


log = get_log()


async def mail_status(request: Request):
    """
    Mail status endpoint
    """

    # Get json data from request
    try:
        data = await request.json()
        log.info(data)
    except Exception:
        data = "Error in mail_status"
        log.exception("Error in mail_status")

    return JSONResponse({"status": "ok", "data": data})


async def mail_verify_token(request: Request):
    """
    Webhook after user has registered
    Note: This is not testable is using localhost as client url and a remote webservice for sending mails
    as the remote service cannot reach localhost. So no logging of success.
    """

    # Get json data from request
    try:
        data = await request.json()

        token = data["token"]
        user = data["to_user"]
        display_name = user["display_name"]
        title = "Bekræft din konto"

        template_values = {
            "title": title,
            "display_name": display_name,
            "client_verify_url": f"{settings['client_url']}/auth/verify/{token}",
            "client_domain_url": settings["client_url"],
            "client_name": settings["client_name"],
        }

        html_content = await get_template_content("mails/verify_email.html", template_values)

        user_id = user["id"]
        mail_dict = {
            "data": {
                "user_id": user_id,
                "subject": title,
                "sender": {"email": settings["client_email"], "name": settings["client_name"]},
                "reply_to": {"email": settings["client_email"], "name": settings["client_name"]},
                "html_content": html_content,
                "text_content": html_content,
            }
        }

        await api.mail_post(mail_dict)
        log.info(f"Verify email sent to: {user['email']}")
    except Exception:
        data = "Error in mail_status"
        log.exception("Error in sending verify email to user")

    return JSONResponse({"status": "ok", "data": data})


async def mail_reset_token(request: Request):
    """
    Webhook after user has requested a password reset
    Note: This is not testable is using localhost as client url and a remote webservice for sending mails
    as the remote service cannot reach localhost. So no logging of success.
    """
    # Get json data from request
    try:
        data = await request.json()

        token = data["token"]
        user = data["to_user"]
        display_name = user["display_name"]
        title = "Glemt adgangskode"

        template_values = {
            "title": title,
            "display_name": display_name,
            "client_reset_url": f"{settings['client_url']}/auth/reset-password/{token}",
            "client_domain_url": settings["client_url"],
            "client_name": settings["client_name"],
        }

        html_content = await get_template_content("mails/reset_password.html", template_values)

        user_id = user["id"]
        mail_dict = {
            "data": {
                "user_id": user_id,
                "subject": title,
                "sender": {"email": settings["client_email"], "name": settings["client_name"]},
                "reply_to": {"email": settings["client_email"], "name": settings["client_name"]},
                "html_content": html_content,
                "text_content": html_content,
            }
        }

        await api.mail_post(mail_dict)
        log.info(f"Reset email sent to: {user['email']}")
    except Exception:
        data = "Error in mail_status"
        log.exception("Error in sending reset email to user")

    return JSONResponse({"status": "ok", "data": data})
