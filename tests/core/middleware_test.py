import asyncio
import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from starlette.datastructures import URL

os.environ.setdefault("BASE_DIR", "sites/aarhus")

from maya.core.middleware import ConcurrencyLimitMiddleware, SameOriginMiddleware


class FakeRequest:
    method = "POST"
    headers = {"origin": "https://blocked.example"}
    url = URL("http://testserver/records/1")


class MiddlewareTest(IsolatedAsyncioTestCase):
    async def test_search_concurrency_limit_rejects_excess_request(self):
        middleware = ConcurrencyLimitMiddleware(app=None, max_concurrency=1, paths=["/search", "/search/json"], retry_after=7)
        first_request_started = asyncio.Event()
        finish_first_request = asyncio.Event()

        async def slow_search(_request):
            first_request_started.set()
            await finish_first_request.wait()
            return "first response"

        first_request = FakeRequest()
        first_request.method = "GET"
        first_request.url = URL("https://www.aarhusarkivet.dk/search?q=aarhus")
        first_task = asyncio.create_task(middleware.dispatch(first_request, slow_search))
        await first_request_started.wait()

        rejected_call_next = AsyncMock()
        rejected_request = FakeRequest()
        rejected_request.method = "GET"
        rejected_request.url = URL("https://www.aarhusarkivet.dk/search?q=archive")
        response = await middleware.dispatch(rejected_request, rejected_call_next)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.body, b"Too Many Requests")
        self.assertEqual(response.headers["retry-after"], "7")
        self.assertEqual(response.headers["cache-control"], "no-store")
        rejected_call_next.assert_not_called()

        finish_first_request.set()
        self.assertEqual(await first_task, "first response")

    async def test_search_concurrency_limit_covers_json_endpoint(self):
        middleware = ConcurrencyLimitMiddleware(app=None, max_concurrency=1, paths=["/search", "/search/json"])
        middleware._active_requests = 1
        request = FakeRequest()
        request.method = "GET"
        request.url = URL("https://www.aarhusarkivet.dk/search/json?q=aarhus")
        call_next = AsyncMock()

        response = await middleware.dispatch(request, call_next)

        self.assertEqual(response.status_code, 429)
        call_next.assert_not_called()

    async def test_search_concurrency_limit_does_not_limit_other_paths(self):
        middleware = ConcurrencyLimitMiddleware(app=None, max_concurrency=1, paths=["/search", "/search/json"])
        middleware._active_requests = 1
        request = FakeRequest()
        request.method = "GET"
        request.url = URL("https://www.aarhusarkivet.dk/records/1")
        call_next = AsyncMock(return_value="record response")

        response = await middleware.dispatch(request, call_next)

        self.assertEqual(response, "record response")
        call_next.assert_called_once_with(request)

    async def test_search_concurrency_limit_releases_slot_after_error(self):
        middleware = ConcurrencyLimitMiddleware(app=None, max_concurrency=1, paths=["/search", "/search/json"])
        request = FakeRequest()
        request.method = "GET"
        request.url = URL("https://www.aarhusarkivet.dk/search")
        failing_call_next = AsyncMock(side_effect=RuntimeError("search failed"))

        with self.assertRaisesRegex(RuntimeError, "search failed"):
            await middleware.dispatch(request, failing_call_next)

        successful_call_next = AsyncMock(return_value="search response")
        response = await middleware.dispatch(request, successful_call_next)

        self.assertEqual(response, "search response")
        successful_call_next.assert_called_once_with(request)

    async def test_same_origin_middleware_allows_configured_origin(self):
        middleware = SameOriginMiddleware(app=None, allowed_origins=["https://api.openaws.dk"])
        call_next = AsyncMock()
        call_next.return_value = "response"
        request = FakeRequest()
        request.headers = {"origin": "https://api.openaws.dk"}

        response = await middleware.dispatch(request, call_next)

        self.assertEqual(response, "response")
        call_next.assert_called_once_with(request)

    async def test_same_origin_middleware_allows_exempt_path_without_origin(self):
        middleware = SameOriginMiddleware(app=None, exempt_path_prefixes=["/webhook/"])
        call_next = AsyncMock()
        call_next.return_value = "response"
        request = FakeRequest()
        request.headers = {}
        request.url = URL("https://www.aarhusarkivet.dk/webhook/mail/token/verify")

        response = await middleware.dispatch(request, call_next)

        self.assertEqual(response, "response")
        call_next.assert_called_once_with(request)

    async def test_same_origin_middleware_logs_error_code_and_url_for_forbidden_origin(self):
        middleware = SameOriginMiddleware(app=None, allowed_origins=[])
        call_next = AsyncMock()
        request = FakeRequest()

        with patch("maya.core.middleware.log") as log:
            response = await middleware.dispatch(request, call_next)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.body, b'{"error":true,"message":"Forbidden. Bad Origin."}')
        call_next.assert_not_called()
        log.exception.assert_called_once_with(
            "Forbidden request from origin: https://blocked.example",
            extra={"error_code": 403, "error_url": "http://testserver/records/1"},
        )
