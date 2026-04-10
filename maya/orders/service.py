from collections import defaultdict

from maya.database import utils_orders
from maya.database.crud import CRUD
from maya.database.utils import DatabaseConnection
from maya.orders.constants import LOG_MESSAGES, MAIL_MESSAGE_ORDER_READY, MAIL_MESSAGE_ORDER_READY_TITLE
from maya.orders.constants import MAIL_MESSAGE_ORDER_RENEW_TITLE, SYSTEM_USER_ID, get_mail_message_order_renew
from maya.orders import logging as orders_logging
from maya.orders import notifications
from maya.orders import repository
from maya.orders import runtime


async def update_location_with_crud(
    crud: "CRUD",
    user_id: str,
    order_id: int,
    new_location: int,
    send_ready_mail: bool = True,
):
    """
    Update a single order location using an existing CRUD/transaction context.
    """
    order = await repository.get_order_one(crud, order_id=order_id)
    if order["location"] == new_location:
        return None

    await repository.allow_location_change(crud, order["record_id"], raise_exception=True)
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
                    MAIL_MESSAGE_ORDER_READY_TITLE,
                    MAIL_MESSAGE_ORDER_READY,
                    [order],
                )
                order_update_values["message_sent"] = 1
            else:
                ready_order_to_notify = True

    await crud.update(table="orders", update_values=order_update_values, filters={"order_id": order_id})
    updated_order = await repository.get_order_one(crud, order_id=order_id)
    await repository.insert_log_message(
        crud,
        user_id=user_id,
        order=updated_order,
        message=LOG_MESSAGES.LOCATION_CHANGED,
    )
    if send_ready_mail and updated_order.get("message_sent") and not order.get("message_sent"):
        await repository.insert_log_message(
            crud,
            user_id=user_id,
            order=updated_order,
            message=LOG_MESSAGES.MAIL_SENT,
        )

    if ready_order_to_notify:
        return updated_order

    return None


async def update_location(user_id: str, order_id: int, new_location: int, send_ready_mail: bool = True):
    """
    Update a single order location and optionally send the ready mail immediately.
    Returns the updated order when it became ready but mail sending is deferred.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await update_location_with_crud(
            crud=crud,
            user_id=user_id,
            order_id=order_id,
            new_location=new_location,
            send_ready_mail=send_ready_mail,
        )


async def update_order_status_with_crud(
    crud: "CRUD",
    user_id: str,
    order_id: int,
    new_status: int,
):
    """
    Update an order status using an existing CRUD/transaction context.
    If a queued order is promoted, send/log ready mail when relevant.
    """
    order = await repository.get_order_one(crud, order_id=order_id)

    if new_status == order["order_status"]:
        return None

    await crud.update(table="orders", update_values={"order_status": new_status}, filters={"order_id": order_id})

    order = await repository.get_order_one(crud, order_id=order_id)
    await repository.insert_log_message(crud, user_id, order, LOG_MESSAGES.STATUS_CHANGED)

    next_queued_order = await repository.get_order_one(
        crud,
        statuses=[utils_orders.ORDER_STATUS.QUEUED],
        record_id=order["record_id"],
    )
    if next_queued_order:
        await crud.update(
            table="orders",
            update_values={"order_status": utils_orders.ORDER_STATUS.ORDERED},
            filters={"order_id": next_queued_order["order_id"]},
        )

        if next_queued_order["location"] == utils_orders.RECORD_LOCATION.READING_ROOM:
            expire_at = utils_orders.get_expire_at_date()
            await crud.update(
                table="orders",
                update_values={"expire_at": expire_at, "message_sent": 1},
                filters={"order_id": next_queued_order["order_id"]},
            )
            next_queued_order = await repository.get_order_one(crud, order_id=next_queued_order["order_id"])
            await notifications.send_ready_orders_message(
                MAIL_MESSAGE_ORDER_READY_TITLE,
                MAIL_MESSAGE_ORDER_READY,
                [next_queued_order],
            )

        await repository.insert_log_message(
            crud,
            user_id=user_id,
            order=next_queued_order,
            message=LOG_MESSAGES.STATUS_CHANGED,
        )
        if next_queued_order["location"] == utils_orders.RECORD_LOCATION.READING_ROOM and next_queued_order.get("message_sent"):
            await repository.insert_log_message(
                crud,
                user_id=user_id,
                order=next_queued_order,
                message=LOG_MESSAGES.MAIL_SENT,
            )

    return None


async def update_order_status(user_id: str, order_id: int, new_status: int):
    """
    Update an order status in its own transaction.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await update_order_status_with_crud(
            crud=crud,
            user_id=user_id,
            order_id=order_id,
            new_status=new_status,
        )


