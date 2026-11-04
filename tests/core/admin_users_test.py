import os
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from starlette.requests import Request
from starlette.routing import Route, Router
from maya.endpoints import endpoints_admin


class TestAdminUsers(unittest.IsolatedAsyncioTestCase):
    async def render(self, query_string="", pages=None):
        router = Router(routes=[Route("/admin/users", endpoints_admin.admin_users_get, name="admin_users_get")])
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "scheme": "http",
                "server": ("testserver", 80),
                "path": "/admin/users",
                "root_path": "",
                "headers": [],
                "query_string": query_string.encode(),
                "router": router,
            }
        )
        with (
            patch.object(endpoints_admin, "is_authenticated", new_callable=AsyncMock) as auth,
            patch.object(endpoints_admin.api, "users_get", new_callable=AsyncMock, side_effect=pages or [[]]) as get_users,
            patch.object(
                endpoints_admin, "get_context", new_callable=AsyncMock, side_effect=lambda request, context_values: context_values
            ),
            patch.object(endpoints_admin.templates, "TemplateResponse", side_effect=lambda request, name, context: context),
        ):
            context = await endpoints_admin.admin_users_get(request)
        auth.assert_awaited_once_with(request, permissions=["admin"])
        queries = [parse_qs(call.kwargs["query_str"]) for call in get_users.await_args_list]
        return context, queries

    async def test_default_newest_first_and_empty_page(self):
        context, queries = await self.render()
        self.assertEqual(
            queries, [{"limit": ["100"], "offset": ["0"], "order": ["created_at"], "descending": ["true"], "is_active": ["true"]}]
        )
        self.assertFalse(context["has_next"])
        self.assertFalse(context["has_previous"])

    async def test_pagination_preserves_search_filter_and_sort(self):
        rows = [{"permissions": [{"grant_id": 10, "name": "user"}]} for _ in range(100)]
        context, queries = await self.render(
            "offset=100&pattern=007%2Banna%40example.com&is_verified=true&order=email&descending=false",
            [rows, [{"id": "next"}]],
        )
        self.assertTrue(context["has_next"])
        self.assertTrue(context["has_previous"])
        self.assertEqual(context["page_number"], 2)
        self.assertEqual(queries[1], {**queries[0], "limit": ["1"], "offset": ["200"]})
        for name, offset in [("next_url", "200"), ("prev_url", "0")]:
            self.assertEqual(parse_qs(urlsplit(context[name]).query), {**queries[0], "offset": [offset]})
        self.assertEqual(queries[0]["pattern"], ["007+anna@example.com"])
        self.assertEqual(queries[0]["is_verified"], ["true"])
        self.assertEqual(queries[0]["descending"], ["false"])

    async def test_exact_full_final_page_has_no_next(self):
        context, queries = await self.render(pages=[[{"permissions": [{"grant_id": 10, "name": "user"}]} for _ in range(100)], []])
        self.assertFalse(context["has_next"])
        self.assertEqual(len(queries), 2)

    async def test_invalid_parameters_and_unchecked_filter(self):
        for offset in ["invalid", "-100"]:
            context, queries = await self.render(f"offset={offset}&order=invalid&is_verified=false")
            self.assertEqual(queries[0]["offset"], ["0"])
            self.assertEqual(queries[0]["order"], ["created_at"])
            self.assertNotIn("is_verified", queries[0])
            self.assertFalse(context["verified_only"])
