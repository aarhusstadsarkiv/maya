import asyncio
import os
import unittest

os.environ.setdefault("BASE_DIR", "sites/aarhus")

from maya.core.dynamic_settings import init_settings
from maya.core.templates import get_template_content

init_settings()


class TestMailTemplates(unittest.TestCase):

    def test_order_mail_renders_multiple_orders(self):
        asyncio.run(self._test_order_mail_renders_multiple_orders())

    async def _test_order_mail_renders_multiple_orders(self):
        html_content = await get_template_content(
            "mails/order_mail.html",
            {
                "title": "Din bestilling er klar til gennemsyn",
                "message": "Du har materiale klar.",
                "client_domain_url": "https://example.com",
                "client_name": "Aarhus Stadsarkiv",
                "orders": [
                    {"record_id": "0001", "label": "Materiale 1", "user_display_name": "Test User"},
                    {"record_id": "0002", "label": "Materiale 2", "user_display_name": "Test User"},
                ],
            },
        )

        self.assertIn("Kære Test User", html_content)
        self.assertIn("Materiale 1", html_content)
        self.assertIn("Materiale 2", html_content)
        self.assertIn('href="https://example.com/records/0001"', html_content)
        self.assertIn('href="https://example.com/records/0002"', html_content)


if __name__ == "__main__":
    unittest.main()
