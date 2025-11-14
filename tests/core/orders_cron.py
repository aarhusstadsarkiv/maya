import asyncio
from maya.core.dynamic_settings import init_settings
from maya.core.logging import get_log
import unittest
from maya.core.migration import Migration
from maya.migrations.orders import migrations_orders
import os
from maya.database import crud_orders
from maya.database import utils_orders
import arrow
import json

init_settings()
log = get_log()


class TestDB(unittest.TestCase):

    def get_test_data(self):
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

    def test_cron_orders(self):
        asyncio.run(self._test_cron_orders())

    async def _test_cron_orders(self):
        """
        Simple integration test for orders
        """
        # generate a new database for testing
        db_path = "/tmp/orders.db"
        if os.path.exists(db_path):
            os.remove(db_path)

        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, me_2, meta_data, record_and_types = self.get_test_data()

        # insert order
        order_1 = await crud_orders.insert_order(meta_data, record_and_types, me)
        order_2 = await crud_orders.insert_order(meta_data, record_and_types, me_2)
        
        self.assertEqual(order_2["order_status"], utils_orders.ORDER_STATUS.QUEUED)
        await crud_orders.update_order(
            me["id"],
            order_1["order_id"],
            update_values={"order_status": utils_orders.ORDER_STATUS.ORDERED},
        )

        num_renewal_emails = await crud_orders.cron_renewal_emails()
        self.assertEqual(num_renewal_emails, 0)

        # set location to READING_ROOM
        await crud_orders.update_order(
            me["id"],
            order_1["order_id"],
            update_values={"location": utils_orders.RECORD_LOCATION.READING_ROOM},
        )

        num_renewal_emails = await crud_orders.cron_renewal_emails()
        self.assertEqual(num_renewal_emails, 0)

        # set expire_at to to 3 + 1 days in the future
        # deadline is the last day the order is valid. 
        # Therefor we add one extra day which is the day it expires
        utc_now = arrow.utcnow()
        expire_at_date = utc_now.floor("day").shift(days=utils_orders.DEADLINE_DAYS_RENEWAL + 1)
        expire_at_str = expire_at_date.format("YYYY-MM-DD HH:mm:ss")
        await crud_orders.update_order(
            me["id"],
            order_1["order_id"],
            update_values={"expire_at": expire_at_str},
        )

        # the order can not be renewed as a another order is queued for 
        # the same record by another user
        num_renewal_emails = await crud_orders.cron_renewal_emails()
        self.assertEqual(num_renewal_emails, 0)

        # Set status of order_2 to COMPLETED so order_1 can be renewed
        await crud_orders.update_order(
            me_2["id"],
            order_2["order_id"],
            update_values={"order_status": utils_orders.ORDER_STATUS.COMPLETED},
        )

        # Now the order can be renewed
        num_renewal_emails = await crud_orders.cron_renewal_emails()
        self.assertEqual(num_renewal_emails, 1)

if __name__ == "__main__":
    unittest.main()
