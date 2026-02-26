"""
Define routes for the application.
"""

from starlette.routing import Route, Mount
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.requests import Request
from maya.endpoints import (
    endpoints_admin,
    endpoints_auth,
    endpoints_bookmarks,
    endpoints_entities,
    endpoints_error,
    endpoints_order,
    endpoints_pages,
    endpoints_records,
    endpoints_relations,
    endpoints_resources,
    endpoints_schemas,
    endpoints_search,
    endpoints_test,
    endpoints_upload,
    endpoints_webhooks,
)
import os
from maya.core.dynamic_settings import settings
from maya.core.multi_static import MultiStaticFiles
from maya.core.paths import get_base_dir_path
from maya.core.logging import get_log
from maya.core.module_loader import load_attr_from_file
from typing import Any

log = get_log()


def _get_static_dirs() -> list:
    """
    If static/ dir exists in local config dir, add it to static_dir_list
    This will be override the module static files
    """

    static_dir_list = []
    local_static_dir = get_base_dir_path("static")
    if os.path.exists(local_static_dir):
        static_dir_list.append(local_static_dir)
        log.debug(f"Loaded local static files: {local_static_dir}")
    else:
        log.debug(f"Local static files NOT loaded: {local_static_dir}")

    # Module static files. Default static files
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    static_dir_list.append(static_dir)

    return static_dir_list


def _get_robots_txt() -> str:
    robots_path = get_base_dir_path("static", "robots.txt")
    robots_content = """User-agent: *
    Disallow: /
    """

    if os.path.exists(robots_path):
        with open(robots_path, "r") as f:
            robots_content = f.read()

    return robots_content


ROBOTS_CONTENT = _get_robots_txt()


async def robots_txt(request: Request):
    return PlainTextResponse(ROBOTS_CONTENT)


async def favicon(request: Request):
    """
    /favicon.ico endpoint
    Redirects to /static/assets/favicon.ico?v={version}
    """
    version = settings["version"]
    redirect_url = f"/static/assets/favicon.ico?v={version}"
    return RedirectResponse(redirect_url)


