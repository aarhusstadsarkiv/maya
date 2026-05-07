"""
This module contains utility functions for working with SQLite databases.

The functions in this module are used to create a transaction scope to ensure that all operations are atomic.
If a query fails, the transaction is rolled back and an exception is raised. Otherwise, the transaction is committed.

Example usage:

```
from maya.database.utils import DatabaseTransaction

database_url = settings["sqlite3"]["default"]
database_transation = DatabaseTransaction(database_url)
transaction_scope = database_transation.transaction_scope

async def delete_user(user_id: int):
    async with transaction_scope_async() as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.execute("INSERT INTO deleted_user_log (user_id, message) VALUES (?, ?)", (user_id, "User deleted"))

async def get_user(user_id: int):
    async with transaction_scope_async() as connection:
        cursor = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return user
```
"""

import sqlite3
import aiosqlite
from contextlib import asynccontextmanager, contextmanager
from maya.core.logging import get_log

log = get_log()

SQLITE_BUSY_TIMEOUT_MS = 30_000
SQLITE_CONNECTION_TIMEOUT_SECONDS = SQLITE_BUSY_TIMEOUT_MS / 1000
SQLITE_CONNECTION_PRAGMAS = (
    "PRAGMA journal_mode=WAL;",
    f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};",
    "PRAGMA synchronous=NORMAL;",
)


class DatabaseConnection:
    def __init__(self, database_url):
        self.database_url = database_url

    def get_db_connection_sync(self) -> sqlite3.Connection:
        """
        Create a synchronous database connection.
        """
        connection = sqlite3.connect(
            self.database_url,
            timeout=SQLITE_CONNECTION_TIMEOUT_SECONDS,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        self._configure_sync_connection(connection)
        return connection

    def _configure_sync_connection(self, connection: sqlite3.Connection) -> None:
        for pragma in SQLITE_CONNECTION_PRAGMAS:
            connection.execute(pragma)

    @contextmanager
    def transaction_scope_sync(self):
        """
        Synchronous deferred transaction scope context manager.
        """
        with self._transaction_scope_sync("BEGIN") as connection:
            yield connection

    @contextmanager
    def write_transaction_scope_sync(self):
        """
        Synchronous write transaction scope context manager.
        """
        with self._transaction_scope_sync("BEGIN IMMEDIATE") as connection:
            yield connection

    @contextmanager
    def _transaction_scope_sync(self, begin_statement):
        """
        Synchronous transaction scope context manager.
        """
        if not self.database_url:
            raise ValueError("Database URL was not set")

        connection = self.get_db_connection_sync()
        try:
            connection.execute(begin_statement)
            yield connection
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    async def get_db_connection_async(self) -> aiosqlite.Connection:
        """
        Create an asynchronous database connection.
        """
        if not self.database_url:
            raise ValueError("Database URL was not set")

        connection = await aiosqlite.connect(
            self.database_url,
            timeout=SQLITE_CONNECTION_TIMEOUT_SECONDS,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        await self._configure_async_connection(connection)
        return connection

    async def _configure_async_connection(self, connection: aiosqlite.Connection) -> None:
        for pragma in SQLITE_CONNECTION_PRAGMAS:
            await connection.execute(pragma)

    @asynccontextmanager
    async def transaction_scope_async(self):
        """
        Asynchronous deferred transaction scope context manager.
        """
        async with self._transaction_scope_async("BEGIN") as connection:
            yield connection

    @asynccontextmanager
    async def write_transaction_scope_async(self):
        """
        Asynchronous write transaction scope context manager.
        """
        async with self._transaction_scope_async("BEGIN IMMEDIATE") as connection:
            yield connection

    @asynccontextmanager
    async def _transaction_scope_async(self, begin_statement):
        """
        Asynchronous transaction scope context manager.
        """
        connection = await self.get_db_connection_async()
        try:
            await connection.execute(begin_statement)
            yield connection
            await connection.commit()
        except (sqlite3.Error, aiosqlite.Error):
            await connection.rollback()
            raise
        except Exception:
            await connection.rollback()
            raise
        finally:
            await connection.close()
