import asyncio
import os
import unittest

from unittest.mock import AsyncMock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.core.dynamic_settings import init_settings
from maya.orders import notifications

init_settings()


class TestOrdersNotifications(unittest.TestCase):

    def test_send_ready_orders_message_rejects_empty_orders(self):
        asyncio.run(self._test_send_ready_orders_message_rejects_empty_orders())

    async def _test_send_ready_orders_message_rejects_empty_orders(self):
        with self.assertRaises(ValueError) as error:
            await notifications.send_ready_orders_message("Titel", "Besked", [])

        self.assertIn("orders must contain at least one order", str(error.exception))

    def test_send_ready_orders_message_rejects_mixed_users(self):
        asyncio.run(self._test_send_ready_orders_message_rejects_mixed_users())

    async def _test_send_ready_orders_message_rejects_mixed_users(self):
        orders = [
            {"order_id": 1, "user_id": "USER_1", "user_display_name": "User 1"},
            {"order_id": 2, "user_id": "USER_2", "user_display_name": "User 2"},
        ]

        with self.assertRaises(ValueError) as error:
            await notifications.send_ready_orders_message("Titel", "Besked", orders)

        self.assertIn("orders must belong to the same user", str(error.exception))

    def test_send_renew_order_message_rejects_empty_orders(self):
        asyncio.run(self._test_send_renew_order_message_rejects_empty_orders())

    async def _test_send_renew_order_message_rejects_empty_orders(self):
        with self.assertRaises(ValueError) as error:
            await notifications.send_renew_order_message("Titel", "Besked", [])

        self.assertIn("orders must contain at least one order", str(error.exception))

    def test_send_renew_order_message_rejects_mixed_users(self):
        asyncio.run(self._test_send_renew_order_message_rejects_mixed_users())

    async def _test_send_renew_order_message_rejects_mixed_users(self):
        orders = [
            {"order_id": 1, "user_id": "USER_1", "user_display_name": "User 1"},
            {"order_id": 2, "user_id": "USER_2", "user_display_name": "User 2"},
        ]

        with self.assertRaises(ValueError) as error:
            await notifications.send_renew_order_message("Titel", "Besked", orders)

        self.assertIn("orders must belong to the same user", str(error.exception))

    def test_send_renew_order_message_posts_mail_for_multiple_orders(self):
        asyncio.run(self._test_send_renew_order_message_posts_mail_for_multiple_orders())

    async def _test_send_renew_order_message_posts_mail_for_multiple_orders(self):
        orders = [
            {"order_id": 1, "user_id": "USER_1", "user_display_name": "Test User", "record_id": "0001", "label": "Mat 1"},
            {"order_id": 2, "user_id": "USER_1", "user_display_name": "Test User", "record_id": "0002", "label": "Mat 2"},
        ]

        with (
            patch("maya.orders.notifications.get_template_content", new=AsyncMock(return_value="<html>mail</html>")),
            patch("maya.orders.notifications.api.mail_post", new=AsyncMock(return_value=None)) as mail_post_mock,
        ):
            await notifications.send_renew_order_message("Forny", "Din bestilling udløber", orders)

        mail_post_mock.assert_awaited_once()
        mail_payload = mail_post_mock.await_args.args[0]
        self.assertEqual(mail_payload["data"]["user_id"], "USER_1")
        self.assertEqual(mail_payload["data"]["subject"], "Forny")
        self.assertEqual(mail_payload["data"]["html_content"], "<html>mail</html>")


if __name__ == "__main__":
    unittest.main()