async def is_owner(user_id: str, order_id: int) -> bool:
    """
    Check whether a user owns a given order.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await crud.exists(
            table="orders",
            filters={"order_id": order_id, "user_id": user_id},
        )


async def has_active_order(user_id: str, record_id: str):
    """
    Check whether a user already has an active-ish order on a record.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await repository.has_active_order_on_record(crud, user_id, record_id)


async def replace_employee(me: dict):
    """
    Insert or update employee details.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        user_data = utils_orders.get_insert_user_data(me)
        await crud.replace("users", user_data, {"user_id": me["id"]})


async def promote_application_order_with_crud(
    crud: "CRUD",
    user_id: str,
    order_id: int,
):
    """
    Promote an application order using an existing CRUD/transaction context.
    """
    order = await repository.get_order_one(crud, order_id=order_id)

    if order["order_status"] != utils_orders.ORDER_STATUS.APPLICATION:
        return None

    existing_ordered = await repository.get_order_one(
        crud,
        statuses=[utils_orders.ORDER_STATUS.ORDERED],
        record_id=order["record_id"],
    )

    target_status = utils_orders.ORDER_STATUS.QUEUED if existing_ordered else utils_orders.ORDER_STATUS.ORDERED
    update_values: dict = {
        "order_status": target_status,
        "updated_at": utils_orders.get_current_date_time(),
    }

    if target_status == utils_orders.ORDER_STATUS.ORDERED and order["location"] == utils_orders.RECORD_LOCATION.READING_ROOM:
        update_values["expire_at"] = utils_orders.get_expire_at_date()

        if not order.get("message_sent"):
            await notifications.send_ready_orders_message(
                MAIL_MESSAGE_ORDER_READY_TITLE,
                MAIL_MESSAGE_ORDER_READY,
                [order],
            )
            update_values["message_sent"] = 1

    await crud.update(
        table="orders",
        update_values=update_values,
        filters={"order_id": order_id},
    )

    updated_order = await repository.get_order_one(crud, order_id=order_id)
    await repository.insert_log_message(
        crud,
        user_id=user_id,
        order=updated_order,
        message=LOG_MESSAGES.STATUS_CHANGED,
    )
    if updated_order.get("message_sent") and not order.get("message_sent"):
        await repository.insert_log_message(
            crud,
            user_id=user_id,
            order=updated_order,
            message=LOG_MESSAGES.MAIL_SENT,
        )

    return updated_order


async def promote_application_order(user_id: str, order_id: int):
    """
    Promote an application order in its own transaction.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await promote_application_order_with_crud(
            crud=crud,
            user_id=user_id,
            order_id=order_id,
        )


async def insert_order_with_crud(
    crud: "CRUD",
    meta_data: dict,
    record_and_types: dict,
    me: dict,
) -> dict:
    """
    Insert an order using an existing CRUD/transaction context.
    """
    if await repository.has_active_order_on_record(crud, me["id"], meta_data["id"]):
        raise Exception("User is already active on this record")

    await repository.update_user_record_data(crud, meta_data, record_and_types, me)

    order_status = await repository.get_insert_order_status(crud, meta_data)
    order_data = utils_orders.get_order_data(
        me["id"],
        meta_data["id"],
        order_status,
    )
    await crud.insert("orders", order_data)

    last_order_id = await crud.last_insert_id()
    last_inserted_order = await repository.get_order_one(crud, order_id=last_order_id)

    if (
        last_inserted_order["location"] == utils_orders.RECORD_LOCATION.READING_ROOM
        and order_status == utils_orders.ORDER_STATUS.ORDERED
    ):
        expire_at = utils_orders.get_expire_at_date()
        last_inserted_order["expire_at"] = expire_at
        await crud.update(
            table="orders",
            update_values={"expire_at": expire_at, "message_sent": 1},
            filters={"order_id": last_inserted_order["order_id"]},
        )
        await notifications.send_ready_orders_message(
            MAIL_MESSAGE_ORDER_READY_TITLE,
            MAIL_MESSAGE_ORDER_READY,
            [last_inserted_order],
        )

    await repository.insert_log_message(
        crud,
        user_id=last_inserted_order["user_id"],
        order=last_inserted_order,
        message=LOG_MESSAGES.ORDER_CREATED,
    )
    if last_inserted_order["location"] == utils_orders.RECORD_LOCATION.READING_ROOM and order_status == utils_orders.ORDER_STATUS.ORDERED:
        await repository.insert_log_message(
            crud,
            user_id=last_inserted_order["user_id"],
            order=last_inserted_order,
            message=LOG_MESSAGES.MAIL_SENT,
        )

    return await repository.get_order_one(crud, order_id=last_order_id)


