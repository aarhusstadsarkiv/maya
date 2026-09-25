import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from starlette.exceptions import HTTPException
from starlette.requests import Request
from maya.core.migration import Migration
from maya.endpoints import endpoints_order
from maya.migrations.orders import migrations_orders
from maya.orders import runtime, service, utils_orders
from maya.orders.types import OrderFilter


class TestMagasinFilter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "orders.db")
        migration = Migration(path, migrations_orders)
        migration.run_migrations()
        migration.close()
        patcher = patch.object(runtime, "orders_url", path)
        patcher.start()
        self.addCleanup(patcher.stop)
        with open("tests/data/meta_data_000309478.json") as source:
            metadata = json.load(source)
        with open("tests/data/record_and_types_000309478.json") as source:
            display = source.read()
        with sqlite3.connect(path) as db:
            for status in [utils_orders.ORDER_STATUS.ORDERED, utils_orders.ORDER_STATUS.COMPLETED]:
                for index, magasin in enumerate(["MAG", "BTV", "MAG", "BTV"]):
                    record_id = f"{status}-{index}"
                    db.execute(
                        "INSERT INTO records (record_id, label, meta_data, record_and_types, location, magasin) VALUES (?, ?, ?, ?, ?, ?)",
                        (record_id, "Material", json.dumps(metadata), display, utils_orders.RECORD_LOCATION.READING_ROOM, magasin),
                    )
                    db.execute("INSERT INTO orders (user_id, order_status, record_id) VALUES ('SYSTEM', ?, ?)", (status, record_id))

    async def test_filter_before_pagination_in_all_views(self):
        for status in ["active", "completed", "order_history"]:
            for magasin in ["MAG", "BTV"]:
                with self.subTest(status=status, magasin=magasin):
                    filters = OrderFilter(filter_status=status, filter_magasin=magasin, filter_limit=1)
                    first, page = await service.get_orders_admin(filters)
                    self.assertEqual([order["magasin"] for order in first], [magasin])
                    self.assertTrue(page.filter_has_next)
                    filters.filter_offset = page.filter_next_offset
                    second, page = await service.get_orders_admin(filters)
                    self.assertEqual([order["magasin"] for order in second], [magasin])
                    self.assertNotEqual(first[0]["order_id"], second[0]["order_id"])
                    self.assertFalse(page.filter_has_next)
                    self.assertTrue(page.filter_has_prev)
            orders, _ = await service.get_orders_admin(OrderFilter(filter_status=status))
            self.assertEqual(len(orders), 4)
            self.assertEqual({order["magasin"] for order in orders}, {"MAG", "BTV"})

    async def test_combines_with_existing_filters(self):
        orders, _ = await service.get_orders_admin(OrderFilter(filter_magasin="BTV", filter_email="no-match"))
        self.assertEqual(orders, [])


class TestMagasinRoute(unittest.IsolatedAsyncioTestCase):
    async def test_url_selection_and_default(self):
        for query, expected in [
            (b"", "all"),
            (b"filter_magasin=all", "all"),
            (b"filter_magasin=MAG", "MAG"),
            (b"filter_magasin=BTV", "BTV"),
        ]:

            async def get_orders(filters):
                self.assertEqual(filters.filter_magasin, expected)
                return [], filters

            with (
                patch.object(endpoints_order, "is_authenticated", new=AsyncMock()),
                patch.object(endpoints_order.api, "users_me_get", new=AsyncMock(return_value={"id": "employee"})),
                patch.object(service, "replace_employee", new=AsyncMock()),
                patch.object(service, "get_orders_admin", side_effect=get_orders),
                patch.object(endpoints_order, "get_context", new=AsyncMock(return_value={})),
                patch.object(endpoints_order.templates, "TemplateResponse"),
            ):
                await endpoints_order.orders_admin_get(Request({"type": "http", "query_string": query}))

    async def test_invalid_selection_rejected(self):
        with (
            patch.object(endpoints_order, "is_authenticated", new=AsyncMock()),
            patch.object(endpoints_order.api, "users_me_get", new=AsyncMock(return_value={"id": "employee"})),
            patch.object(service, "replace_employee", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as error:
                await endpoints_order.orders_admin_get(Request({"type": "http", "query_string": b"filter_magasin=invalid"}))
        self.assertEqual(error.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
