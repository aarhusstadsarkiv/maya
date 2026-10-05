import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from bs4 import BeautifulSoup
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from starlette.requests import Request

from maya.core.auth import AuthExceptionJSON
from maya.core.migration import Migration
from maya.endpoints import endpoints_order
from maya.migrations.orders import migrations_orders
from maya.orders import runtime, service, utils_orders
from maya.orders.constants import LOG_MESSAGES
from maya.orders.types import OrderFilter

STATUS = utils_orders.ORDER_STATUS
LOCATION = utils_orders.RECORD_LOCATION


class TestCompleteAndReturn(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, "orders.db")
        migration = Migration(self.path, migrations_orders)
        migration.run_migrations()
        migration.close()
        self.enterContext(patch.object(runtime, "orders_url", self.path))
        self.send_mail = self.enterContext(patch.object(service.notifications, "send_ready_orders_message", new=AsyncMock()))
        with open("tests/data/meta_data_000309478.json") as source:
            metadata = source.read()
        with open("tests/data/record_and_types_000309478.json") as source:
            display = source.read()
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO records (record_id, label, meta_data, record_and_types, location) VALUES (?, ?, ?, ?, ?)",
                ("record", "Material", metadata, display, LOCATION.READING_ROOM),
            )
            db.execute("INSERT INTO orders (user_id, order_status, record_id) VALUES ('SYSTEM', ?, 'record')", (STATUS.ORDERED,))

    def snapshot(self):
        with sqlite3.connect(self.path) as db:
            return {table: db.execute(f"SELECT * FROM {table}").fetchall() for table in ["orders", "records", "orders_log"]}

    def add_other_order(self, status):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO orders (user_id, order_status, record_id) VALUES ('OTHER', ?, 'record')", (status,))

    async def post_return(self, order_id=1):
        request = Request({"type": "http", "path_params": {"order_id": order_id}, "session": {}})
        with (
            patch.object(endpoints_order, "is_authenticated_json", new=AsyncMock()) as authenticate,
            patch.object(endpoints_order.api, "users_me_get", new=AsyncMock(return_value={"id": "SYSTEM"})),
        ):
            response = await endpoints_order.orders_admin_complete_and_return(request)
        authenticate.assert_awaited_once_with(request, must_be_verified=True, permissions=["employee"])
        return response, request

    async def test_completes_and_returns_with_both_log_entries(self):
        response, request = await self.post_return()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(json.loads(response.body)["error"])
        self.assertEqual(request.session["flash"][0]["type"], "success")
        order = await service.get_order(1)
        self.assertEqual(order["order_status"], STATUS.COMPLETED)
        self.assertEqual(order["location"], LOCATION.RETURN_TO_STORAGE)
        logs = await service.get_logs(1)
        self.assertEqual([log["message"] for log in logs], [LOG_MESSAGES.LOCATION_CHANGED, LOG_MESSAGES.STATUS_CHANGED])
        self.assertEqual([log["updated_order_status"] for log in logs], ["Afsluttet", "Afsluttet"])
        self.assertEqual([log["updated_location"] for log in logs], ["Pakket retur", "På læsesalen"])
        self.assertEqual({log["user_id"] for log in logs}, {"SYSTEM"})
        self.send_mail.assert_not_awaited()

        # Repeating a stale click cannot create more logs or alter the completed order.
        before = self.snapshot()
        response, _ = await self.post_return()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.snapshot(), before)

    async def test_return_requires_reading_room_for_orders_and_applications(self):
        for status in [STATUS.ORDERED, STATUS.APPLICATION]:
            for location in vars(LOCATION).values():
                with self.subTest(status=status, location=location):
                    with sqlite3.connect(self.path) as db:
                        db.execute("UPDATE orders SET order_status = ?", (status,))
                        db.execute("UPDATE records SET location = ?", (location,))
                    before = self.snapshot()
                    page = await self.render_orders(OrderFilter())
                    response, request = await self.post_return()
                    if location == LOCATION.READING_ROOM:
                        self.assertEqual(page.select_one('[data-action="complete_and_return"]').text, "Retur")
                        self.assertEqual(response.status_code, 200)
                        order = await service.get_order(1)
                        self.assertEqual(order["order_status"], STATUS.COMPLETED)
                        self.assertEqual(order["location"], LOCATION.RETURN_TO_STORAGE)
                    else:
                        self.assertIsNone(page.select_one('[data-action="complete_and_return"]'))
                        disabled = page.select_one('[aria-disabled="true"]')
                        self.assertEqual(disabled.text, "Retur")
                        self.assertIn("på læsesalen", disabled["title"])
                        self.assertEqual(response.status_code, 409)
                        self.assertIn("på læsesalen", json.loads(response.body)["message"])
                        self.assertNotIn("flash", request.session)
                        self.assertEqual(self.snapshot(), before)
        self.send_mail.assert_not_awaited()

    async def test_waiting_or_active_orders_block_without_changes_or_mail(self):
        for status in [STATUS.QUEUED, STATUS.ORDERED, STATUS.APPLICATION]:
            with self.subTest(status=status):
                with sqlite3.connect(self.path) as db:
                    db.execute("DELETE FROM orders WHERE order_id != 1")
                self.add_other_order(status)
                before = self.snapshot()
                response, request = await self.post_return()
                self.assertEqual(response.status_code, 409)
                self.assertIn("andre aktive bestillinger", json.loads(response.body)["message"])
                self.assertNotIn("flash", request.session)
                self.assertEqual(self.snapshot(), before)
        self.send_mail.assert_not_awaited()

    async def test_historical_orders_do_not_block_return(self):
        self.add_other_order(STATUS.COMPLETED)
        self.add_other_order(STATUS.DELETED)
        await service.complete_and_return_order("SYSTEM", 1)
        self.assertEqual((await service.get_order(1))["location"], LOCATION.RETURN_TO_STORAGE)

    async def test_queued_and_closed_orders_cannot_be_returned(self):
        for status in [STATUS.QUEUED, STATUS.COMPLETED, STATUS.DELETED]:
            with self.subTest(status=status):
                with sqlite3.connect(self.path) as db:
                    db.execute("UPDATE orders SET order_status = ?", (status,))
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    await service.complete_and_return_order("SYSTEM", 1)
                self.assertEqual(self.snapshot(), before)
        response, _ = await self.post_return(order_id=999)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.body)["message"], "Bestillingen findes ikke.")
        self.send_mail.assert_not_awaited()

    async def test_failure_rolls_back_status_location_and_logs(self):
        before = self.snapshot()
        update_location = service.update_location_with_crud

        async def fail_after_location_update(*args, **kwargs):
            await update_location(*args, **kwargs)
            raise RuntimeError("Simulated failure after writing location and logs")

        with (
            patch.object(service, "update_location_with_crud", side_effect=fail_after_location_update),
            self.assertLogs(endpoints_order.log, level="ERROR"),
        ):
            response, request = await self.post_return()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("flash", request.session)
        self.assertEqual(self.snapshot(), before)
        self.send_mail.assert_not_awaited()

    async def test_unauthorized_requests_cannot_change_orders(self):
        before = self.snapshot()
        request = Request({"type": "http", "path_params": {"order_id": 1}, "session": {}})
        with (
            patch.object(endpoints_order, "is_authenticated_json", new=AsyncMock(side_effect=AuthExceptionJSON())),
            patch.object(endpoints_order.api, "users_me_get", new=AsyncMock()) as get_user,
        ):
            response = await endpoints_order.orders_admin_complete_and_return(request)
        self.assertEqual(response.status_code, 403)
        get_user.assert_not_awaited()
        self.assertEqual(self.snapshot(), before)

    async def render_orders(self, filters):
        orders, filters = await service.get_orders_admin(filters)
        environment = Environment(
            loader=ChoiceLoader([DictLoader({"base.html": "{% block content %}{% endblock %}"}), FileSystemLoader("maya/templates")]),
            autoescape=True,
        )
        environment.globals.update(get_setting=lambda key: None, get_icon=lambda name: "", has_permission=lambda *args: False)
        html = environment.get_template("order/orders_admin.html").render(
            orders=orders,
            filters=filters,
            locations=utils_orders.RECORD_LOCATION_HUMAN,
            magasin_options={"all": "Alle magasiner"},
            ORDER_STATUS=STATUS,
            request=Request({"type": "http"}),
        )
        return BeautifulSoup(html, "html.parser")

    async def test_page_action_and_stale_page_queue_check(self):
        page = await self.render_orders(OrderFilter())
        self.assertIsNotNone(page.select_one('[data-action="complete_and_return"]'))
        self.assertIsNotNone(page.select_one('[data-action="completed"]'))

        # A queued order arriving after the page was loaded must still block the POST.
        self.add_other_order(STATUS.QUEUED)
        response, _ = await self.post_return()
        self.assertEqual(response.status_code, 409)
        page = await self.render_orders(OrderFilter())
        self.assertIsNone(page.select_one('[data-action="complete_and_return"]'))
        disabled = page.select_one('[aria-disabled="true"]')
        self.assertIsNotNone(disabled)
        self.assertIn("brugere i kø", disabled["title"])
        self.assertIsNotNone(page.select_one('[data-action="completed"]'))

        # Ordinary completion continues to promote and notify the next user.
        await service.update_order("SYSTEM", 1, {"order_status": STATUS.COMPLETED})
        self.assertEqual((await service.get_order(2))["order_status"], STATUS.ORDERED)
        self.send_mail.assert_awaited_once()

    async def test_completed_and_history_views_hide_combined_action(self):
        await service.complete_and_return_order("SYSTEM", 1)
        for status in ["completed", "order_history"]:
            with self.subTest(status=status):
                page = await self.render_orders(OrderFilter(filter_status=status))
                self.assertIsNone(page.select_one('[data-action="complete_and_return"]'))
                self.assertIsNone(page.select_one('[aria-disabled="true"]'))
