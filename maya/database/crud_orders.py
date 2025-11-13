"""
A collection of functions for performing CRUD operations on orders.
"""

from maya.core.dynamic_settings import settings
from maya.database.crud import CRUD
from maya.database import utils_orders
from maya.database.utils import DatabaseConnection
from maya.core.logging import get_log, get_custom_log
from dataclasses import dataclass
from typing import Optional
import json


log = get_log()
cron_log = get_custom_log("cron")


try:
    orders_url = settings["sqlite3"]["orders"]
except KeyError:
    orders_url = ""


@dataclass
class LogMessages:
    ORDER_CREATED: str = "Bestilling oprettet"
    ORDER_RENEWED: str = "Bestilling fornyet"
    STATUS_CHANGED: str = "Bruger status ændret"
    LOCATION_CHANGED: str = "Lokation ændret"
    MAIL_SENT: str = "Mail sendt"
    RENEWAL_SENT: str = "Mail fornyelse sendt"


LOG_MESSAGES = LogMessages()
SYSTEM_USER_ID = "SYSTEM"

MAIL_MESSAGE_ORDER_READY = """Du har bestilt et arkivalie til gennemsyn på Aarhus Stadsarkiv.
Materialet er tilgængeligt, og kan ses på studiepladser i Stadsarkivets Værksted på Dokk1."""
MAIL_MESSAGE_ORDER_READY_TITLE = "Din bestilling er klar til gennemsyn"
MAIL_MESSAGE_ORDER_RENEW = f"""Din bestilling har deadline om {utils_orders.DEADLINE_DAYS_RENEWAL} dage.<br>
Forny dit materiale på <a href="{settings.get("client_url", "")}/auth/orders/active">www.aarhusarkivet.dk</a>"""
MAIL_MESSAGE_ORDER_RENEW_TITLE = "Fornyelse af bestilling"


@dataclass
class OrderFilter:
    """
    OrderFilter for seach
    filter_status can be: active, completed, order_history
    """

    filter_status: str = "active"
    filter_location: Optional[str] = ""
    filter_email: Optional[str] = ""
    filter_user: Optional[str] = ""
    filter_show_queued: Optional[str] = ""
    filter_limit: int = 50
    filter_offset: int = 0

    # Pagination
    filter_has_next: bool = False
    filter_has_prev: bool = False
    filter_next_offset: int = 0
    filter_prev_offset: int = 0


async def has_active_order(user_id: str, record_id: str):
    """
    Check if user has an active order on a record
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        return await _has_active_order(crud, user_id, record_id)


async def is_owner(user_id: str, order_id: int):
    """
    Check if user is owner of order
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        filters = {"order_id": order_id, "user_id": user_id}
        is_owner = await crud.exists(
            table="orders",
            filters=filters,
        )

    return is_owner


