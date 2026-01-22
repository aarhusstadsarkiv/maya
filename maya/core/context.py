"""
This module provides helper functions to construct the context dictionary used in rendering templates
within the Maya application.

Functions included:
- `get_context`: Builds the complete context dictionary, incorporating request-specific and global data.
"""

from starlette.requests import Request
from maya.core.flash import get_messages
from maya.core.dynamic_settings import settings
from maya.core import api
from maya.core.hooks import get_hooks
from maya.core import cookie
from maya.core.logging import get_log
import urllib.parse

log = get_log()


async def get_context(request: Request, context_values: dict = {}, identifier: str = "") -> dict:
    """
    Get context for templates and add extra context using context_values.\n
    context_values: a dict that can be used to pass additional context values to the templates.\n
    identifier: is a string that can be used to identify the context.\n
    """
    hooks = get_hooks(request)

    # User specific context
    is_logged_in = await api.is_logged_in(request)
    permissions_list = await api.me_permissions(request)
    is_verified = await api.me_verified(request)
    is_employee = "employee" in permissions_list

    # search_query_str is used to display the last search query
    # it is e.g. present in the context_values if the request url is the search page
    # if it is not present, we check if it is set in cookies
    search_query_str = context_values.get("search_query_str", "")
    if "search_query_str" not in context_values:
        search_query_str = cookie.get_search_query_str(request)

    main_menu_system = _get_main_menu_system(is_logged_in, permissions_list)
    main_menu_system = _generate_menu_urls(request, main_menu_system, search_query_str)
    main_menu_top = _generate_menu_urls(request, settings["main_menu_top"], search_query_str)

    # default context variables available
    context = {
        "request": request,
        # user information
        "is_logged_in": is_logged_in,
        "is_verified": is_verified,
        "is_employee": is_employee,
        "permissions_list": permissions_list,
        # misc
        "search_query_str": search_query_str,
        "identifier": identifier,
        "flash_messages": get_messages(request),
        "title": _get_title(request),
        # Menus
        "main_menu_top": main_menu_top,
        "main_menu_system": main_menu_system,
        "main_menu_sections": settings["main_menu_sections"],
        # Theme
        "dark_theme": request.cookies.get("dark_theme", False),
    }

    # Add context_values to context
    context.update(context_values)
    if "meta_title" not in context:
        context["meta_title"] = context["title"]

    if "meta_description" not in context:
        context["meta_description"] = context["meta_title"]

    context = await hooks.before_context(context=context)
    return context


def _generate_menu_urls(request: Request, menu_items: list, search_query_str):
    """
    Generate URLs for the main menu items.
    In order to ease the process of using the items on the frontend.
    """

    for menu_item in menu_items:
        url = str(request.url_for(menu_item["name"]))
        if menu_item["name"] == "search_get":

            # Add search_query_str to search url
            menu_item["url"] = f"{url}?{search_query_str}"
        elif menu_item["name"] == "auth_login_get":

            # Add next parameter to login url
            path_with_query = request.url.path
            if request.url.query:
                path_with_query += f"?{request.url.query}"

            next_url = urllib.parse.quote(path_with_query, safe="")
            menu_item["url"] = f"{url}?next={next_url}"
        else:
            menu_item["url"] = url

    return menu_items


def _get_main_menu_system(is_logged_in: bool, permissions_list: list) -> list:
    """
    Get the main menu system. Based on the settings and the user's permissions.
    """
    main_menu_system: list = settings["main_menu_system"]

    if not settings.get("allow_user_registration", False):
        excluded_items = {
            "auth_login_get",
            "auth_register_get",
            "auth_forgot_password_get",
            "auth_logout_get",
            "auth_me_get",
            "auth_register_post",
            "auth_login_post",
            "auth_forgot_password_post",
        }
        main_menu_system = [item for item in main_menu_system if item["name"] not in excluded_items]

    if is_logged_in:
        excluded_items = {"auth_login_get", "auth_register_get", "auth_forgot_password_get"}
        main_menu_system = [item for item in main_menu_system if item["name"] not in excluded_items]

    if not is_logged_in:
        excluded_items = {"auth_logout_get", "auth_me_get"}
        main_menu_system = [item for item in main_menu_system if item["name"] not in excluded_items]

    if "employee" not in permissions_list:
        excluded_items = {"orders_admin_get"}
        main_menu_system = [item for item in main_menu_system if item["name"] not in excluded_items]

    if "root" not in permissions_list and "admin" not in permissions_list:
        excluded_items = {"admin_users_get", "schemas_get_list", "entities_get_list"}
        main_menu_system = [item for item in main_menu_system if item["name"] not in excluded_items]

    return main_menu_system


def _get_title(request: Request) -> str:
    """
    Get a title for a page which is part of settings["pages"].
    """

    title = ""
    pages: list[dict] = settings["pages"]

    for page in pages:
        if page["url"] == request.url.path:
            title = page["title"]
    return title
