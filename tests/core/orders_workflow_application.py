import asyncio
from maya.core.dynamic_settings import init_settings
from maya.core.logging import get_log
import unittest
from maya.core.migration import Migration
from maya.migrations.orders import migrations_orders
import os
from maya.database import crud_orders
from maya.database import utils_orders
import json

init_settings()
log = get_log()


class TestDB(unittest.TestCase):

    def get_test_data_application(self):

        # Load user, meta_data and record_and_types - test data
        me_data_file = "tests/data/me.json"
        with open(me_data_file) as f:
            me = json.load(f)

        # Generate a second user
        me_2 = me.copy()
        me_2["id"] = "ANOTHER_USER_ID"
        me_2["email"] = "another.email@example.com"

        meta_data_file = "tests/data/meta_data_000495102.json"
        with open(meta_data_file) as f:
            meta_data = json.load(f)

        record_and_types_file = "tests/data/record_and_types_000495102.json"
        with open(record_and_types_file) as f:
            record_and_types = json.load(f)

        return me, me_2, meta_data, record_and_types

    def test_insert_application_order(self):
        asyncio.run(self._test_order_application_workflow())

    async def _test_order_application_workflow(self):
        """
        Simple integration test for orders
        """

        # Generate a new database for testing
        db_path = "/tmp/orders.db"
        if os.path.exists(db_path):
            os.remove(db_path)

        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, me_2, meta_data, record_and_types = self.get_test_data_application()
        # Test insert_order
        await crud_orders.insert_order(meta_data, record_and_types, me)

        order = await crud_orders.get_order(1)
        self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.APPLICATION)

        update_values = {"location": utils_orders.RECORD_LOCATION.READING_ROOM}
        await crud_orders.update_order(
            me["id"],
            order["order_id"],
            update_values,
        )

        # Order should now have an expire_at
        order = await crud_orders.get_order(1)
        self.assertIsNone(order["expire_at"])

        # promote application to order
        await crud_orders.promote_application_order(me["id"], order["order_id"])
        order = await crud_orders.get_order(1)
        self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.ORDERED)

        with self.assertRaises(Exception) as cm:
            await crud_orders.insert_order(meta_data, record_and_types, me)

        self.assertIn("User is already active on this record", str(cm.exception))
        # Test that application order can be updated to ordered

        # Test has_active_order again with the new order
        has_active_order = await crud_orders.has_active_order(me["id"], meta_data["id"])
        self.assertTrue(has_active_order)

        # application are displayed as active orders
        orders_filter = crud_orders.OrderFilter(filter_status="active")
        orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
        self.assertEqual(len(orders), 1)

        # Test correct amount of log messages. One line for inserting and one for promoting the application to an order
        logs = await crud_orders.get_logs(1)
        self.assertEqual(len(logs), 3)

        # Test that log messages are correct
        # last thing is that the order was promoted to an order so "status" has changed
        self.assertIn("Bruger status ændret", logs[0]["message"])

        # Update location to reading room


if __name__ == "__main__":
    unittest.main()