async def replace_employee(me: dict):
    """
    Insert or update employee details
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        user_data = utils_orders.get_insert_user_data(me)
        await crud.replace("users", user_data, {"user_id": me["id"]})


async def _has_active_order(crud: "CRUD", user_id: str, record_id: str):
    """
    Check if user has an active order on a record
    """
    statuses = [utils_orders.ORDER_STATUS.ORDERED, utils_orders.ORDER_STATUS.QUEUED]
    order = await _get_orders_one(crud, statuses, record_id, user_id)
    return order


async def _is_renew_possible(crud: "CRUD", order: dict):
    """
    Check if an order can be renewed
    - Check if user status is ORDERED
    - Order has a expire_at date
    - Order has not passed expire_at
    - Check if no other order is in the queue in the same record
    """

    if not order["expire_at"]:
        return False

    days_remaining_ = utils_orders.get_days_until_expire(order)
    if days_remaining_ > utils_orders.DEADLINE_DAYS_RENEWAL:
        return False

    queued = await _get_orders_one(
        crud,
        record_id=order["record_id"],
        statuses=[utils_orders.ORDER_STATUS.QUEUED],
    )

    if queued:
        return False

    return True


async def renew_order(user_id: str, order_id: int):
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        order = await _get_orders_one(crud, order_id=order_id)

        if not await _is_renew_possible(crud, order):
            raise Exception(f"Bestilling {order_id} kan ikke fornyes")

        expire_at_date = utils_orders.get_expire_at_date()
        await crud.update(
            table="orders",
            update_values={"expire_at": expire_at_date},
            filters={"order_id": order_id},
        )

        # Log the renewal
        await _insert_log_message(
            crud,
            user_id=user_id,
            order=order,
            message=LOG_MESSAGES.ORDER_RENEWED,
        )


async def _save_data(meta_data: dict, record_and_types: dict, me: dict):

    # save meta_data, and record_and_types, me as JSON
    base_path = "tests/data"

    with open(f"{base_path}/meta_data_000495102.json", "w") as f:
        json.dump(meta_data, f, ensure_ascii=False)

    with open(f"{base_path}/record_and_types_000495102.json", "w") as f:
        json.dump(record_and_types, f, ensure_ascii=False)

    with open(f"{base_path}/me.json", "w") as f:
        json.dump(me, f, ensure_ascii=False)


async def insert_order(meta_data: dict, record_and_types: dict, me: dict):
    """
    Insert an order into the database with proper validations and updates.
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        # Check for active order by the user on the same record
        if await _has_active_order(crud, me["id"], meta_data["id"]):
            raise Exception("User is already active on this record")

        # Insert or update user details
        user_data = utils_orders.get_insert_user_data(me)
        await crud.replace("users", user_data, {"user_id": me["id"]})

        # Fetch or prepare record data
        record_db = await crud.select_one("records", filters={"record_id": meta_data["id"]})
        if record_db:
            record_data = utils_orders.get_insert_record_data(meta_data, record_and_types, record_db["location"])
        else:
            record_data = utils_orders.get_insert_record_data(meta_data, record_and_types)

        await crud.replace("records", record_data, {"record_id": meta_data["id"]})

        # Determine user status based on active orders for the record
        active_order = await _get_orders_one(crud, [utils_orders.ORDER_STATUS.ORDERED], meta_data["id"])
        order_status = utils_orders.ORDER_STATUS.QUEUED if active_order else utils_orders.ORDER_STATUS.ORDERED

        # Create new order data
        order_data = utils_orders.get_order_data(
            user_data["user_id"],
            record_data["record_id"],
            order_status,
        )

        await crud.insert("orders", order_data)

        # Retrieve the newly created order and log the creation
        last_order_id = await crud.last_insert_id()
        inserted_order = await _get_orders_one(crud, order_id=last_order_id)
        log_messages = [LOG_MESSAGES.ORDER_CREATED]

        # Handle special cases for orders already in the reading room and ordered
        if record_data["location"] == utils_orders.RECORD_LOCATION.READING_ROOM and order_status == utils_orders.ORDER_STATUS.ORDERED:

            expire_at = utils_orders.get_expire_at_date()
            inserted_order["expire_at"] = expire_at

            # Update order with expire_at and message status
            await crud.update(
                table="orders",
                update_values={"expire_at": expire_at, "message_sent": 1},
                filters={"order_id": inserted_order["order_id"]},
            )

            updated_order = await _get_orders_one(crud, order_id=inserted_order["order_id"])
            await utils_orders.send_order_message(MAIL_MESSAGE_ORDER_READY_TITLE, MAIL_MESSAGE_ORDER_READY, updated_order)
            log_messages.append(LOG_MESSAGES.MAIL_SENT)

        await _insert_log_message(
            crud,
            user_id=inserted_order["user_id"],
            order=inserted_order,
            message=". ".join(log_messages),
        )

        return inserted_order


async def _update_status(crud: "CRUD", user_id: str, order_id: int, new_status: int):
    """
    Updates the user status of an order. If the order's status is COMPLETED or DELETED, it checks for QUEUED orders
    on the same record. If found, updates the first QUEUED order to ORDERED and processes further actions.
    """
    order = await _get_orders_one(crud, order_id=order_id)
    if new_status == order["order_status"]:
        return

    await crud.update(
        table="orders",
        update_values={"order_status": new_status},
        filters={"order_id": order_id},
    )

    # Get the updated order
    order = await _get_orders_one(crud, order_id=order_id)
    if new_status in [utils_orders.ORDER_STATUS.COMPLETED, utils_orders.ORDER_STATUS.DELETED]:
        await _insert_log_message(
            crud,
            user_id,
            order,
            LOG_MESSAGES.STATUS_CHANGED,
        )

        next_queued_order = await _get_orders_one(crud, statuses=[utils_orders.ORDER_STATUS.QUEUED], record_id=order["record_id"])
        if next_queued_order:
            # Update the status of the next queued order to ORDERED
            await crud.update(
                table="orders",
                update_values={"order_status": utils_orders.ORDER_STATUS.ORDERED},
                filters={"order_id": next_queued_order["order_id"]},
            )
            log_messages = [LOG_MESSAGES.STATUS_CHANGED]

            if next_queued_order["location"] == utils_orders.RECORD_LOCATION.READING_ROOM:
                # Update the expire and send a message if the order is in the reading room
                log.info(f"Order {next_queued_order['order_id']} moved to READING_ROOM.")

                expire_at = utils_orders.get_expire_at_date()
                await crud.update(
                    table="orders",
                    update_values={"expire_at": expire_at, "message_sent": 1},
                    filters={"order_id": next_queued_order["order_id"]},
                )

                next_queued_order = await _get_orders_one(crud, order_id=next_queued_order["order_id"])
                await utils_orders.send_order_message(MAIL_MESSAGE_ORDER_READY_TITLE, MAIL_MESSAGE_ORDER_READY, next_queued_order)
                log_messages.append(LOG_MESSAGES.MAIL_SENT)

            # Log the status change
            await _insert_log_message(
                crud,
                user_id=user_id,
                order=next_queued_order,
                message=". ".join(log_messages),
            )


