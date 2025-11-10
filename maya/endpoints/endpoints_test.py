"""
Just a test endpoint in order to test anything
Only enabled in development mode
"""

from starlette.requests import Request
from starlette.responses import JSONResponse
from maya.core.logging import get_log
from maya.core.context import get_context
from maya.core.templates import templates
from maya.database.cache import DatabaseCache
from maya.database.crud_default import database_url
from maya.database.utils import DatabaseConnection
from maya.core.dynamic_settings import settings
import random
import asyncio

log = get_log()


async def test_get(request: Request):

    insert_value = None
    # Get a result that is max 10 seconds old
    cache_expire = 10
    has_result = False

    database_connection = DatabaseConnection(database_url)
    async with database_connection.transaction_scope_async() as connection:
        cache = DatabaseCache(connection)
        result = await cache.get("test", cache_expire)

        if not result:
            # Set a new cache value
            insert_value = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
            await cache.set("test", {"random": insert_value})
        else:
            has_result = True

    return JSONResponse(
        {
            "message": "Test note inserted",
            "result": result,
            "has_result": has_result,
            "expire": cache_expire,
            "inserted_value": insert_value,
        }
    )


async def test_page(request: Request):
    # get page id from request
    page = request.path_params["page"]
    context_values = {"title": f"Test page: {page}"}
    context = await get_context(request, context_values=context_values)

    return templates.TemplateResponse(request, f"testing/{page}.html", context)


async def test_post(request: Request):
    context = await get_context(request)
    return templates.TemplateResponse(request, "testing/thanks.html", context)


async def test_mail(request: Request):
    """
    /test/mail
    """

    # settings["client_name"]
    token = "123456"
    context_values = {
        "display_name": "Test User",
        "client_verify_url": settings["client_url"] + "/auth/verify/" + token,
        "client_domain_url": settings["client_url"],
        "client_name": settings["client_name"],
    }

    context = await get_context(request, context_values=context_values)

    # template_str = await get_template_content("mails/verify_email.html", context)

    # data_dict = {
    #     "data": {
    #         "user_id": "01944542-2d7b-72bc-82bf-34e735b383cb",
    #         "subject": "Test",
    #         "sender": {"email": "stadsarkivet@aarhusarkivet.dk", "name": "Aarhus Stadsarkiv"},
    #         "reply_to": {"email": "stadsarkivet@aarhusarkivet.dk", "name": "Aarhus Stadsarkiv"},
    #         "html_content": "Test Test",
    #         "text_content": "Test Test",
    #     }
    # }

    # await api.mail_post(request, data_dict)

    return templates.TemplateResponse(request, "mails/verify_email.html", context)


async def infinite_wait(request):
    """
    Endpoint that never responds (simulates infinite wait)
    """
    await asyncio.Event().wait()