# Add basic routes
routes = [
    Mount("/static", MultiStaticFiles(directories=_get_static_dirs()), name="static"),
    Route("/robots.txt", robots_txt),
    Route("/favicon.ico", favicon),
    Route("/admin/users", endpoint=endpoints_admin.admin_users_get, name="admin_users_get"),
    Route("/admin/users/{uuid}/update", endpoint=endpoints_admin.admin_users_get_single, name="admin_users_get_single"),
    Route("/admin/users/{uuid}/permissions", endpoint=endpoints_admin.admin_users_patch, name="admin_users_patch", methods=["POST"]),
    Route("/admin/users/{uuid}/delete", endpoint=endpoints_admin.admin_users_delete, name="admin_users_delete", methods=["POST"]),
    Route("/admin/users/{uuid}/json", endpoint=endpoints_admin.admin_users_get_json, name="admin_users_get_json"),
    Route("/admin/test", endpoint=endpoints_admin.admin_test, name="admin_test"),
    Route("/admin/config", endpoint=endpoints_admin.admin_config_get, name="admin_config_get"),
    Route("/auth/login", endpoint=endpoints_auth.auth_login_get, name="auth_login_get"),
    Route("/auth/login", endpoint=endpoints_auth.auth_login_post, name="auth_login_post", methods=["POST"]),
    Route("/auth/logout", endpoint=endpoints_auth.auth_logout_get, name="auth_logout_get"),
    Route("/auth/forgot-password", endpoint=endpoints_auth.auth_forgot_password_get, name="auth_forgot_password_get"),
    Route("/auth/forgot-password", endpoint=endpoints_auth.auth_forgot_password_post, name="auth_forgot_password_post", methods=["POST"]),
    Route("/auth/reset-password/{token:str}", endpoint=endpoints_auth.auth_reset_password_get, name="auth_reset_password_get"),
    Route(
        "/auth/reset-password/{token:str}",
        endpoint=endpoints_auth.auth_reset_password_post,
        name="auth_reset_password_post",
        methods=["POST"],
    ),
    Route("/auth/me", endpoint=endpoints_auth.auth_me_get, name="auth_me_get"),
    Route("/auth/cookie", endpoint=endpoints_auth.auth_set_cooke, name="auth_set_cooke", methods=["POST"]),
    Route("/auth/search-results", endpoint=endpoints_auth.auth_search_results, name="auth_search_results"),
    # verify request token sent by email
    Route("/auth/verify/{token:str}", endpoint=endpoints_auth.auth_verify, name="auth_verify"),
    # send verify email again
    Route("/auth/send-verify-email", endpoint=endpoints_auth.auth_send_verify_email, name="auth_send_verify_email"),
    Route("/auth/user-info", endpoint=endpoints_auth.auth_user_info, name="auth_user_info", methods=["POST"]),
    Route("/schemas/{schema_type:str}", endpoint=endpoints_schemas.schemas_get_single, name="schemas_get_single"),
    Route("/schemas", endpoint=endpoints_schemas.schemas_get_list, name="schemas_get_list"),
    Route("/schemas", endpoint=endpoints_schemas.schemas_post, name="schemas_post", methods=["POST"]),
    Route("/entities", endpoint=endpoints_entities.entities_get_list, name="entities_get_list"),
    Route("/entities", endpoint=endpoints_entities.entities_post, name="entities_post", methods=["POST"]),
    Route("/entities/{uuid:str}", endpoint=endpoints_entities.entities_get_single, name="entities_get_single"),
    Route("/entities/{uuid:str}/json/{type:str}", endpoint=endpoints_entities.entities_get_single_json, name="entities_get_single_json"),
    Route("/entities/{uuid:str}", endpoint=endpoints_entities.entities_patch, name="entities_patch", methods=["PATCH"]),
    Route("/entities/create/{schema_type:str}", endpoint=endpoints_entities.entities_create, name="entities_create"),
    Route("/entities/update/{uuid:str}", endpoint=endpoints_entities.entities_update, name="entities_update"),
    Route(
        "/entities/delete/{uuid:str}/{delete_type:str}",
        endpoint=endpoints_entities.entities_delete,
        name="entities_delete",
        methods=["DELETE", "GET"],
    ),
    Route("/search", endpoint=endpoints_search.search_get, name="search_get"),
    Route("/auto_complete", endpoint=endpoints_search.records_auto_complete_search, name="records_auto_complete_search"),
    Route("/auto_complete_relations", endpoint=endpoints_search.records_auto_complete_relations, name="records_auto_complete_relations"),
    Route("/search/json", endpoint=endpoints_search.search_get_json, name="search_get_json"),
    Route("/records/{record_id:str}", endpoint=endpoints_records.records_get, name="records_get"),
    Route("/records/{record_id:str}/json/{type:str}", endpoint=endpoints_records.records_get_misc, name="records_get_json"),
    Route("/records/{record_id:str}/html/{type:str}", endpoint=endpoints_records.records_get_misc, name="records_get_html"),
    Route("/relations", endpoint=endpoints_relations.relations_post, name="relations_post", methods=["POST"]),
    Route("/relations/{rel_id:str}", endpoint=endpoints_relations.relations_delete, name="relations_delete", methods=["DELETE"]),
    Route("/relations/{type:str}/{id:str}", endpoint=endpoints_relations.relations_get, name="relations_get"),
    Route("/error/log", endpoint=endpoints_error.error_log_post, name="error_log_post", methods=["POST"]),
    Route("/upload", endpoint=endpoints_upload.upload, name="upload", methods=["POST"]),
    Route("/webhook/mail/status", endpoint=endpoints_webhooks.mail_status, name="mail_status", methods=["GET", "POST"]),
    Route("/webhook/mail/token/verify", endpoint=endpoints_webhooks.mail_verify_token, name="mail_verify_token", methods=["GET", "POST"]),
    Route("/webhook/mail/token/reset", endpoint=endpoints_webhooks.mail_reset_token, name="mail_reset_token", methods=["GET", "POST"]),
]


