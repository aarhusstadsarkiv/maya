"""
Simple sqlite3 cache implementation
Example usage:

```
async def test_get(request: Request):

    insert_value = None
    # Get a result that is max 10 seconds old
    cache_expire = 10
    has_result = False

    async with crud_default.transaction_scope() as connection:
        cache = DatabaseCache(connection)
        result = await cache.get("test", cache_expire)

        if not result:
            # Set a new cache value
            insert_value = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
            await cache.set("test", {"random": insert_value})
        else:
            has_result = True

    return JSONResponse(
        {
            "message": "Test note inserted",
            "result": result,
            "has_result": has_result,
            "expire": cache_expire,
            "inserted_value": insert_value,
        }
    )
```
"""

import aiosqlite
import json
import time
from typing import Any


class DatabaseCache:
    def __init__(self, connection: aiosqlite.Connection):
        """
        Initialize the DatabaseCache with a connection.
        The connection is expected to be managed externally (e.g., with async with).
        """
        self.connection = connection

    async def set(self, key: str, data: Any) -> bool:
        """
        Set a cache value for a key using a single-row upsert.
        """
        json_data = json.dumps(data)
        await self.connection.execute(
            """
            INSERT INTO cache (key, value, unix_timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                unix_timestamp = excluded.unix_timestamp
            """,
            (key, json_data, int(time.time())),
        )
        return True

    async def get(self, key: str, expire_in: int = 0) -> Any:
        """
        Will return the value if the key exists and is not expired.
        Will return None if the key does not exist or if the key is expired.
        If expire_in is 0, the value will never expire.
        """
        cursor = await self.connection.execute(
            "SELECT id, value, unix_timestamp FROM cache WHERE key = ?",
            (key,),
        )
        result = await cursor.fetchone()

        if result:
            if expire_in == 0:
                return json.loads(result["value"])

            current_time = int(time.time())
            if current_time - result["unix_timestamp"] < expire_in:
                return json.loads(result["value"])
            await self.connection.execute("DELETE FROM cache WHERE key = ?", (key,))
        return None

    async def delete(self, id: int) -> None:
        """
        Delete a cache value by id
        """
        await self.connection.execute("DELETE FROM cache WHERE id = ?", (id,))
        return None

    async def delete_expired(self, expire_in: int) -> int:
        """
        Delete cache values older than the provided TTL.
        """
        if expire_in <= 0:
            return 0

        cutoff = int(time.time()) - expire_in
        cursor = await self.connection.execute(
            "DELETE FROM cache WHERE unix_timestamp <= ?",
            (cutoff,),
        )
        return cursor.rowcount