async def insert_order(meta_data: dict, record_and_types: dict, me: dict) -> dict:
    """
    Insert an order in its own transaction.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await insert_order_with_crud(
            crud=crud,
            meta_data=meta_data,
            record_and_types=record_and_types,
            me=me,
        )


async def update_comment_with_crud(crud: "CRUD", order_id: int, new_comment: str):
    await crud.update(
        table="orders",
        update_values={
            "comment": new_comment,
            "updated_at": utils_orders.get_current_date_time(),
        },
        filters={"order_id": order_id},
    )


async def update_order(
    user_id: str,
    order_id: int,
    update_values: dict,
    send_ready_mail: bool = True,
):
    """
    Update one supported aspect of an order.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        comment = update_values.get("comment")
        order_status = update_values.get("order_status")
        location = update_values.get("location")
        expire_at = update_values.get("expire_at")

        ready_order_to_notify = None

        if comment is not None:
            await update_comment_with_crud(crud, order_id, comment)

        if location:
            ready_order_to_notify = await update_location_with_crud(
                crud,
                user_id,
                order_id,
                location,
                send_ready_mail=send_ready_mail,
            )

        if order_status in [utils_orders.ORDER_STATUS.COMPLETED, utils_orders.ORDER_STATUS.DELETED]:
            await update_order_status_with_crud(crud, user_id, order_id, order_status)

        if expire_at:
            await crud.update(
                table="orders",
                update_values={"expire_at": expire_at},
                filters={"order_id": order_id},
            )

        return ready_order_to_notify


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
            MAIL_MESSAGE_ORDER_READY_TITLE,
            MAIL_MESSAGE_ORDER_READY,
            user_orders,
        )
        for order in user_orders:
            await orders_logging.mark_ready_order_message_sent(user_id, order["order_id"])

    return {"num_orders": num_orders}


async def get_order(order_id: int):
    """
    Get a single order for display, including computed fields.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        order = await repository.get_order_one(crud, order_id=order_id)
        order = utils_orders.format_order_display(order)
        allow_location_change = await repository.allow_location_change(crud, order["record_id"])
        order["allow_location_change"] = allow_location_change
        return order


async def get_order_by_record_id(user_id: str, record_id: str):
    """
    Get a single raw joined order by user and record_id.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await repository.get_order_one(crud, user_id=user_id, record_id=record_id)


async def get_orders_user_count(user_id: str) -> int:
    """
    Count active-ish user orders for the order limit check.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await repository.get_orders_user_count(crud, user_id)


async def get_logs(order_id: int = 0, limit: int = 100, offset: int = 0) -> list:
    """
    Get logs for an order, formatted for display.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        logs = await repository.get_logs(crud, order_id=order_id, limit=limit, offset=offset)
        for single_log in logs:
            utils_orders.format_log_display(single_log)
        return logs


def _get_and_filters_str_and_values(filters) -> tuple:
    search_filters = []
    if filters.filter_location:
        search_filters.append("r.location =:location_filter")
    if filters.filter_email:
        search_filters.append("u.user_email LIKE :email_filter")
    if filters.filter_user:
        search_filters.append("u.user_display_name LIKE :user_filter")

    placeholder_values = {}
    if search_filters:
        placeholder_values = {
            "location_filter": filters.filter_location,
            "email_filter": f"{filters.filter_email}%",
            "user_filter": f"{filters.filter_user}%",
        }

    search_filters_as_str = ""
    if search_filters:
        search_filters_as_str = " AND " + " AND ".join(search_filters)

    return search_filters_as_str, placeholder_values


