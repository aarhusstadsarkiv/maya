from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from maya.core.dataclasses import SearchCookie
from maya.endpoints.endpoints_records import _get_record_pagination


class TestRecordPagination(IsolatedAsyncioTestCase):
    async def test_uses_session_cache_for_prev_next_on_same_page(self):
        request = SimpleNamespace(
            query_params={"search": "10"},
            cookies={},
            session={
                "search_result": {
                    "query_params": [["size", "20"], ["q", "test"]],
                    "start": 0,
                    "size": 20,
                    "total": 25,
                    "record_ids": list(range(1, 21)),
                }
            },
        )
        search_cookie = SearchCookie(
            search_query_str="q=test&size=20&",
            query_params=[("size", "20"), ("q", "test")],
            total=25,
            q="test",
        )

        with (
            patch("maya.endpoints.endpoints_records.cookie.get_search_cookie", return_value=search_cookie),
            patch("maya.endpoints.endpoints_records.api.proxies_records", new=AsyncMock()) as proxies_records,
        ):
            pagination = await _get_record_pagination(request)

        self.assertEqual(pagination.current_page, 10)
        self.assertEqual(pagination.prev_page, 9)
        self.assertEqual(pagination.next_page, 11)
        self.assertEqual(pagination.prev_record, 9)
        self.assertEqual(pagination.next_record, 11)
        proxies_records.assert_not_awaited()

    async def test_fetches_next_page_when_navigation_crosses_cached_boundary(self):
        request = SimpleNamespace(
            query_params={"search": "20"},
            cookies={},
            session={
                "search_result": {
                    "query_params": [["size", "20"], ["q", "test"]],
                    "start": 0,
                    "size": 20,
                    "total": 25,
                    "record_ids": list(range(1, 21)),
                }
            },
        )
        search_cookie = SearchCookie(
            search_query_str="q=test&size=20&",
            query_params=[("size", "20"), ("q", "test")],
            total=25,
            q="test",
        )
        next_page_result = {
            "start": 20,
            "size": 20,
            "total": 25,
            "result": [{"id": record_id} for record_id in range(21, 26)],
        }

        with (
            patch("maya.endpoints.endpoints_records.cookie.get_search_cookie", return_value=search_cookie),
            patch("maya.endpoints.endpoints_records.api.proxies_records", new=AsyncMock(return_value=next_page_result)) as proxies_records,
        ):
            pagination = await _get_record_pagination(request)

        self.assertEqual(pagination.current_page, 20)
        self.assertEqual(pagination.prev_record, 19)
        self.assertEqual(pagination.next_record, 21)
        proxies_records.assert_awaited_once_with(request, [("size", "20"), ("q", "test"), ("start", "20")])
        self.assertEqual(request.session["search_result"]["start"], 20)
        self.assertEqual(request.session["search_result"]["record_ids"], [21, 22, 23, 24, 25])
