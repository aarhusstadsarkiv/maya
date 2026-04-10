from collections import defaultdict

from maya.database import crud_orders
from maya.database import utils_orders
from maya.database.crud import CRUD
from maya.database.utils import DatabaseConnection
from maya.orders import logging as orders_logging
from maya.orders import notifications


async def update_location(user_id: str, order_id: int, new_location: int, send_ready_mail: bool = True):
    """
    Update a single order location and optionally send the ready mail immediately.
    Returns the updated order when it became ready but mail sending is deferred.
    """
    database_connection = DatabaseConnection(crud_orders.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        order = await crud_orders._get_orders_one(crud, order_id=order_id)
        if order["location"] == new_location:
            return None

        await crud_orders._allow_location_change(crud, order["record_id"], raise_exception=True)
        await crud.update(table="records", update_values={"location": new_location}, filters={"record_id": order["record_id"]})

        order_update_values = {
            "updated_at": utils_orders.get_current_date_time(),
        }

        ready_order_to_notify = None
        if new_location == utils_orders.RECORD_LOCATION.READING_ROOM and order["order_status"] == utils_orders.ORDER_STATUS.ORDERED:
            order_update_values["expire_at"] = utils_orders.get_expire_at_date()

            if not order.get("message_sent"):
                if send_ready_mail:
                    await notifications.send_ready_orders_message(
                        crud_orders.MAIL_MESSAGE_ORDER_READY_TITLE,
                        crud_orders.MAIL_MESSAGE_ORDER_READY,
                        [order],
                    )
                    order_update_values["message_sent"] = 1
                else:
                    ready_order_to_notify = True

        await crud.update(table="orders", update_values=order_update_values, filters={"order_id": order_id})
        updated_order = await crud_orders._get_orders_one(crud, order_id=order_id)
        await crud_orders._insert_log_message(
            crud,
            user_id=user_id,
            order=updated_order,
            message=crud_orders.LOG_MESSAGES.LOCATION_CHANGED,
        )
        if send_ready_mail and updated_order.get("message_sent") and not order.get("message_sent"):
            await crud_orders._insert_log_message(
                crud,
                user_id=user_id,
                order=updated_order,
                message=crud_orders.LOG_MESSAGES.MAIL_SENT,
            )

        if ready_order_to_notify:
            return updated_order

        return None


async def bulk_update_locations(user_id: str, orders_and_locations: list[dict]):
    """
    Update multiple order locations and send grouped ready mails per user when relevant.
    """
    num_orders = len(orders_and_locations)
    ready_orders_by_user: dict[str, list[dict]] = defaultdict(list)

    for order_location in orders_and_locations:
        order_id = order_location["order_id"]
        assert isinstance(order_id, int)
        location = order_location["location"]
        assert isinstance(location, int)

        ready_order = await update_location(user_id, order_id, location, send_ready_mail=False)
        if ready_order:
            ready_orders_by_user[ready_order["user_id"]].append(ready_order)

    for user_orders in ready_orders_by_user.values():
        await notifications.send_ready_orders_message(
            crud_orders.MAIL_MESSAGE_ORDER_READY_TITLE,
            crud_orders.MAIL_MESSAGE_ORDER_READY,
            user_orders,
        )
        for order in user_orders:
            await orders_logging.mark_ready_order_message_sent(user_id, order["order_id"])

    return {"num_orders": num_orders}