if settings["allow_online_ordering"]:
    online_ordering = [
        Route("/auth/orders/{status_type:str}", endpoint=endpoints_order.orders_get_orders_user, name="orders_get_orders_user"),
        Route("/order/{record_id:str}", endpoint=endpoints_order.orders_post, name="orders_post_order", methods=["POST"]),
        Route("/admin/orders", endpoint=endpoints_order.orders_admin_get, name="orders_admin_get"),
        Route("/admin/orders/{order_id:str}/edit", endpoint=endpoints_order.orders_admin_get_edit, name="orders_admin_get_edit"),
        Route(
            "/order/patch/{order_id:int}/order-id",
            endpoint=endpoints_order.orders_user_delete_by_order_id,
            name="orders_user_patch_by_order_id",
            methods=["POST"],
        ),
        Route(
            "/order/patch/{record_id:str}/record-id",
            endpoint=endpoints_order.orders_user_delete_by_record_id,
            name="orders_user_patch_by_record_id",
            methods=["POST"],
        ),
        Route(
            "/order/patch/{order_id:str}/renew",
            endpoint=endpoints_order.orders_user_renew_by_order_id,
            name="orders_user_patch_renew",
            methods=["POST"],
        ),
        Route("/admin/orders/{record_id:str}/html", endpoint=endpoints_order.orders_record_get, name="orders_record_get"),
        Route("/admin/orders/logs", endpoint=endpoints_order.orders_logs, name="orders_logs"),
        Route(
            "/admin/orders/patch/{order_id:int}",
            endpoint=endpoints_order.orders_admin_patch_single,
            name="orders_admin_patch_single",
            methods=["POST"],
        ),
        Route(
            "/admin/orders/patch/{order_id:int}/promote",
            endpoint=endpoints_order.orders_admin_promote_application,
            name="orders_admin_patch_promote_application",
            methods=["POST"],
        ),
        Route(
            "/admin/orders/patch",
            endpoint=endpoints_order.orders_admin_patch_multiple,
            name="orders_admin_patch",
            methods=["POST"],
        ),
        Route(
            "/admin/orders/print",
            endpoint=endpoints_order.order_admin_print,
            name="orders_admin_print",
            methods=["GET", "POST"],
        ),
    ]
    routes.extend(online_ordering)

if settings["allow_save_bookmarks"]:
    routes_bookmarks = [
        Route("/auth/bookmarks", endpoint=endpoints_bookmarks.auth_bookmarks_get, name="auth_bookmarks_get"),
        Route("/auth/bookmarks", endpoint=endpoints_bookmarks.auth_bookmarks_post, name="auth_bookmarks_post", methods=["POST"]),
        Route("/auth/bookmarks/json", endpoint=endpoints_bookmarks.auth_bookmarks_json, name="auth_bookmarks_json"),
    ]
    routes.extend(routes_bookmarks)

if settings["allow_user_registration"]:
    routes_registration = [
        Route("/auth/register", endpoint=endpoints_auth.auth_register_get, name="auth_register_get"),
        Route("/auth/register", endpoint=endpoints_auth.auth_register_post, name="auth_register_post", methods=["POST"]),
    ]
    routes.extend(routes_registration)

if settings["environment"] == "development":
    routes_test = [
        Route("/test", endpoint=endpoints_test.test_get, name="test_get"),
        Route("/test/mail", endpoint=endpoints_test.test_mail, name="test_mail"),
        Route("/test", endpoint=endpoints_test.test_post, name="test_post", methods=["POST"]),
        Route("/test/{page:str}", endpoint=endpoints_test.test_page, name="test_page", methods=["GET", "POST"]),
        Route("/infinite-wait", endpoint=endpoints_test.infinite_wait, name="infinite_wait"),
    ]
    routes.extend(routes_test)

# Add routes for custom pages
common_pages: Any = []
if "pages" in settings:
    common_pages = settings["pages"]

for common_page in common_pages:
    url = common_page["url"]
    name = common_page["name"]

    routes.append(Route(url, endpoint=endpoints_pages.custom_page, name=name))

# Last as these are not very specific
routes.append(Route("/{resource_type:str}/{id:str}", endpoint=endpoints_resources.get_resource, name="resources_get"))
routes.append(
    Route(
        "/{resource_type:str}/{id:str}/json/{type:str}",
        endpoint=endpoints_resources.get_resource_json,
        name="resources_get_json",
    )
)


def init_module_routes(default_routes: list):
    """
    Load all routes from all plugins
    """

    plugins_dir = get_base_dir_path("plugins")
    if os.path.exists(plugins_dir):

        files = os.listdir(plugins_dir)
        for file_name in files:
            if ".plugin" not in file_name:
                continue

            plugin_path = os.path.join(plugins_dir, file_name)
            log.info(f"Loading plugin {plugin_path}")

            try:
                module_name = os.path.splitext(file_name)[0]
                get_routes: list = load_attr_from_file(
                    module_name,
                    "get_routes",
                    plugin_path,
                )

                if callable(get_routes):

                    log.info(f"Loading module {file_name}")
                    module_routes = get_routes()
                    default_routes = module_routes + default_routes

            except Exception:
                log.exception(f"Could not load module {file_name}")

    return default_routes


def get_app_routes():
    app_routes = init_module_routes(routes)
    return app_routes