async def _get_queued_orders_length(crud: "CRUD", orders: list[dict]) -> dict:
    records_ids = [order["record_id"] for order in orders]
    list_of_record_ids = ", ".join([f"'{record_id}'" for record_id in records_ids])

    query = f"""
SELECT record_id, COUNT(*) AS queued_count
FROM orders
WHERE order_status IN ({utils_orders.ORDER_STATUS.QUEUED})
AND record_id IN ({list_of_record_ids})
GROUP BY record_id
ORDER BY queued_count DESC;
"""
    queued_orders = await crud.query(query, {})
    return {order["record_id"]: order["queued_count"] for order in queued_orders}


async def _get_active_orders(crud: "CRUD", filters, offset: int = 0) -> list:
    search_filters_as_str, placeholder_values = _get_and_filters_str_and_values(filters)

    if filters.filter_show_queued:
        order_statuses = f"{utils_orders.ORDER_STATUS.ORDERED}, {utils_orders.ORDER_STATUS.QUEUED}, {utils_orders.ORDER_STATUS.APPLICATION}"
    else:
        order_statuses = f"{utils_orders.ORDER_STATUS.ORDERED}, {utils_orders.ORDER_STATUS.APPLICATION}"

    query = f"""
SELECT o.*, r.*, u.*
FROM orders o
LEFT JOIN records r ON o.record_id = r.record_id
LEFT JOIN users u ON o.user_id = u.user_id
WHERE o.order_status IN ({order_statuses})
{search_filters_as_str}
ORDER BY o.order_id DESC
LIMIT {filters.filter_limit} OFFSET {offset}
"""

    return await crud.query(query, placeholder_values)


async def _get_completed_records(crud: "CRUD", filters, offset: int = 0) -> list:
    search_filters_as_str, placeholder_values = _get_and_filters_str_and_values(filters)
    query = f"""
SELECT o.*, r.*, u.*
FROM orders o
LEFT JOIN records r ON o.record_id = r.record_id
LEFT JOIN users u ON o.user_id = u.user_id
WHERE
    o.order_status IN ({utils_orders.ORDER_STATUS.COMPLETED}, {utils_orders.ORDER_STATUS.DELETED})
    AND o.order_id = (
        SELECT o2.order_id
        FROM orders o2
        WHERE o2.record_id = o.record_id
          AND o2.order_status IN ({utils_orders.ORDER_STATUS.COMPLETED}, {utils_orders.ORDER_STATUS.DELETED})
        ORDER BY o2.updated_at DESC, o2.order_id DESC
        LIMIT 1
    )
    AND o.record_id NOT IN (
        SELECT record_id
        FROM orders
        WHERE order_status IN ({utils_orders.ORDER_STATUS.ORDERED}, {utils_orders.ORDER_STATUS.APPLICATION})
    )
    AND r.location <> {utils_orders.RECORD_LOCATION.IN_STORAGE}
    {search_filters_as_str}
ORDER BY o.updated_at DESC
LIMIT {filters.filter_limit} OFFSET {offset};
"""
    return await crud.query(query, placeholder_values)


async def _get_history_orders(crud: "CRUD", filters, offset: int = 0) -> list:
    search_filters_as_str, placeholder_values = _get_and_filters_str_and_values(filters)
    query = f"""
SELECT o.*, r.*, u.*
    FROM orders o
    LEFT JOIN records r ON o.record_id = r.record_id
    LEFT JOIN users u ON o.user_id = u.user_id
    WHERE o.order_status IN ({utils_orders.ORDER_STATUS.DELETED}, {utils_orders.ORDER_STATUS.COMPLETED})
    {search_filters_as_str}
    ORDER BY o.updated_at DESC
    LIMIT {filters.filter_limit} OFFSET {offset}
"""
    return await crud.query(query, placeholder_values)


async def get_orders_user(user_id: str, status: str = "active") -> list:
    """
    Get all orders for a user. Exclude orders with specific statuses.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        if status == "active":
            query = f"""
            SELECT o.*, r.*, u.*
FROM orders o
LEFT JOIN records r ON o.record_id = r.record_id
LEFT JOIN users u ON o.user_id = u.user_id
WHERE o.order_status IN ({utils_orders.ORDER_STATUS.ORDERED})
AND r.location = {utils_orders.RECORD_LOCATION.READING_ROOM}
AND o.user_id = :user_id
ORDER BY o.order_id DESC
            """
        elif status == "reserved":
            query = f"""
            SELECT o.*, r.*, u.*
