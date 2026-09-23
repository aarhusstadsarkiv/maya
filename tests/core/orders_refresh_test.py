import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.core.dynamic_settings import init_settings
from maya.core.migration import Migration
from maya.migrations.orders import migrations_orders
from maya.orders import refresh, runtime, utils_orders

init_settings()


class TestRefresh(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, "orders.db")
        migration = Migration(self.path, {"create_orders": migrations_orders["create_orders"]})
        migration.run_migrations()
        migration.close()
        with sqlite3.connect(self.path) as connection:
            for record_id, location in [("one", "Bautavej"), ("two", ""), ("three", None)]:
                connection.execute(
                    "INSERT INTO records VALUES (?, ?, ?, ?, ?)",
                    (record_id, "Old title", json.dumps({"resources": {"location": location}}), "{}", 2),
                )
        migration = Migration(self.path, migrations_orders)
        migration.run_migrations()
        migration.close()
        self.patcher = patch.object(runtime, "orders_url", self.path)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_migration_backfills_and_indexes(self):
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(
                connection.execute("SELECT magasin FROM records ORDER BY record_id").fetchall(), [("BTV",), ("MAG",), ("MAG",)]
            )
            self.assertIn("idx_records_magasin", [row[1] for row in connection.execute("PRAGMA index_list(records)")])
        for location, expected in [(" BAUTAVEJ ", "BTV"), ("", "MAG"), (None, "MAG"), ("Elsewhere", "MAG")]:
            self.assertEqual(utils_orders.get_mag_location_string({"resources": {"location": location}}), expected)

    async def test_refresh_preserves_workflow_and_continues_after_failure(self):
        async def fetch(client, record_id):
            if record_id == "three":
                raise RuntimeError("Unavailable")
            # Simulate a staff location change while the API call is in flight.
            with sqlite3.connect(self.path) as connection:
                connection.execute("UPDATE records SET location = 3 WHERE record_id = ?", (record_id,))
            return {"id": record_id, "meta_title": "New title", "resources": {"location": "Bautavej"}}, {"title": "New"}

        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT INTO orders (user_id, order_status, record_id) VALUES ('SYSTEM', 1, 'one')")
            before_orders = connection.execute("SELECT * FROM orders").fetchall()
        with patch.object(refresh, "fetch_record_data", side_effect=fetch):
            self.assertEqual(await refresh.cron_refresh_records(), {"updated": 2, "failed": 1})
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT * FROM orders").fetchall(), before_orders)
            self.assertEqual(
                connection.execute("SELECT label, location, magasin FROM records WHERE record_id='one'").fetchone(), ("New title", 3, "BTV")
            )
            self.assertEqual(connection.execute("SELECT label, location FROM records WHERE record_id='three'").fetchone(), ("Old title", 2))
            self.assertEqual(
                json.loads(connection.execute("SELECT record_and_types FROM records WHERE record_id='two'").fetchone()[0]), {"title": "New"}
            )

    async def test_fetch_converts_material_without_a_user_session(self):
        with open("tests/data/record_and_types_000309478.json") as source:
            record = {key: field["value"] for key, field in json.load(source).items()}
        record["admin_data"] = {"Æske": "42"}
        record["resources"] = [{"location": "Bautavej"}]
        record["contractual_status"] = {"id": 1}
        response = Mock()
        response.json.return_value = record
        client = Mock(get=AsyncMock(return_value=response))
        meta_data, display = await refresh.fetch_record_data(client, "000309478")
        self.assertEqual(meta_data["meta_title"], "Aarhus Vejviser 1997")
        self.assertEqual(utils_orders.get_mag_location_string(meta_data), "BTV")
        self.assertEqual(utils_orders.get_lb_number(display), "42")
        response.raise_for_status.assert_called_once()

    async def test_fetch_rejects_mismatched_ids(self):
        response = Mock()
        response.json.return_value = {"id": "wrong"}
        client = Mock(get=AsyncMock(return_value=response))
        with self.assertRaises(ValueError):
            await refresh.fetch_record_data(client, "one")

    async def test_failed_refresh_reports_counts_without_raising(self):
        with (
            patch.object(refresh, "fetch_record_data", new=AsyncMock(side_effect=RuntimeError("Unavailable"))),
            patch.object(refresh.runtime.cron_log, "info") as log_info,
        ):
            result = await refresh.cron_refresh_records()
        self.assertEqual(result, {"updated": 0, "failed": 3})
        log_info.assert_any_call("Materials refreshed: %s; failed: %s", 0, 3)


if __name__ == "__main__":
    unittest.main()
