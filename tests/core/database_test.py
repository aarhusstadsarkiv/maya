import asyncio
from maya.core.dynamic_settings import init_settings
from maya.core.logging import get_log
import unittest
from maya.core.migration import Migration
from maya.migrations.tests import migrations_tests
from maya.database import crud, utils
import os

init_settings()
log = get_log()


class TestDB(unittest.TestCase):

    def test_migrations(self):
        db_path = ":memory:"
        migration = Migration(db_path=db_path, migrations=migrations_tests)
        migration.run_migrations()

    def test_crud(self):
        asyncio.run(self._test_crud_async())

    async def _test_crud_async(self):

        db_path = "/tmp/test.db"

        # remove db_path
        if os.path.exists(db_path):
            os.remove(db_path)

        migration = Migration(db_path=db_path, migrations=migrations_tests)
        migration.run_migrations()

        database_transaction = utils.DatabaseConnection(db_path)
        async with database_transaction.write_transaction_scope_async() as connection:
            crud_instance = crud.CRUD(connection)

            # Insert a user
            user_data = {"user_id": "1", "user_email": "test@example.com", "user_display_name": "Test User"}
            await crud_instance.insert("users", user_data)

            # Check if user exists
            self.assertTrue(await crud_instance.exists("users", {"user_id": "1"}))

            # Select the user
            user = await crud_instance.select_one("users", ["user_id", "user_email", "user_display_name"], {"user_id": "1"})
            self.assertEqual(user["user_email"], "test@example.com")

            # Update the user
            updated_data = {"user_display_name": "Updated User"}
            await crud_instance.update("users", updated_data, {"user_id": "1"})

            # Check if the update was successful
            updated_user = await crud_instance.select_one("users", ["user_display_name"], {"user_id": "1"})
            self.assertEqual(updated_user["user_display_name"], "Updated User")

            # Count users
            count = await crud_instance.count("users", {})
            self.assertEqual(count, 1)

            # Delete the user
            await crud_instance.delete("users", {"user_id": "1"})
            self.assertFalse(await crud_instance.exists("users", {"user_id": "1"}))

            # Insert multiple users
            users_data = [
                {"user_id": "2", "user_email": "user2@example.com", "user_display_name": "User Two"},
                {"user_id": "3", "user_email": "user3@example.com", "user_display_name": "User Three"},
            ]
            await crud_instance.insert_many("users", users_data)

            # Select multiple users
            users = await crud_instance.select("users", ["user_id", "user_email"], {}, order_by=[("user_id", "desc")], limit_offset=(10, 0))
            self.assertEqual(len(users), 2)

            # Query with a raw SQL statement
            queried_users = await crud_instance.query("SELECT * FROM users WHERE user_email LIKE :email", {"email": "%@example.com"})
            self.assertEqual(len(queried_users), 2)

            # Query single row
            queried_user = await crud_instance.query_one("SELECT * FROM users WHERE user_id = :id", {"id": "2"})
            self.assertEqual(queried_user["user_display_name"], "User Two")

    def test_transaction_failure(self):
        asyncio.run(self._test_crud_async_transaction_failure())

    async def _test_crud_async_transaction_failure(self):
        """
        Test if the transaction is auto rolled back if an exception is raised.
        """

        db_path = "/tmp/test.db"

        # remove db_path
        if os.path.exists(db_path):
            os.remove(db_path)

        migration = Migration(db_path=db_path, migrations=migrations_tests)
        migration.run_migrations()

        try:
            database_transaction = utils.DatabaseConnection(db_path)
            async with database_transaction.write_transaction_scope_async() as connection:
                crud_instance = crud.CRUD(connection)

                # Insert multiple users
                users_data = [
                    {"user_id": "2", "user_email": "user2@example.com", "user_display_name": "User Two"},
                    {"user_id": "3", "user_email": "user3@example.com", "user_display_name": "User Three"},
                ]
                await crud_instance.insert_many("users", users_data)
                raise Exception("Test exception")
        except Exception:
            pass

        # Check num users
        async with database_transaction.transaction_scope_async() as connection:
            crud_instance = crud.CRUD(connection)
            count = await crud_instance.count("users", {})
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
