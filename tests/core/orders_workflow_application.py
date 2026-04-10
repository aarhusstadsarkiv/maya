import os
import asyncio
import json
import tempfile
import unittest

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.core.dynamic_settings import init_settings
from maya.core.logging import get_log
from maya.core.migration import Migration
from maya.migrations.orders import migrations_orders
from maya.database import crud_orders
from maya.database import utils_orders

init_settings()
log = get_log()


class TestDB(unittest.TestCase):

    def get_db_path(self) -> str:
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(db_path)
        crud_orders.orders_url = db_path
        return db_path

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
        db_path = self.get_db_path()
        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, me_2, meta_data, record_and_types = self.get_test_data_application()
        original_send_ready_orders_message = utils_orders.send_ready_orders_message

        async def _send_ready_orders_message_stub(*args, **kwargs):
            return None

        utils_orders.send_ready_orders_message = _send_ready_orders_message_stub

        try:
            await crud_orders.insert_order(meta_data, record_and_types, me)
            await crud_orders.insert_order(meta_data, record_and_types, me_2)
            logs = await crud_orders.get_logs(1)
            self.assertIn("Bestilling oprettet", logs[0]["message"])

            order = await crud_orders.get_order(1)
            self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.APPLICATION)

            orders_filter = crud_orders.OrderFilter(filter_status="active")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 2)

            await crud_orders.update_order(
                me["id"],
                order["order_id"],
                {"location": utils_orders.RECORD_LOCATION.READING_ROOM},
            )

            logs = await crud_orders.get_logs(1)
            self.assertIn("Lokation ændret", logs[0]["message"])

            order = await crud_orders.get_order(1)
            self.assertIsNone(order["expire_at"])

            await crud_orders.promote_application_order(me["id"], order["order_id"])
            order = await crud_orders.get_order(1)
            self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.ORDERED)
            self.assertIsNotNone(order["expire_at"])

            logs = await crud_orders.get_logs(1)
            self.assertIn("Mail sendt", logs[0]["message"])
            self.assertIn("Bruger status ændret", logs[1]["message"])
            self.assertEqual(len(logs), 4)

            with self.assertRaises(Exception) as cm:
                await crud_orders.insert_order(meta_data, record_and_types, me)
            self.assertIn("User is already active on this record", str(cm.exception))

            has_active_order = await crud_orders.has_active_order(me["id"], meta_data["id"])
            self.assertTrue(has_active_order)

            logs_2 = await crud_orders.get_logs(2)
            self.assertIn("Bestilling oprettet", logs_2[0]["message"])

            order_2 = await crud_orders.get_order(2)
            await crud_orders.promote_application_order(me_2["id"], order_2["order_id"])
            order_2 = await crud_orders.get_order(2)
            self.assertEqual(order_2["order_status"], utils_orders.ORDER_STATUS.QUEUED)

            orders_filter = crud_orders.OrderFilter(filter_status="active", filter_show_queued="on")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 2)

            orders_filter = crud_orders.OrderFilter(filter_status="order_history")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 0)

            orders_filter = crud_orders.OrderFilter(filter_status="active")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 1)

            await crud_orders.update_order(
                me["id"],
                order["order_id"],
                {"order_status": utils_orders.ORDER_STATUS.COMPLETED},
            )

            order = await crud_orders.get_order(1)
            self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.COMPLETED)

            logs = await crud_orders.get_logs(1)
            self.assertEqual(utils_orders.ORDER_STATUS.COMPLETED, logs[0]["order_status"])

            order_2 = await crud_orders.get_order(2)
            self.assertEqual(order_2["order_status"], utils_orders.ORDER_STATUS.ORDERED)

            logs_2 = await crud_orders.get_logs(2)
            self.assertIn("Mail sendt", logs_2[0]["message"])
            self.assertIn("Bruger status ændret", logs_2[1]["message"])

            orders_filter = crud_orders.OrderFilter(filter_status="active", filter_show_queued="on")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 1)

            orders_filter = crud_orders.OrderFilter(filter_status="completed")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 0)

            orders_filter = crud_orders.OrderFilter(filter_status="order_history")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 1)

            await crud_orders.update_order(
                me_2["id"],
                order_2["order_id"],
                {"order_status": utils_orders.ORDER_STATUS.COMPLETED},
            )

            orders_filter = crud_orders.OrderFilter(filter_status="active", filter_show_queued="on")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 0)

            orders_filter = crud_orders.OrderFilter(filter_status="completed")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 1)

            orders_filter = crud_orders.OrderFilter(filter_status="order_history")
            orders, _ = await crud_orders.get_orders_admin(filters=orders_filter)
            self.assertEqual(len(orders), 2)
        finally:
            utils_orders.send_ready_orders_message = original_send_ready_orders_message


if __name__ == "__main__":
    unittest.main()
