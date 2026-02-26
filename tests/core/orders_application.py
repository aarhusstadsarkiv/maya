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

        # promote application to order
        await crud_orders.promote_application_order(me["id"], order["order_id"])
        order = await crud_orders.get_order(1)
        self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.ORDERED)

        # Test that application order can be updated to ordered


if __name__ == "__main__":
    unittest.main()
