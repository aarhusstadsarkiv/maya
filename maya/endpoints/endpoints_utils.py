"""
Utils for endpoints.
"""

from starlette.requests import Request
from maya.core.logging import get_log
from maya.core.hooks import get_hooks
from maya.records import record_alter
from maya.records.meta_data_record import get_record_meta_data
from maya.core.object_storage import set_presigned_urls_record
from maya.core.dynamic_settings import settings
import typing


log = get_log()


async def get_record_data(request: Request, record: dict) -> typing.Tuple[dict, dict, dict]:
    """
    A mutated record is returned. In order to keep the original record make a copy before using this function.
    """
    hooks = get_hooks(request)

    if settings.get("boto3_presigned_urls", False):
        record = await set_presigned_urls_record(record)

    meta_data = await get_record_meta_data(request, record)
    record, meta_data = await hooks.after_get_record(record, meta_data)

    record_altered = record_alter.record_alter(request, record, meta_data)
    record_and_types = record_alter.get_record_and_types(record_altered)

    record, record_and_types = await hooks.after_get_record_and_types(record, record_and_types)

    return record, meta_data, record_and_types
