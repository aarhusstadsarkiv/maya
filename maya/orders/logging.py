from maya.database.crud import CRUD
from maya.database.utils import DatabaseConnection
from maya.orders.constants import LOG_MESSAGES
from maya.orders import repository
from maya.orders import runtime


async def mark_ready_order_message_sent(user_id: str, order_id: int):
    """
    Mark a ready-order mail as sent and write the corresponding log message.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        order = await repository.get_order_one(crud, order_id=order_id)
        if order.get("message_sent"):
            return

        await crud.update(table="orders", update_values={"message_sent": 1}, filters={"order_id": order_id})
        updated_order = await repository.get_order_one(crud, order_id=order_id)
        await repository.insert_log_message(
            crud,
            user_id=user_id,
            order=updated_order,
            message=LOG_MESSAGES.MAIL_SENT,
        )
