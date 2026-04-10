from maya.database import utils_orders
from maya.records.meta_data_record import is_orderable_by_form


async def get_order_one(
    crud,
    statuses: list = [],
    record_id: str = "",
    user_id: str = "",
    order_id: int = 0,
    location: int = 0,
    order_by: str = "o.order_id DESC",
    limit: int = 1,
):
    query, params = await _get_orders_query_params(
        statuses=statuses,
        record_id=record_id,
        user_id=user_id,
        order_id=order_id,
        location=location,
        order_by=order_by,
        limit=limit,
    )
    return await crud.query_one(query, params)


async def get_orders_query(
    crud,
    statuses: list = [],
    record_id: str = "",
    user_id: str = "",
    order_id: int = 0,
    location: int = 0,
    order_by: str = "o.order_id DESC",
    limit: int = 100,
):
    query, params = await _get_orders_query_params(
        statuses=statuses,
        record_id=record_id,
        user_id=user_id,
        order_id=order_id,
        location=location,
        order_by=order_by,
        limit=limit,
    )
    return await crud.query(query, params)


async def _get_orders_query_params(
    statuses: list = [],
    record_id: str = "",
    user_id: str = "",
    order_id: int = 0,
    location: int = 0,
    order_by: str = "o.order_id DESC",
    limit: int = 0,
):
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


async def insert_log_message(crud, user_id: str, order: dict, message: str):
    log_message = {
        "user_id": user_id,
        "order_id": order["order_id"],
        "record_id": order["record_id"],
        "updated_location": order["location"],
        "updated_order_status": order["order_status"],
        "message": message,
    }
    await crud.insert("orders_log", log_message)


async def allow_location_change(crud, record_id: str, raise_exception: bool = False):
    orders = await get_orders_query(
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


async def has_active_order_on_record(crud, user_id: str, record_id: str):
    statuses = [utils_orders.ORDER_STATUS.ORDERED, utils_orders.ORDER_STATUS.QUEUED, utils_orders.ORDER_STATUS.APPLICATION]
    return await get_order_one(crud, statuses=statuses, record_id=record_id, user_id=user_id)


async def update_user_record_data(crud, meta_data: dict, record_and_types: dict, me: dict):
    user_data = utils_orders.get_insert_user_data(me)
    await crud.replace("users", user_data, {"user_id": me["id"]})

    record_db = await crud.select_one("records", filters={"record_id": meta_data["id"]})
    if record_db:
        record_data = utils_orders.get_insert_record_data(meta_data, record_and_types, record_db["location"])
    else:
        record_data = utils_orders.get_insert_record_data(meta_data, record_and_types)

    await crud.replace("records", record_data, {"record_id": meta_data["id"]})


async def get_insert_order_status(crud, meta_data: dict) -> int:
    active_order = await get_order_one(crud, [utils_orders.ORDER_STATUS.ORDERED], meta_data["id"])
    if is_orderable_by_form(meta_data):
        return utils_orders.ORDER_STATUS.APPLICATION
    if active_order:
        return utils_orders.ORDER_STATUS.QUEUED
    return utils_orders.ORDER_STATUS.ORDERED


async def get_logs(crud, order_id: int = 0, limit: int = 100, offset: int = 0) -> list:
    sql = []
    values = {}
    if order_id:
        sql.append("l.order_id = :order_id")
        values["order_id"] = order_id

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
LIMIT :limit
OFFSET :offset
"""

    values["limit"] = limit
    values["offset"] = offset
    return await crud.query(query, values)


async def get_orders_user_count(crud, user_id: str) -> int:
    query = """
    SELECT COUNT(*) AS num_rows
    FROM orders
    WHERE user_id = :user_id
      AND order_status IN (:status_ordered, :status_queued, :status_application)
    """

    row = await crud.query_one(
        query,
        {
            "user_id": user_id,
            "status_ordered": utils_orders.ORDER_STATUS.ORDERED,
            "status_queued": utils_orders.ORDER_STATUS.QUEUED,
            "status_application": utils_orders.ORDER_STATUS.APPLICATION,
        },
    )
    return row["num_rows"]
