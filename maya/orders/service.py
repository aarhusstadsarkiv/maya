from collections import defaultdict

from maya.database import crud_orders
from maya.orders import notifications


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

        ready_order = await crud_orders.update_order(
            user_id=user_id,
            order_id=order_id,
            update_values={"location": location},
            send_ready_mail=False,
        )
        if ready_order:
            ready_orders_by_user[ready_order["user_id"]].append(ready_order)

    for user_orders in ready_orders_by_user.values():
        await notifications.send_ready_orders_message(
            crud_orders.MAIL_MESSAGE_ORDER_READY_TITLE,
            crud_orders.MAIL_MESSAGE_ORDER_READY,
            user_orders,
        )
        for order in user_orders:
            await crud_orders.mark_ready_order_message_sent(user_id, order["order_id"])

    return {"num_orders": num_orders}
