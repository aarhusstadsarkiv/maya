import os
import asyncio
import json
import tempfile
import unittest

from unittest.mock import AsyncMock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.core.dynamic_settings import init_settings
from maya.core.migration import Migration
from maya.migrations.orders import migrations_orders
from maya.orders import utils_orders
from maya.endpoints import endpoints_order
from maya.orders import service as orders_service
from maya.orders.constants import LOG_MESSAGES
from maya.orders import runtime as orders_runtime

init_settings()


class FakeRequest:
    def __init__(self, payload: list[dict]):
        self._payload = payload
        self.session = {}

    async def json(self):
        return self._payload


class TestOrdersBulkAdmin(unittest.TestCase):

    def get_db_path(self) -> str:
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(db_path)
        orders_runtime.orders_url = db_path
        return db_path

    def get_test_data(self):
        with open("tests/data/me.json") as f:
            me = json.load(f)

        me_2 = me.copy()
        me_2["id"] = "ANOTHER_USER_ID"
        me_2["email"] = "another.email@example.com"
        me_2["display_name"] = "another user"

        with open("tests/data/meta_data_000309478.json") as f:
            meta_data = json.load(f)

        with open("tests/data/record_and_types_000309478.json") as f:
            record_and_types = json.load(f)

        meta_data_2 = meta_data.copy()
        meta_data_2["id"] = "000309479"
        meta_data_2["real_id"] = "309479"
        meta_data_2["title"] = "Aarhus Vejviser 1998"
        meta_data_2["meta_title"] = "Aarhus Vejviser 1998"
        meta_data_2["meta_description"] = "Aarhus Vejviser 1998"

        return me, me_2, meta_data, record_and_types, meta_data_2, record_and_types

    def test_orders_admin_patch_multiple_groups_ready_mail_per_user(self):
        asyncio.run(self._test_orders_admin_patch_multiple_groups_ready_mail_per_user())

    async def _test_orders_admin_patch_multiple_groups_ready_mail_per_user(self):
        db_path = self.get_db_path()
        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, _, meta_data_1, record_and_types_1, meta_data_2, record_and_types_2 = self.get_test_data()

        order_1 = await orders_service.insert_order(meta_data_1, record_and_types_1, me)
        order_2 = await orders_service.insert_order(meta_data_2, record_and_types_2, me)

        sent_mail_calls: list[list[dict]] = []

        async def _send_ready_orders_message_stub(title: str, orders: list[dict]):
            sent_mail_calls.append(orders)
            return None

        request = FakeRequest(
            [
                {"order_id": order_1["order_id"], "location": utils_orders.RECORD_LOCATION.READING_ROOM},
                {"order_id": order_2["order_id"], "location": utils_orders.RECORD_LOCATION.READING_ROOM},
            ]
        )

        with (
            patch("maya.endpoints.endpoints_order.is_authenticated_json", new=AsyncMock(return_value=None)),
            patch("maya.endpoints.endpoints_order.api.users_me_get", new=AsyncMock(return_value=me)),
            patch("maya.orders.service.notifications.send_ready_orders_message", new=_send_ready_orders_message_stub),
        ):
            response = await endpoints_order.orders_admin_patch_multiple(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, b'{"error":false}')
        self.assertEqual(len(sent_mail_calls), 1)
        self.assertEqual(len(sent_mail_calls[0]), 2)
        self.assertEqual({order["order_id"] for order in sent_mail_calls[0]}, {order_1["order_id"], order_2["order_id"]})

        updated_order_1 = await orders_service.get_order(order_1["order_id"])
        updated_order_2 = await orders_service.get_order(order_2["order_id"])
        self.assertEqual(updated_order_1["message_sent"], 1)
        self.assertEqual(updated_order_2["message_sent"], 1)
        self.assertIsNotNone(updated_order_1["expire_at"])
        self.assertIsNotNone(updated_order_2["expire_at"])

        logs_1 = await orders_service.get_logs(order_1["order_id"])
        logs_2 = await orders_service.get_logs(order_2["order_id"])

        self.assertEqual(len(logs_1), 3)
        self.assertEqual(len(logs_2), 3)
        self.assertEqual(logs_1[0]["message"], LOG_MESSAGES.MAIL_SENT)
        self.assertEqual(logs_1[1]["message"], LOG_MESSAGES.LOCATION_CHANGED)
        self.assertEqual(logs_1[2]["message"], LOG_MESSAGES.ORDER_CREATED)
        self.assertEqual(logs_2[0]["message"], LOG_MESSAGES.MAIL_SENT)
        self.assertEqual(logs_2[1]["message"], LOG_MESSAGES.LOCATION_CHANGED)
        self.assertEqual(logs_2[2]["message"], LOG_MESSAGES.ORDER_CREATED)

    def test_orders_admin_patch_multiple_sends_one_mail_per_user_group(self):
        asyncio.run(self._test_orders_admin_patch_multiple_sends_one_mail_per_user_group())

    async def _test_orders_admin_patch_multiple_sends_one_mail_per_user_group(self):
        db_path = self.get_db_path()
        migration = Migration(db_path=db_path, migrations=migrations_orders)
        migration.run_migrations()

        me, me_2, meta_data_1, record_and_types_1, meta_data_2, record_and_types_2 = self.get_test_data()

        order_1 = await orders_service.insert_order(meta_data_1, record_and_types_1, me)
        order_2 = await orders_service.insert_order(meta_data_2, record_and_types_2, me_2)

        sent_mail_calls: list[list[dict]] = []

        async def _send_ready_orders_message_stub(title: str, orders: list[dict]):
            sent_mail_calls.append(orders)
            return None

        request = FakeRequest(
            [
                {"order_id": order_1["order_id"], "location": utils_orders.RECORD_LOCATION.READING_ROOM},
                {"order_id": order_2["order_id"], "location": utils_orders.RECORD_LOCATION.READING_ROOM},
            ]
        )

        with (
            patch("maya.endpoints.endpoints_order.is_authenticated_json", new=AsyncMock(return_value=None)),
            patch("maya.endpoints.endpoints_order.api.users_me_get", new=AsyncMock(return_value=me)),
            patch("maya.orders.service.notifications.send_ready_orders_message", new=_send_ready_orders_message_stub),
        ):
            response = await endpoints_order.orders_admin_patch_multiple(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(sent_mail_calls), 2)
        self.assertEqual(sorted(len(call) for call in sent_mail_calls), [1, 1])
        self.assertEqual(
            {call[0]["user_id"] for call in sent_mail_calls},
            {me["id"], me_2["id"]},
        )
        self.assertEqual(
            {call[0]["order_id"] for call in sent_mail_calls},
            {order_1["order_id"], order_2["order_id"]},
        )
