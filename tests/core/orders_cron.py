import os
import asyncio
import arrow
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

    def get_test_data(self):
        # Load user, meta_data and record_and_types - test data
        me_data_file = "tests/data/me.json"
        with open(me_data_file) as f:
            me = json.load(f)

        # Generate a second user
        me_2 = me.copy()
        me_2["id"] = "ANOTHER_USER_ID"
        me_2["email"] = "another.email@example.com"

        meta_data_file = "tests/data/meta_data_000309478.json"
        with open(meta_data_file) as f:
            meta_data = json.load(f)

        record_and_types_file = "tests/data/record_and_types_000309478.json"
        with open(record_and_types_file) as f:
            record_and_types = json.load(f)

        return me, me_2, meta_data, record_and_types

    async def _test_cron_orders(self):
        """
        Simple integration test for orders
        """
        db_path = self.get_db_path()
        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, me_2, meta_data, record_and_types = self.get_test_data()
        original_send_ready_orders_message = utils_orders.send_ready_orders_message
        original_send_renew_order_message = utils_orders.send_renew_order_message

        async def _send_ready_orders_message_stub(*args, **kwargs):
            return None

        async def _send_renew_order_message_stub(*args, **kwargs):
            return None

        utils_orders.send_ready_orders_message = _send_ready_orders_message_stub
        utils_orders.send_renew_order_message = _send_renew_order_message_stub

        try:
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

            await crud_orders.update_order(
                me["id"],
                order_1["order_id"],
                update_values={"location": utils_orders.RECORD_LOCATION.READING_ROOM},
            )

            num_renewal_emails = await crud_orders.cron_renewal_emails()
            self.assertEqual(num_renewal_emails, 0)

            utc_now = arrow.utcnow()
            expire_at_date = utc_now.floor("day").shift(days=utils_orders.DEADLINE_DAYS_RENEWAL + 1)
            expire_at_str = expire_at_date.format("YYYY-MM-DD HH:mm:ss")
            await crud_orders.update_order(
                me["id"],
                order_1["order_id"],
                update_values={"expire_at": expire_at_str},
            )

            num_renewal_emails = await crud_orders.cron_renewal_emails()
            self.assertEqual(num_renewal_emails, 0)

            await crud_orders.update_order(
                me_2["id"],
                order_2["order_id"],
                update_values={"order_status": utils_orders.ORDER_STATUS.COMPLETED},
            )

            num_renewal_emails = await crud_orders.cron_renewal_emails()
            self.assertEqual(num_renewal_emails, 1)
        finally:
            utils_orders.send_ready_orders_message = original_send_ready_orders_message
            utils_orders.send_renew_order_message = original_send_renew_order_message

    def test_cron_orders(self):
        asyncio.run(self._test_cron_orders())

    async def _test_cron_expire_orders(self):
        """
        Simple integration test for expiring orders
        """
        # generate a new database for testing
        db_path = self.get_db_path()

        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, me_2, meta_data, record_and_types = self.get_test_data()

        # insert order
        order = await crud_orders.insert_order(meta_data, record_and_types, me)
        order_2 = await crud_orders.insert_order(meta_data, record_and_types, me_2)

        self.assertEqual(order["order_status"], utils_orders.ORDER_STATUS.ORDERED)
        self.assertEqual(order_2["order_status"], utils_orders.ORDER_STATUS.QUEUED)

        num_expired_orders = await crud_orders.cron_orders_expire()
        self.assertEqual(num_expired_orders, 0)

        # set expire_at to today
        utc_now = arrow.utcnow()
        expire_at_date = utc_now.floor("day").shift(days=0)
        expire_at_str = expire_at_date.format("YYYY-MM-DD HH:mm:ss")

        log.info(f"Setting expire_at to {expire_at_str} for order {order['order_id']}")
        await crud_orders.update_order(
            me["id"],
            order["order_id"],
            update_values={"expire_at": expire_at_str},
        )

        # This is queued order - should not be expired
        await crud_orders.update_order(
            me_2["id"],
            order_2["order_id"],
            update_values={"expire_at": expire_at_str},
        )

        num_expired_orders = await crud_orders.cron_orders_expire()
        self.assertEqual(num_expired_orders, 1)

        # First order is expired now so we can expire the second order
        num_expired_orders = await crud_orders.cron_orders_expire()
        self.assertEqual(num_expired_orders, 1)

        num_expired_orders = await crud_orders.cron_orders_expire()
        self.assertEqual(num_expired_orders, 0)

    def test_cron_expire_orders(self):
        asyncio.run(self._test_cron_expire_orders())

    async def _test_renew_orders_user(self):
        db_path = self.get_db_path()

        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, _, meta_data, record_and_types = self.get_test_data()

        with open("tests/data/meta_data_000495102.json") as f:
            meta_data_2 = json.load(f)

        with open("tests/data/record_and_types_000495102.json") as f:
            record_and_types_2 = json.load(f)

        original_send_ready_orders_message = utils_orders.send_ready_orders_message

        async def _send_ready_orders_message_stub(*args, **kwargs):
            return None

        utils_orders.send_ready_orders_message = _send_ready_orders_message_stub

        try:
            renewable_order = await crud_orders.insert_order(meta_data, record_and_types, me)
            not_renewable_order = await crud_orders.insert_order(meta_data_2, record_and_types_2, me)

            await crud_orders.update_order(
                me["id"],
                renewable_order["order_id"],
                update_values={"location": utils_orders.RECORD_LOCATION.READING_ROOM},
            )
            await crud_orders.update_order(
                me["id"],
                not_renewable_order["order_id"],
                update_values={"location": utils_orders.RECORD_LOCATION.READING_ROOM},
            )

            utc_now = arrow.utcnow()
            renewable_expire_at = utc_now.floor("day").shift(days=utils_orders.DEADLINE_DAYS_RENEWAL + 1).format("YYYY-MM-DD HH:mm:ss")
            not_renewable_expire_at = utc_now.floor("day").shift(days=utils_orders.DEADLINE_DAYS_RENEWAL + 10).format("YYYY-MM-DD HH:mm:ss")

            await crud_orders.update_order(
                me["id"],
                renewable_order["order_id"],
                update_values={"expire_at": renewable_expire_at},
            )
            await crud_orders.update_order(
                me["id"],
                not_renewable_order["order_id"],
                update_values={"expire_at": not_renewable_expire_at},
            )

            num_renewed = await crud_orders.renew_orders_user(me["id"])
            self.assertEqual(num_renewed, 1)

            renewed_order = await crud_orders.get_order(renewable_order["order_id"])
            skipped_order = await crud_orders.get_order(not_renewable_order["order_id"])

            self.assertEqual(renewed_order["expire_at"], utils_orders.get_expire_at_date())
            self.assertEqual(skipped_order["expire_at"], not_renewable_expire_at)
        finally:
            utils_orders.send_ready_orders_message = original_send_ready_orders_message

    def test_renew_orders_user(self):
        asyncio.run(self._test_renew_orders_user())


if __name__ == "__main__":
    unittest.main()