async def _update_location(crud: "CRUD", user_id: str, order_id: int, new_location: int):
    """
    Updates the location of a record.
    If the location changes to READING_ROOM, set the expire_at and sends a message.
    """
    order = await _get_orders_one(crud, order_id=order_id)
    if order["location"] == new_location:
        return

    # Update record location
    await _allow_location_change(crud, order["record_id"], raise_exception=True)
    record_update_values = {"location": new_location}
    await crud.update(
        table="records",
        update_values=record_update_values,
        filters={"record_id": order["record_id"]},
    )

    log_messages = [LOG_MESSAGES.LOCATION_CHANGED]

    # If the new location is the reading room, add expire_at and message_sent fields
    order_update_values: dict = {}
    order_update_values["updated_at"] = utils_orders.get_current_date_time()

    # If the order is in the reading room, set the expire_at and send a message
    if new_location == utils_orders.RECORD_LOCATION.READING_ROOM:
        order_update_values["expire_at"] = utils_orders.get_expire_at_date()

        if not order.get("message_sent"):
            await utils_orders.send_order_message(MAIL_MESSAGE_ORDER_READY_TITLE, MAIL_MESSAGE_ORDER_READY, order)
            order_update_values["message_sent"] = 1
            log_messages.append(LOG_MESSAGES.MAIL_SENT)

    # Perform update on the order
    await crud.update(
        table="orders",
        update_values=order_update_values,
        filters={"order_id": order_id},
    )

    updated_order = await _get_orders_one(crud, order_id=order_id)
    await _insert_log_message(
        crud,
        user_id=user_id,
        order=updated_order,
        message=". ".join(log_messages),
    )


async def _update_comment(crud: "CRUD", user_id: str, order_id: int, new_comment: str):
    update_values = {
        "comment": new_comment,
        "updated_at": utils_orders.get_current_date_time(),
    }
    await crud.update(
        table="orders",
        update_values=update_values,
        filters={"order_id": order_id},
    )


async def update_order(
    user_id: str,
    order_id: int,
    update_values: dict,
):
    """
    Updates an order's details (location, comment, and order_status)
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        # Only one of the following can be updated at a time
        comment = update_values.get("comment", "")
        order_status = update_values.get("order_status", 0)
        location = update_values.get("location", 0)
        expire_at = update_values.get("expire_at", "")

        # comment should also be updated if empty string
        if comment is not None:
            await _update_comment(crud, user_id, order_id, comment)

        if location:
            await _update_location(crud, user_id, order_id, location)

        elif order_status:
            await _update_status(crud, user_id, order_id, order_status)

        elif expire_at:
            """only used in tests"""
            update_values = {"expire_at": expire_at}
            await crud.update(
                table="orders",
                update_values=update_values,
                filters={"order_id": order_id},
            )


async def _get_queued_orders_length(crud: "CRUD", orders: list[dict]) -> dict:
    """
    From a list of order get the count of queued orders for each record in the list
    """
    records_ids = [order["record_id"] for order in orders]
    list_of_record_ids = ", ".join([f"'{record_id}'" for record_id in records_ids])

    # query for getting count of queued orders for any record in the list
    query = f"""