FROM orders o
LEFT JOIN records r ON o.record_id = r.record_id
LEFT JOIN users u ON o.user_id = u.user_id
WHERE
  o.user_id = :user_id
  AND (
    o.order_status IN ({utils_orders.ORDER_STATUS.QUEUED}, {utils_orders.ORDER_STATUS.APPLICATION})
    OR (
      o.order_status IN ({utils_orders.ORDER_STATUS.ORDERED})
      AND r.location <> {utils_orders.RECORD_LOCATION.READING_ROOM}
    )
  )
ORDER BY o.order_id DESC
            """
        else:
            query = ""

        orders = await crud.query(query, {"user_id": user_id})

        for order in orders:
            order["renewal_possible"] = await is_order_renew_possible(crud, order=order)
            order["days_remaining"] = utils_orders.get_days_until_expire(order)

        orders = [utils_orders.format_order_display(order) for order in orders]
        orders = [utils_orders.format_order_display_user(order, status) for order in orders]
        return orders


async def is_order_renew_possible(crud: "CRUD", order: dict):
    """
    Check whether an order qualifies for renewal.
    """
    if not order["expire_at"]:
        return False

    if utils_orders.get_days_until_expire(order) > utils_orders.DEADLINE_DAYS_RENEWAL:
        return False

    queued = await repository.get_order_one(
        crud,
        record_id=order["record_id"],
        statuses=[utils_orders.ORDER_STATUS.QUEUED],
    )
    if queued:
        return False

    return True


async def renew_order_with_crud(crud: "CRUD", user_id: str, order_id: int) -> bool:
    """
    Renew a single order within an existing transaction.
    """
    order = await repository.get_order_one(crud, order_id=order_id)

    renew_possible = await is_order_renew_possible(crud, order)
    if not renew_possible:
        raise Exception(f"Bestilling {order_id} kan ikke fornyes")

    expire_at_date = utils_orders.get_expire_at_date()
    await crud.update(table="orders", update_values={"expire_at": expire_at_date}, filters={"order_id": order_id})

    renewed_order = await repository.get_order_one(crud, order_id=order_id)
    await repository.insert_log_message(
        crud,
        user_id=user_id,
        order=renewed_order,
        message=LOG_MESSAGES.ORDER_RENEWED,
    )
    return True


async def renew_order(user_id: str, order_id: int):
    """
    Renew a single order.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        await renew_order_with_crud(crud, user_id, order_id)


