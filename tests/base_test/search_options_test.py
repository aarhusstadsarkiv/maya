import unittest
from unittest.mock import patch

from starlette.requests import Request

from maya.endpoints.endpoints_search import get_size_sort_view


def make_request(query_string: bytes = b"", cookie: bytes | None = None) -> Request:
    headers = []
    if cookie is not None:
        headers.append((b"cookie", cookie))

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/search",
            "query_string": query_string,
            "headers": headers,
        }
    )


class TestSearchOptions(unittest.TestCase):
    def test_accepts_supported_sort_and_view(self):
        request = make_request(b"size=50&sort=_score&view=grid")

        self.assertEqual(get_size_sort_view(request), ("50", "_score", "grid"))

    def test_invalid_query_values_fall_back_to_configured_defaults(self):
        request = make_request(b"sort=%0D%0ASet-Cookie%3Aevil%3D1&view=%00")

        with patch.dict(
            "maya.endpoints.endpoints_search.settings",
            {"search_default_sort": "created_at", "search_default_view": "gallery"},
        ):
            self.assertEqual(get_size_sort_view(request), ("20", "created_at", "gallery"))

    def test_invalid_cookie_values_fall_back_to_defaults(self):
        request = make_request(cookie=b"sort=invalid; view=invalid")

        with patch.dict(
            "maya.endpoints.endpoints_search.settings",
            {"search_default_sort": "date_to", "search_default_view": "grid"},
        ):
            self.assertEqual(get_size_sort_view(request), ("20", "date_to", "grid"))

    def test_invalid_configured_defaults_use_safe_defaults(self):
        request = make_request()

        with patch.dict(
            "maya.endpoints.endpoints_search.settings",
            {"search_default_sort": "invalid", "search_default_view": "invalid"},
        ):
            self.assertEqual(get_size_sort_view(request), ("20", "date_from", "list"))
