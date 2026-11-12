import os
import sqlite3
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

import httpx2
from bs4 import BeautifulSoup

from maya.app import app
from maya.core import api
from maya.core.dynamic_settings import settings
from maya.endpoints import endpoints_bookmarks
from maya.migrations.default import alter_bookmarks_table, create_booksmarks_query


class BookmarksTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.dict(settings, update_translations=False))
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.db_path = str(Path(directory) / "bookmarks.db")
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(create_booksmarks_query + alter_bookmarks_table)
        self.enterContext(patch.object(endpoints_bookmarks, "database_url", self.db_path))
        self.enterContext(patch.object(endpoints_bookmarks, "is_authenticated", new=AsyncMock()))
        self.enterContext(patch.object(endpoints_bookmarks, "is_authenticated_json", new=AsyncMock()))
        self.enterContext(
            patch.object(api, "users_me_get", new=AsyncMock(return_value={"id": "bookmark-user", "is_verified": True, "permissions": []}))
        )

        async def resolve(request, record_ids):
            return [{"id": record_id, "title": "Bookmarked record"} for record_id in record_ids]

        self.enterContext(patch.object(api, "proxies_resolve", new=AsyncMock(side_effect=resolve)))
        self.client = await self.enterAsyncContext(
            httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="https://aarhus.local")
        )

    async def post(self, data):
        return await self.client.post("/auth/bookmarks", json=data, headers={"Origin": "https://aarhus.local"})

    def stored_bookmarks(self):
        with sqlite3.connect(self.db_path) as connection:
            return connection.execute("SELECT user_id, record_id FROM bookmarks ORDER BY user_id, record_id").fetchall()

    async def test_add_then_delete_using_the_id_rendered_in_the_bookmarks_list(self):
        record_id = "000495102"
        response = await self.post({"record_id": record_id, "action": "add"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["error"])
        self.assertIn(("bookmark-user", record_id), self.stored_bookmarks())

        page = await self.client.get("/auth/bookmarks")
        self.assertEqual(page.status_code, 200)
        soup = BeautifulSoup(page.text, "html.parser")
        button = soup.select_one(".delete-bookmark")
        self.assertIsNotNone(button)
        self.assertEqual(button["data-id"], record_id)

        response = await self.post({"record_id": button["data-id"], "action": "delete"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["error"])
        self.assertEqual(self.stored_bookmarks(), [])
        page = await self.client.get("/auth/bookmarks")
        self.assertIsNone(BeautifulSoup(page.text, "html.parser").select_one(".delete-bookmark"))

    async def test_deletion_only_removes_the_current_users_selected_bookmark(self):
        with sqlite3.connect(self.db_path) as connection:
            connection.executemany(
                "INSERT INTO bookmarks (user_id, record_id) VALUES (?, ?)",
                [("bookmark-user", "000495102"), ("other-user", "000495102"), ("bookmark-user", "000495103")],
            )
        response = await self.post({"record_id": "000495102", "action": "delete"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.stored_bookmarks(), [("bookmark-user", "000495103"), ("other-user", "000495102")])

    async def test_invalid_delete_payload_cannot_report_success(self):
        await self.post({"record_id": "000495102", "action": "add"})
        for payload in (
            {"record_id": "", "action": "delete"},
            {"record_id": None, "action": "delete"},
            {"action": "delete"},
            {"record_id": "000495102", "action": "invalid"},
        ):
            with self.subTest(payload=payload):
                response = await self.post(payload)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.json()["error"])
                self.assertEqual(self.stored_bookmarks(), [("bookmark-user", "000495102")])
