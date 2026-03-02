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

        # Test insert_order application order. Both order that same record, but different users
        await crud_orders.insert_order(meta_data, record_and_types, me)
        await crud_orders.insert_order(meta_data, record_and_types, me_2)

        logs = await crud_orders.get_logs(1)
        self.assertIn("Bestilling oprettet", logs[0]["message"])

        order = await crud_orders.get_order(1)
        self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.APPLICATION)

        # application are displayed as active orders
        orders_filter = crud_orders.OrderFilter(filter_status="active")
        orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
        self.assertEqual(len(orders), 2)

        # Set location to reading room
        update_values = {"location": utils_orders.RECORD_LOCATION.READING_ROOM}
        await crud_orders.update_order(
            me["id"],
            order["order_id"],
            update_values,
        )

        # Check that the location was updated and logged correctly
        logs = await crud_orders.get_logs(1)
        self.assertIn("Lokation ændret", logs[0]["message"])

        # Order should NOT have an expire_at date when it's an application order
        order = await crud_orders.get_order(1)
        self.assertIsNone(order["expire_at"])

        # promote application to order
        await crud_orders.promote_application_order(me["id"], order["order_id"])

        # Order should now have status "ordered"
        order = await crud_orders.get_order(1)
        self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.ORDERED)

        logs = await crud_orders.get_logs(1)
        self.assertIn("Bruger status ændret. Mail sendt", logs[0]["message"])

        # Test correct amount of log messages. One line for inserting and one for promoting the application to an order
        logs = await crud_orders.get_logs(1)
        self.assertEqual(len(logs), 3)

        # Check that the user cannot add another order for the same record.
        with self.assertRaises(Exception) as cm:
            await crud_orders.insert_order(meta_data, record_and_types, me)
        self.assertIn("User is already active on this record", str(cm.exception))

        # Test has_active_order again with the new order
        has_active_order = await crud_orders.has_active_order(me["id"], meta_data["id"])
        self.assertTrue(has_active_order)

        logs = await crud_orders.get_logs(2)
        self.assertIn("Bestilling oprettet", logs[0]["message"])

        # promte second application to order
        order_2 = await crud_orders.get_order(2)
        await crud_orders.promote_application_order(me_2["id"], order_2["order_id"])

        # order_2 should now have status "queued"
        order_2 = await crud_orders.get_order(2)
        self.assertEqual(order_2["order_status"], utils_orders.ORDER_STATUS.QUEUED)

        # Change order 1 user status to completed
        update_values = {"order_status": utils_orders.ORDER_STATUS.COMPLETED}
        await crud_orders.update_order(
            me["id"],
            order["order_id"],
            update_values,
        )

        # get order_1 again and check that status is completed
        order = await crud_orders.get_order(1)
        self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.COMPLETED)

        # check last log status is ORDER_STATUS.COMPLETED
        logs = await crud_orders.get_logs(1)
        self.assertEqual(utils_orders.ORDER_STATUS.COMPLETED, logs[0]["order_status"])

        # Order 2 should now be active since order 1 is completed
        order_2 = await crud_orders.get_order(2)
        self.assertEqual(order_2["order_status"], utils_orders.ORDER_STATUS.ORDERED)

        logs_2 = await crud_orders.get_logs(2)
        self.assertIn("Bruger status ændret. Mail sendt", logs_2[0]["message"])


if __name__ == "__main__":
    unittest.main()
