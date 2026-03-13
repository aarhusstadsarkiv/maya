import json
import typing

from maya.core.dynamic_settings import settings
from maya.database.cache import DatabaseCache
from maya.database.crud_default import database_url
from maya.database.utils import DatabaseConnection


def _get_proxy_cache_expire() -> typing.Optional[int]:
    proxy_cache_expire = settings.get("proxy_cache_expire")
    if proxy_cache_expire is None:
        return None

    if not isinstance(proxy_cache_expire, int):
        raise TypeError("settings['proxy_cache_expire'] must be an int")

    return proxy_cache_expire


PROXY_CACHE_EXPIRE = _get_proxy_cache_expire()
database_connection = DatabaseConnection(database_url)


async def proxy_cache_get(key: str) -> typing.Any:
    if not database_url or PROXY_CACHE_EXPIRE is None:
        return None

    async with database_connection.transaction_scope_async() as connection:
        database_cache = DatabaseCache(connection)
        return await database_cache.get(key, expire_in=PROXY_CACHE_EXPIRE)


async def proxy_cache_set(key: str, data: typing.Any) -> None:
    if not database_url or PROXY_CACHE_EXPIRE is None:
        return None

    async with database_connection.transaction_scope_async() as connection:
        database_cache = DatabaseCache(connection)
        await database_cache.set(key, data)


def proxy_record_cache_key(record_id: str) -> str:
    return f"proxy_record:{record_id}"


def proxy_records_cache_key(query_params_before_search: list) -> str:
    normalized_params = [[str(key), str(value)] for key, value in query_params_before_search]
    return "proxy_records:" + json.dumps(normalized_params, sort_keys=False, separators=(",", ":"))
