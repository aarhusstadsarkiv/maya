"""Refresh material snapshots without changing order workflow state."""

from starlette.requests import Request

from maya.core import api, api_client
from maya.database.crud import CRUD
from maya.database.utils import DatabaseConnection
from maya.endpoints.endpoints_utils import get_record_data
from maya.orders import runtime, utils_orders


async def fetch_record_data(client, record_id: str) -> tuple[dict, dict]:
    # Use the same proxy endpoint as order creation, bypassing the page cache.
    response = await client.get(
        api.base_url + "/proxy/records/" + record_id,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    record = response.json()
    if record.get("id") != record_id:
        raise ValueError(f"Unexpected material ID when refreshing {record_id}")
    request = Request({"type": "http", "method": "GET", "path": f"/records/{record_id}", "headers": [], "session": {}})
    _, meta_data, record_and_types = await get_record_data(request, record)
    if meta_data.get("id") != record_id:
        raise ValueError(f"Unexpected metadata ID when refreshing {record_id}")
    return meta_data, record_and_types


async def cron_refresh_records() -> dict[str, int]:
    """Refresh each local material once, including materials used by historical orders.

    Fetch outside write transactions. A failed fetch or conversion leaves the
    previous snapshot intact and does not prevent other materials being updated.
    """
    runtime.cron_log.info("Starting cron_refresh_records")
    database = DatabaseConnection(runtime.orders_url)
    async with database.transaction_scope_async() as connection:
        records = await CRUD(connection).select("records", columns=["record_id"])

    result = {"updated": 0, "failed": 0}
    async with api_client.get_async_client() as client:
        for record in records:
            record_id = record["record_id"]
            try:
                meta_data, record_and_types = await fetch_record_data(client, record_id)
                values = utils_orders.get_insert_record_data(meta_data, record_and_types)
                # Never overwrite a location changed by staff during the fetch.
                del values["location"]
                del values["record_id"]
                async with database.write_transaction_scope_async() as connection:
                    await CRUD(connection).update("records", values, {"record_id": record_id})
                result["updated"] += 1
            except Exception:
                result["failed"] += 1
                runtime.cron_log.exception("Failed to refresh material %s", record_id)

    runtime.cron_log.info("Materials refreshed: %s; failed: %s", result["updated"], result["failed"])
    return result