SELECT record_id, COUNT(*) AS queued_count
FROM orders
WHERE order_status IN ({utils_orders.ORDER_STATUS.QUEUED})
AND record_id IN ({list_of_record_ids})
GROUP BY record_id
ORDER BY queued_count DESC;
"""
    queued_orders = await crud.query(query, {})
    queued_orders_dict = {order["record_id"]: order["queued_count"] for order in queued_orders}

    return queued_orders_dict


async def get_orders_user(user_id: str, status: str = "active") -> list:
    """
    Get all orders for a user. Exclude orders with specific statuses.
    """
    database_connection = DatabaseConnection(orders_url)
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
    (o.order_status IN ({utils_orders.ORDER_STATUS.QUEUED})) OR
    (o.order_status IN ({utils_orders.ORDER_STATUS.ORDERED}) AND r.location <> {utils_orders.RECORD_LOCATION.READING_ROOM})
AND o.user_id = :user_id
ORDER BY o.order_id DESC
            """

        # Fetch the orders based on statuses
        orders = await crud.query(query, {"user_id": user_id})

        # Add renewal_possible and days_remaining to each order (utils_orders.)
        for order in orders:
            order["renewal_possible"] = await _is_renew_possible(
                crud,
                order=order,
            )
            order["days_remaining"] = utils_orders.get_days_until_expire(order)

        # Format each order for display
        orders = [utils_orders.format_order_display(order) for order in orders]
        orders = [utils_orders.format_order_display_user(order, status) for order in orders]

        return orders


def _get_and_filters_str_and_values(filters: OrderFilter) -> tuple:
    search_values = []
    search_filters = []
    if filters.filter_location:
        search_filters.append("r.location =:location_filter")
        search_values.append(filters.filter_location)
    if filters.filter_email:
        search_filters.append("u.user_email LIKE :email_filter")
        search_values.append(filters.filter_email)
    if filters.filter_user:
        search_filters.append("u.user_display_name LIKE :user_filter")
        search_values.append(filters.filter_user)

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


async def _get_active_orders(crud: "CRUD", filters: OrderFilter, offset: int = 0) -> list:
    search_filters_as_str, placeholder_values = _get_and_filters_str_and_values(filters)

    if filters.filter_show_queued:
        order_statuses = f"{utils_orders.ORDER_STATUS.ORDERED}, {utils_orders.ORDER_STATUS.QUEUED}"
    else:
        order_statuses = f"{utils_orders.ORDER_STATUS.ORDERED}"

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

    orders = await crud.query(query, placeholder_values)
    return orders


async def _get_completed_orders(crud: "CRUD", filters: OrderFilter, offset: int = 0) -> list:
    search_filters_as_str, placeholder_values = _get_and_filters_str_and_values(filters)
    query = f"""
SELECT o.*, r.*, u.*
FROM orders o
LEFT JOIN records r ON o.record_id = r.record_id
LEFT JOIN users u ON o.user_id = u.user_id
WHERE
    -- Only COMPLETED orders
    o.order_status IN ({utils_orders.ORDER_STATUS.COMPLETED}, {utils_orders.ORDER_STATUS.DELETED})

    -- Make sure we pick the most recent COMPLETED order for each record
    AND o.order_id = (
        SELECT o2.order_id
        FROM orders o2
        WHERE o2.record_id = o.record_id
          AND o2.order_status IN ({utils_orders.ORDER_STATUS.COMPLETED}, {utils_orders.ORDER_STATUS.DELETED})
        ORDER BY o2.updated_at DESC, o2.order_id DESC
        LIMIT 1
    )

    -- Exclude records that have an ORDERED status
    AND o.record_id NOT IN (
        SELECT record_id
        FROM orders
        WHERE order_status = {utils_orders.ORDER_STATUS.ORDERED}
    )

    -- Also exclude records with location = IN_STORAGE
    AND r.location <> {utils_orders.RECORD_LOCATION.IN_STORAGE}

    -- Search filters
    {search_filters_as_str}

ORDER BY o.updated_at DESC
LIMIT {filters.filter_limit} OFFSET {offset};

"""
    orders = await crud.query(query, placeholder_values)
    return orders


async def _get_history_orders(crud: "CRUD", filters: OrderFilter, offset: int = 0) -> list:
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
    orders = await crud.query(query, placeholder_values)
    return orders


