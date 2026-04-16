"""
Define routes for the application.
"""

from maya.endpoints import endpoints_order
from starlette.routing import Route

online_ordering = [
    Route("/auth/orders/{status_type:str}", endpoint=endpoints_order.orders_get_orders_user, name="orders_get_orders_user"),
    Route("/order/{record_id:str}", endpoint=endpoints_order.orders_post, name="orders_post_order", methods=["POST"]),
    Route("/admin/orders", endpoint=endpoints_order.orders_admin_get, name="orders_admin_get"),
    Route("/admin/orders/{order_id:int}/edit", endpoint=endpoints_order.orders_admin_get_edit, name="orders_admin_get_edit"),
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
        "/order/patch/{order_id:int}/renew",
        endpoint=endpoints_order.orders_user_renew_by_order_id,
        name="orders_user_patch_renew",
        methods=["POST"],
    ),
    Route(
        "/order/patch/renew-all",
        endpoint=endpoints_order.orders_user_renew_all,
        name="orders_user_patch_renew_all",
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