async def renew_orders_user(user_id: str) -> int:
    """
    Renew all qualifying active user orders.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        query = f"""
        SELECT o.*
        FROM orders o
        LEFT JOIN records r ON o.record_id = r.record_id
        WHERE o.user_id = :user_id
          AND o.order_status = {utils_orders.ORDER_STATUS.ORDERED}
          AND r.location = {utils_orders.RECORD_LOCATION.READING_ROOM}
        ORDER BY o.order_id DESC
        """
        orders = await crud.query(query, {"user_id": user_id})

        num_renewed = 0
        for order in orders:
            try:
                await renew_order_with_crud(crud, user_id, order["order_id"])
                num_renewed += 1
            except Exception:
                continue

        return num_renewed


async def get_orders_admin(filters) -> tuple[list, object]:
    """
    Get admin order lists with pagination metadata.
    """
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        offset = filters.filter_offset
        if filters.filter_status == "active":
            orders = await _get_active_orders(crud, filters, offset)
            queued_orders = await _get_queued_orders_length(crud, orders)

            for order in orders:
                order = utils_orders.format_order_display(order)
                record_id = order["record_id"]
                order["count"] = queued_orders.get(record_id, 0)
                if order["location"] != utils_orders.RECORD_LOCATION.READING_ROOM:
                    order["allow_location_change"] = True

            offset_next = offset + filters.filter_limit
            orders_next = await _get_active_orders(crud, filters, offset_next)

        if filters.filter_status == "completed":
            orders = await _get_completed_records(crud, filters, offset)

            for order in orders:
                order = utils_orders.format_order_display(order)
                order["user_actions_deactivated"] = True
                order["allow_location_change"] = True

            offset_next = offset + filters.filter_limit
            orders_next = await _get_completed_records(crud, filters, offset_next)

        if filters.filter_status == "order_history":
            orders = await _get_history_orders(crud, filters, offset)

            for order in orders:
                order = utils_orders.format_order_display(order)
                order["user_actions_deactivated"] = True
                order["allow_location_change"] = False

            offset_next = offset + filters.filter_limit
            orders_next = await _get_history_orders(crud, filters, offset_next)

        has_next = bool(len(orders_next))
        filters.filter_has_next = has_next
        filters.filter_has_prev = bool(filters.filter_offset > 0)
        filters.filter_next_offset = filters.filter_offset + filters.filter_limit if has_next else 0
        filters.filter_prev_offset = filters.filter_offset - filters.filter_limit if filters.filter_has_prev else 0

        return orders, filters


async def cron_orders_expire() -> int:
    """
    Complete expired orders and promote the next queued order when relevant.
    """
    runtime.cron_log.info("Starting cron_orders_expire")
    try:
        database_connection = DatabaseConnection(runtime.orders_url)
        async with database_connection.transaction_scope_async() as connection:
            crud = CRUD(connection)
            query = f"""
            SELECT * FROM orders
            WHERE expire_at IS NOT NULL
            AND expire_at < :current_date
            AND order_status = {utils_orders.ORDER_STATUS.ORDERED}"""

            params = {"current_date": utils_orders.get_current_date_time()}
            orders_expire = await crud.query(query, params)
            runtime.cron_log.info(f"Found {len(orders_expire)} orders to expire")
    except Exception:
        runtime.cron_log.exception("Failed to get orders for cron_orders")
        return 0

    num_orders_expired = 0
    for order in orders_expire:
        try:
            database_connection = DatabaseConnection(runtime.orders_url)
            async with database_connection.transaction_scope_async() as connection:
                crud = CRUD(connection)
                runtime.log.info(f"Order {order['order_id']} has passed expire_at. Setting status to COMPLETED")
                await update_order_status_with_crud(
                    crud,
                    SYSTEM_USER_ID,
                    order["order_id"],
                    utils_orders.ORDER_STATUS.COMPLETED,
                )
                num_orders_expired += 1
        except Exception:
            runtime.log.exception(f"Failed to update order {order['order_id']} to COMPLETED")

    return num_orders_expired


async def cron_renewal_emails() -> int:
    """
    Send grouped renewal emails per user for renewable orders.
    """
    renewal_orders = []
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        date_indicating_renewal = utils_orders.get_date_indicating_renewal_mail()
        query = f"""
            SELECT o.*, r.*, u.*
FROM orders o
LEFT JOIN records r ON o.record_id = r.record_id
LEFT JOIN users u ON o.user_id = u.user_id
WHERE o.expire_at IS NOT NULL
AND o.expire_at = :expire_at
AND o.order_status = {utils_orders.ORDER_STATUS.ORDERED}
ORDER BY o.user_id, o.order_id
        """
        params = {"expire_at": date_indicating_renewal}
        renewal_orders = await crud.query(query, params)
        runtime.cron_log.info(f"Found {len(renewal_orders)} orders with expire_at = {date_indicating_renewal}")

    num_renewal_emails = 0
    database_connection = DatabaseConnection(runtime.orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        renewal_orders_by_user = defaultdict(list)

        for order in renewal_orders:
            try:
                if not await is_order_renew_possible(crud, order):
                    runtime.cron_log.info(f"Order {order['order_id']} could not be renewed")
                    continue

                renewal_orders_by_user[order["user_id"]].append(order)
            except Exception:
                runtime.cron_log.exception(f"Failed renewal eligibility check for order {order['order_id']}")

        for user_id, user_orders in renewal_orders_by_user.items():
            try:
                runtime.cron_log.info(
                    f"User {user_id} has {len(user_orders)} order(s) with expire_at indicating renewal. Sending mail"
                )

                await notifications.send_renew_order_message(
                    MAIL_MESSAGE_ORDER_RENEW_TITLE,
                    get_mail_message_order_renew(),
                    user_orders,
                )

                for order in user_orders:
                    await repository.insert_log_message(
                        crud,
                        user_id=SYSTEM_USER_ID,
                        order=order,
                        message=LOG_MESSAGES.RENEWAL_SENT,
                    )

                num_renewal_emails += 1
            except Exception:
                runtime.cron_log.exception(f"Failed to send renewal email for user {user_id}")

    return num_renewal_emails