async def get_orders_admin(filters: OrderFilter) -> tuple[list, OrderFilter]:
    """
    Get all orders for a user.
    """
    database_connection = DatabaseConnection(orders_url)
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

                # Only the first order in the list is 'ORDERED' and can be changed
                # if location is READING_ROOM set action_location_change to False
                if order["location"] != utils_orders.RECORD_LOCATION.READING_ROOM:
                    order["allow_location_change"] = True

            offset_next = offset + filters.filter_limit
            orders_next = await _get_active_orders(crud, filters, offset_next)

        if filters.filter_status == "completed":
            orders = await _get_completed_orders(crud, filters, offset)

            for order in orders:
                order = utils_orders.format_order_display(order)
                order["user_actions_deactivated"] = True
                order["allow_location_change"] = True

            offset_next = offset + filters.filter_limit
            orders_next = await _get_completed_orders(crud, filters, offset_next)

        if filters.filter_status == "order_history":
            orders = await _get_history_orders(crud, filters, offset)

            for order in orders:
                order = utils_orders.format_order_display(order)
                order["user_actions_deactivated"] = True
                order["allow_location_change"] = False

            offset_next = offset + filters.filter_limit
            orders_next = await _get_history_orders(crud, filters, offset_next)

        # Generate pagination
        has_next = bool(len(orders_next))
        if has_next:
            next_offset = filters.filter_offset + filters.filter_limit
        else:
            next_offset = 0

        has_prev = bool(filters.filter_offset > 0)
        if has_prev:
            prev_offset = filters.filter_offset - filters.filter_limit
        else:
            prev_offset = 0

        filters.filter_has_next = has_next
        filters.filter_has_prev = has_prev
        filters.filter_next_offset = next_offset
        filters.filter_prev_offset = prev_offset

        return orders, filters


async def get_order(order_id: int):
    """
    Get a single joined order by order_id for display on the admin edit order page
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        order = await _get_orders_one(CRUD(connection), order_id=order_id)
        order = utils_orders.format_order_display(order)
        allow_location_change = await _allow_location_change(CRUD(connection), order["record_id"])
        order["allow_location_change"] = allow_location_change
        return order


async def get_logs(order_id: int = 0) -> list:
    """
    Get a single joined order by order_id for display on the admin edit order page
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        sql = []
        values = {}
        if order_id:
            sql.append("l.order_id = :order_id")
            values = {"order_id": order_id}

        where_sql = ""
        if sql:
            where_sql = "WHERE " + " AND ".join(sql)
        query = f"""
SELECT * FROM orders_log l
JOIN orders o ON l.order_id = o.order_id
JOIN users u ON l.user_id = u.user_id
JOIN records r ON l.record_id = r.record_id
{where_sql}
ORDER BY l.log_id DESC
LIMIT 100
"""

        logs = await crud.query(query, values)
        for single_log in logs:
            single_log = utils_orders.format_log_display(single_log)
        return logs


async def get_order_by_record_id(user_id: str, record_id: str):
    """
    Get a single order by record_id
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        order = await _get_orders_one(CRUD(connection), user_id=user_id, record_id=record_id)
        return order


async def cron_orders_expire():
    """
    Check if expire has passed and update user status to COMPLETED
    """
    # Get orders where expire_at has passed
    cron_log.info("Starting cron_orders_expire")
    try:
        database_connection = DatabaseConnection(orders_url)
        async with database_connection.transaction_scope_async() as connection:
            crud = CRUD(connection)

            # Expire orders where expire_at has passed
            query = f"""
            SELECT * FROM orders
            WHERE expire_at IS NOT NULL
            AND expire_at < :current_date
            AND order_status = {utils_orders.ORDER_STATUS.ORDERED}"""

            params = {"current_date": utils_orders.get_current_date_time()}
            orders_expire = await crud.query(query, params)

            cron_log.info(f"Found {len(orders_expire)} orders to expire")
    except Exception:
        cron_log.exception("Failed to get orders for cron_orders")
        return

    for order in orders_expire:
        try:
            database_connection = DatabaseConnection(orders_url)
            async with database_connection.transaction_scope_async() as connection:
                crud = CRUD(connection)
                log.info(f"Order {order['order_id']} has passed expire_at. Setting status to COMPLETED")
                await _update_status(crud, SYSTEM_USER_ID, order["order_id"], utils_orders.ORDER_STATUS.COMPLETED)
        except Exception:
            log.exception(f"Failed to update order {order['order_id']} to COMPLETED")


async def cron_renewal_emails():

    cron_log.info("Starting cron_renewal_emails")
    try:
        database_connection = DatabaseConnection(orders_url)
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
            """
            params = {"expire_at": date_indicating_renewal}
            renewal_orders = await crud.query(query, params)
            cron_log.info(f"Found {len(renewal_orders)} orders with expire_at = {date_indicating_renewal}")

    except Exception:
        cron_log.exception("Cron renewal emails failed")
        return

    for order in renewal_orders:

        try:
            database_connection = DatabaseConnection(orders_url)
            async with database_connection.transaction_scope_async() as connection:
                crud = CRUD(connection)

                if not await _is_renew_possible(crud, order):
                    cron_log.info(f"Order {order['order_id']} could not be renewed")
                    continue

                cron_log.info(f"Order {order['order_id']} has expire_at indicating renewal. Sending mail")

                await utils_orders.send_order_message(MAIL_MESSAGE_ORDER_RENEW_TITLE, MAIL_MESSAGE_ORDER_RENEW, order)
                await _insert_log_message(
                    crud,
                    user_id=SYSTEM_USER_ID,
                    order=order,
                    message=LOG_MESSAGES.RENEWAL_SENT,
                )
        except Exception:
            cron_log.exception(f"Failed to send renewal email for order {order['order_id']}")


