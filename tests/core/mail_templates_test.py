import asyncio
import os
import unittest

os.environ.setdefault("BASE_DIR", "sites/aarhus")

from maya.core.dynamic_settings import init_settings
from maya.core.templates import get_template_content

init_settings()


class TestMailTemplates(unittest.TestCase):
    def test_order_mail_renders_single_order_wording(self):
        asyncio.run(self._test_order_mail_renders_single_order_wording())

    async def _test_order_mail_renders_single_order_wording(self):
        html_content = await get_template_content(
            "mails/order_mail.html",
            {
                "title": "Din bestilling er klar til gennemsyn",
                "client_domain_url": "https://example.com",
                "client_name": "Aarhus Stadsarkiv",
                "orders": [
                    {"record_id": "0001", "label": "Materiale 1", "user_display_name": "Test User"},
                ],
            },
        )

        self.assertIn("Kære Test User", html_content)
        self.assertIn("Du har bestilt et arkivalie", html_content)
        self.assertIn("Materialet er nu tilgængeligt", html_content)
        self.assertNotIn("Du har bestilt flere arkivalier", html_content)

    def test_order_mail_renders_multiple_orders(self):
        asyncio.run(self._test_order_mail_renders_multiple_orders())

    async def _test_order_mail_renders_multiple_orders(self):
        html_content = await get_template_content(
            "mails/order_mail.html",
            {
                "title": "Din bestilling er klar til gennemsyn",
                "client_domain_url": "https://example.com",
                "client_name": "Aarhus Stadsarkiv",
                "orders": [
                    {"record_id": "0001", "label": "Materiale 1", "user_display_name": "Test User"},
                    {"record_id": "0002", "label": "Materiale 2", "user_display_name": "Test User"},
                ],
            },
        )

        self.assertIn("Kære Test User", html_content)
        self.assertIn("Du har bestilt arkivalier", html_content)
        self.assertIn("Materialerne er nu tilgængelige", html_content)
        self.assertIn("Materiale 1", html_content)
        self.assertIn("Materiale 2", html_content)
        self.assertIn('href="https://example.com/records/0001"', html_content)
        self.assertIn('href="https://example.com/records/0002"', html_content)

    def test_order_renew_mail_renders_single_order_wording(self):
        asyncio.run(self._test_order_renew_mail_renders_single_order_wording())

    async def _test_order_renew_mail_renders_single_order_wording(self):
        html_content = await get_template_content(
            "mails/order_renew_mail.html",
            {
                "title": "Udlob af materiale",
                "client_domain_url": "https://example.com",
                "renew_orders_url": "https://example.com/auth/orders/active",
                "deadline_days": 14,
                "client_name": "Aarhus Stadsarkiv",
                "orders": [
                    {"record_id": "0001", "label": "Materiale 1", "user_display_name": "Test User"},
                ],
            },
        )

        self.assertIn("Kære Test User", html_content)
        self.assertIn("Din bestilling udløber om 14 dage", html_content)
        self.assertIn("fornyelse af følgende materiale", html_content)
        self.assertNotIn("Dine bestillinger udløber", html_content)

    def test_order_renew_mail_renders_multiple_orders(self):
        asyncio.run(self._test_order_renew_mail_renders_multiple_orders())

    async def _test_order_renew_mail_renders_multiple_orders(self):
        html_content = await get_template_content(
            "mails/order_renew_mail.html",
            {
                "title": "Udlob af materiale",
                "client_domain_url": "https://example.com",
                "renew_orders_url": "https://example.com/auth/orders/active",
                "deadline_days": 14,
                "client_name": "Aarhus Stadsarkiv",
                "orders": [
                    {"record_id": "0001", "label": "Materiale 1", "user_display_name": "Test User"},
                    {"record_id": "0002", "label": "Materiale 2", "user_display_name": "Test User"},
                ],
            },
        )

        self.assertIn("Kære Test User", html_content)
        self.assertIn("Dine bestillinger udløber om 14 dage", html_content)
        self.assertIn("fornyelse af følgende materialer", html_content)
        self.assertIn('href="https://example.com/auth/orders/active"', html_content)


if __name__ == "__main__":
    unittest.main()
