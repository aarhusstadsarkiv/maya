"""
Bookmark sendpoints.
"""

from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from stadsarkiv_client.core.templates import templates
from stadsarkiv_client.core.context import get_context
from stadsarkiv_client.core.auth import is_authenticated, is_authenticated_json
from stadsarkiv_client.core import flash
from stadsarkiv_client.core.translate import translate
from stadsarkiv_client.core.logging import get_log
from stadsarkiv_client.core.api import OpenAwsException
from stadsarkiv_client.core import api
from stadsarkiv_client.records.meta_data_record import get_record_meta_data
from stadsarkiv_client.records import normalize_dates
from stadsarkiv_client.database.crud_default import database_url
from stadsarkiv_client.database.crud import CRUD
from stadsarkiv_client.database.utils import DatabaseConnection


log = get_log()


async def auth_bookmarks_get(request: Request):
    """
    User bookmarks page.
    """
    await is_authenticated(request)
    try:
        me = await api.me_get(request)
        filters = {"user_id": me["id"]}

        database_connection = DatabaseConnection(database_url)
        async with database_connection.transaction_scope_async() as connection:
            crud_default = CRUD(connection)
            bookmarks_db = await crud_default.select(
                table="bookmarks",
                columns=["record_id"],
                filters=filters,
                order_by=[("created_at", "DESC")],
                limit_offset=(100, 0),
            )

        record_list = [bookmark["record_id"] for bookmark in bookmarks_db]
        records = await api.proxies_resolve(request, record_list)

        bookmarks_data = []
        for record in records:

            try:

                record = normalize_dates.normalize_dates(record)
                meta_data = get_record_meta_data(request, record)

                record_id = meta_data["id"]
                record_link = f"/records/{record_id}"
                title = meta_data.get("title")
                date_normalized = record.get("date_normalized")
                collection_label = record.get("collection", {}).get("label", "")
                content_types_label = meta_data.get("content_types_label")
                portrait = meta_data.get("portrait")

                bookmark_data = {
                    "record_id": record_id,
                    "record_link": record_link,
                    "title": title,
                    "date_normalized": date_normalized,
                    "collection_label": collection_label,
                    "content_types": content_types_label,
                    "portrait": portrait,
                }
            except Exception:
                log.exception("Error in auth_bookmarks_get")
                continue

            bookmarks_data.append(bookmark_data)

        context_values = {"title": translate("Your bookmarks"), "me": me, "bookmarks_data": bookmarks_data}
        context = await get_context(request, context_values=context_values)

        return templates.TemplateResponse(request, "auth/bookmarks.html", context)
    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception("Error in auth_bookmarks_get")
        flash.set_message(request, str(e), type="error")
        return RedirectResponse(url="/auth/login", status_code=302)


async def auth_bookmarks_json(request: Request):
    """
    Get user bookmarks as JSON. Used for /records/{record_id} page.
    In /static/js/bookmarks-record.js
    """
    try:

        # get query param record_id
        record_id = request.query_params.get("record_id")
        if not record_id:
            return JSONResponse({"message": "No record_id provided", "error": True}, status_code=400)

        me = await api.me_get(request)
        filters = {"user_id": me["id"], "record_id": record_id}

        database_connection = DatabaseConnection(database_url)
        async with database_connection.transaction_scope_async() as connection:
            crud_default = CRUD(connection)
            bookmarks_list = await crud_default.select_one(table="bookmarks", filters=filters)

        return JSONResponse(bookmarks_list, status_code=200)
    except OpenAwsException as e:
        log.exception("Error in auth_bookmarks_json")
        json_data = {"message": str(e), "error": True}
        return JSONResponse(json_data, status_code=400)


async def auth_bookmarks_post(request: Request):
    """
    POST request to bookmark a record.
    """

    message = translate("You need to be logged in as user in order to bookmark a record.")
    await is_authenticated_json(request, ["user"], message=message)

    try:

        me = await api.users_me_get(request)
        user_id = me["id"]
        json_data = await request.json()
        filters = {"user_id": user_id, "record_id": json_data["record_id"]}
        insert_values = filters.copy()

        database_connection = DatabaseConnection(database_url)
        async with database_connection.transaction_scope_async() as connection:
            crud_default = CRUD(connection)
            exists = await crud_default.exists(table="bookmarks", filters=filters)
            if json_data["action"] == "remove" and exists:
                await crud_default.delete(table="bookmarks", filters=filters)
            elif json_data["action"] == "add" and not exists:
                await crud_default.insert(table="bookmarks", insert_values=insert_values)

    except OpenAwsException as e:
        log.exception("Error in auth_bookmarks_post")
        json_data = {"message": str(e), "error": True}
        return JSONResponse(json_data, status_code=400)

    except Exception as e:
        log.exception("Error in auth_bookmarks_post")
        json_data = {"message": str(e), "error": True}
        return JSONResponse(json_data, status_code=400)

    if json_data["action"] == "add":
        message = translate("Bookmark has been added.")
    else:
        message = translate("Bookmark has been removed.")

    json_data = {"message": message, "user_data": json_data, "error": False}
    return JSONResponse(json_data, status_code=200)