async def _get_orders(
    crud: "CRUD",
    statuses: list = [],
    record_id: str = "",
    user_id: str = "",
    order_id: int = 0,
    location: int = 0,
    order_by: str = "o.order_id DESC",
    limit: int = 100,
):
    query, params = await _get_orders_query_params(
        statuses,
        record_id,
        user_id,
        order_id,
        location,
        order_by,
        limit,
    )

    result = await crud.query(query, params)
    return result


async def _get_orders_one(
    crud: "CRUD",
    statuses: list = [],
    record_id: str = "",
    user_id: str = "",
    order_id: int = 0,
    location: int = 0,
    order_by: str = "o.order_id DESC",
    limit: int = 1,
):
    """
    Get a single order
    """
    query, params = await _get_orders_query_params(
        statuses,
        record_id,
        user_id,
        order_id,
        location,
        order_by,
        limit,
    )
    order = await crud.query_one(query, params)
    return order


async def _get_orders_query_params(
    statuses: list = [],
    record_id: str = "",
    user_id: str = "",
    order_id: int = 0,
    location: int = 0,
    order_by: str = "o.order_id DESC",
    limit: int = 0,
):
    """
    SELECT complete order data by statuses, record_id, user_id, order_id
    Returns query and params
    """
    where_clauses = []
    params: dict = {}

    if statuses:
        statuses_str = ", ".join([str(status) for status in statuses])
        where_clauses.append(f"o.order_status IN ({statuses_str})")

    if record_id:
        where_clauses.append("r.record_id = :record_id")
        params["record_id"] = record_id

    if user_id:
        where_clauses.append("o.user_id = :user_id")
        params["user_id"] = user_id

    if order_id:
        where_clauses.append("o.order_id = :order_id")
        params["order_id"] = order_id

    if location:
        where_clauses.append("r.location = :location")
        params["location"] = location

    query = """
    SELECT * FROM orders o
    LEFT JOIN records r ON o.record_id = r.record_id
    LEFT JOIN users u ON o.user_id = u.user_id
    """

    if where_clauses:
        query += "WHERE " + " AND ".join(where_clauses) + " "

    if order_by:
        query += f"ORDER BY {order_by} "

    if limit:
        query += f"LIMIT {limit} "

    return query, params


async def _allow_location_change(crud: "CRUD", record_id: str, raise_exception=False):
    """
    Check if location can be changed
    Get orders where location is READING_ROOM and order_status is ORDERED
    If there are no orders then location can be changed
    """
    orders = await _get_orders(
        crud,
        statuses=[utils_orders.ORDER_STATUS.ORDERED],
        location=utils_orders.RECORD_LOCATION.READING_ROOM,
        record_id=record_id,
    )
    if orders:
        if raise_exception:
            raise Exception(f"Lokation kan ikke ændres. Der er allerede en bestilling med record_id {record_id} i læsesalen")
        return False
    return True


async def _insert_log_message(
    crud: "CRUD",
    user_id: str,
    order: dict,
    message: str,
):
    log_message = {
        "user_id": user_id,
        "order_id": order["order_id"],
        "record_id": order["record_id"],
        "updated_location": order["location"],
        "updated_order_status": order["order_status"],
        "message": message,
    }

    """
    order_id=order_id,
    record_id=updated_order["record_id"],
    location=updated_order["location"],
    order_status=updated_order["order_status"],
    """

    await crud.insert("orders_log", log_message)
