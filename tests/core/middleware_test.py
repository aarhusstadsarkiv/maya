import asyncio
import os
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from starlette.datastructures import URL

os.environ.setdefault("BASE_DIR", "sites/aarhus")

from maya.core.logging_context import get_client_ip
from maya.core.middleware import AccessLogMiddleware, ConcurrencyLimitMiddleware, SameOriginMiddleware


class FakeRequest:
    method = "POST"
    headers = {"origin": "https://blocked.example"}
    url = URL("http://testserver/records/1")


class MiddlewareTest(IsolatedAsyncioTestCase):
    async def test_access_log_exposes_client_ip_to_request_logs_and_resets_it(self):
        middleware = AccessLogMiddleware(app=None)
        request = FakeRequest()
        request.method = "GET"
        request.headers = {"user-agent": "test-agent"}
        request.url = URL("https://www.aarhusarkivet.dk/records/1")
        request.client = SimpleNamespace(host="203.0.113.4", port=0)

        async def call_next(_request):
            self.assertEqual(get_client_ip(), "203.0.113.4")
            return SimpleNamespace(status_code=200)

        with patch("maya.core.middleware.access_log") as access_log:
            response = await middleware.dispatch(request, call_next)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(get_client_ip())
        self.assertIn('203.0.113.4:0 - "GET /records/1" 200', access_log.info.call_args.args[0])

    async def test_search_concurrency_limit_rejects_excess_request(self):
        middleware = ConcurrencyLimitMiddleware(
            app=None,
            limits=[
                {"max": 1, "retry_after": 7, "paths": ["/search", "/search/json"]},
                {"max": 2, "retry_after": 5, "paths": ["*"]},
            ],
        )
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

        record_request = FakeRequest()
        record_request.url = URL("https://www.aarhusarkivet.dk/records/1")
        record_call_next = AsyncMock(return_value="record response")
        record_response = await middleware.dispatch(record_request, record_call_next)

        self.assertEqual(record_response, "record response")
        record_call_next.assert_called_once_with(record_request)

        finish_first_request.set()
        self.assertEqual(await first_task, "first response")

    async def test_search_concurrency_limit_covers_json_endpoint(self):
        middleware = ConcurrencyLimitMiddleware(
            app=None,
            limits=[{"max": 1, "retry_after": 5, "paths": ["/search", "/search/json"]}],
        )
        first_request_started = asyncio.Event()
        finish_first_request = asyncio.Event()

        async def slow_search(_request):
            first_request_started.set()
            await finish_first_request.wait()
            return "first response"

        search_request = FakeRequest()
        search_request.url = URL("https://www.aarhusarkivet.dk/search")
        first_task = asyncio.create_task(middleware.dispatch(search_request, slow_search))
        await first_request_started.wait()

        json_request = FakeRequest()
        json_request.url = URL("https://www.aarhusarkivet.dk/search/json?q=aarhus")
        call_next = AsyncMock()
        response = await middleware.dispatch(json_request, call_next)

        self.assertEqual(response.status_code, 429)
        call_next.assert_not_called()

        finish_first_request.set()
        await first_task

    async def test_search_concurrency_limit_does_not_limit_other_paths(self):
        middleware = ConcurrencyLimitMiddleware(
            app=None,
            limits=[{"max": 1, "retry_after": 5, "paths": ["/search", "/search/json"]}],
        )
        request = FakeRequest()
        request.url = URL("https://www.aarhusarkivet.dk/records/1")
        call_next = AsyncMock(return_value="record response")

        response = await middleware.dispatch(request, call_next)

        self.assertEqual(response, "record response")
        call_next.assert_called_once_with(request)

    async def test_search_concurrency_limit_releases_slot_after_error(self):
        middleware = ConcurrencyLimitMiddleware(
            app=None,
            limits=[{"max": 1, "retry_after": 5, "paths": ["/search", "/search/json"]}],
        )
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

    async def test_global_wildcard_limits_all_paths(self):
        middleware = ConcurrencyLimitMiddleware(
            app=None,
            limits=[{"max": 1, "retry_after": 9, "paths": ["*"]}],
        )
        first_request_started = asyncio.Event()
        finish_first_request = asyncio.Event()

        async def slow_request(_request):
            first_request_started.set()
            await finish_first_request.wait()
            return "first response"

        record_request = FakeRequest()
        record_request.url = URL("https://www.aarhusarkivet.dk/records/1")
        first_task = asyncio.create_task(middleware.dispatch(record_request, slow_request))
        await first_request_started.wait()

        home_request = FakeRequest()
        home_request.url = URL("https://www.aarhusarkivet.dk/")
        call_next = AsyncMock()
        response = await middleware.dispatch(home_request, call_next)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "9")
        call_next.assert_not_called()

        finish_first_request.set()
        await first_task

    async def test_trailing_wildcard_limits_matching_prefix(self):
        middleware = ConcurrencyLimitMiddleware(
            app=None,
            limits=[{"max": 1, "retry_after": 5, "paths": ["/records/*"]}],
        )
        first_request_started = asyncio.Event()
        finish_first_request = asyncio.Event()

        async def slow_record(_request):
            first_request_started.set()
            await finish_first_request.wait()
            return "first response"

        first_request = FakeRequest()
        first_request.url = URL("https://www.aarhusarkivet.dk/records/1")
        first_task = asyncio.create_task(middleware.dispatch(first_request, slow_record))
        await first_request_started.wait()

        second_request = FakeRequest()
        second_request.url = URL("https://www.aarhusarkivet.dk/records/2")
        call_next = AsyncMock()
        response = await middleware.dispatch(second_request, call_next)

        self.assertEqual(response.status_code, 429)
        call_next.assert_not_called()

        finish_first_request.set()
        await first_task

    async def test_excluded_path_uses_its_own_limit(self):
        middleware = ConcurrencyLimitMiddleware(
            app=None,
            limits=[
                {"max": 2, "retry_after": 5, "paths": ["/static/*"]},
                {"max": 1, "retry_after": 5, "paths": ["*"], "exclude_paths": ["/static/*"]},
            ],
        )
        global_request_started = asyncio.Event()
        finish_global_request = asyncio.Event()

        async def slow_global_request(_request):
            global_request_started.set()
            await finish_global_request.wait()
            return "global response"

        record_request = FakeRequest()
        record_request.url = URL("https://www.aarhusarkivet.dk/records/1")
        global_task = asyncio.create_task(middleware.dispatch(record_request, slow_global_request))
        await global_request_started.wait()

        static_request = FakeRequest()
        static_request.url = URL("https://www.aarhusarkivet.dk/static/css/default.css")
        static_call_next = AsyncMock(return_value="static response")
        response = await middleware.dispatch(static_request, static_call_next)

        self.assertEqual(response, "static response")
        static_call_next.assert_called_once_with(static_request)

        blocked_record_request = FakeRequest()
        blocked_record_request.url = URL("https://www.aarhusarkivet.dk/records/2")
        blocked_call_next = AsyncMock()
        blocked_response = await middleware.dispatch(blocked_record_request, blocked_call_next)

        self.assertEqual(blocked_response.status_code, 429)
        blocked_call_next.assert_not_called()

        finish_global_request.set()
        await global_task

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
        request.client = SimpleNamespace(host="203.0.113.4", port=0)

        with patch("maya.core.middleware.log") as log:
            response = await middleware.dispatch(request, call_next)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.body, b'{"error":true,"message":"Forbidden. Bad Origin."}')
        call_next.assert_not_called()
        log.exception.assert_called_once_with(
            "Forbidden request from origin: https://blocked.example",
            extra={
                "client_ip": "203.0.113.4",
                "error_code": 403,
                "error_url": "http://testserver/records/1",
            },
        )
