import asyncio
import os
import unittest

from unittest.mock import AsyncMock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.core.dynamic_settings import init_settings
from sites.aarhus.hooks import Hooks

init_settings()


class TestAarhusHooks(unittest.TestCase):

    def test_after_get_record_sets_active_order_fields(self):
        asyncio.run(self._test_after_get_record_sets_active_order_fields())

    async def _test_after_get_record_sets_active_order_fields(self):
        record = {"id": "0001"}
        meta_data = {"id": "0001", "title": "Materiale"}
        active_order = {
            "order_id": 17,
            "record_id": "0001",
            "label": "Materiale",
            "location_human": "Læsesal",
            "expire_at_human": "2026-04-20",
        }

        hooks = Hooks(request=object())

        with (
            patch("sites.aarhus.hooks.api.me_get", new=AsyncMock(return_value={"id": "USER_1"})),
            patch("sites.aarhus.hooks.orders_service.has_active_order", new=AsyncMock(return_value=active_order)),
            patch("sites.aarhus.hooks.orders_service.is_order_renew_possible_user", new=AsyncMock(return_value=True)),
            patch("sites.aarhus.hooks.utils_orders.get_single_order_message", return_value="Bestilling aktiv"),
        ):
            _, updated_meta_data = await hooks.after_get_record(record, meta_data)

        self.assertTrue(updated_meta_data["has_active_order"])
        self.assertTrue(updated_meta_data["is_order_renew_possible"])
        self.assertEqual(updated_meta_data["active_order_id"], 17)
        self.assertEqual(updated_meta_data["active_order_message"], "Bestilling aktiv")


if __name__ == "__main__":
    unittest.main()
