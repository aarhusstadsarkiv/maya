import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from starlette.datastructures import URL

os.environ.setdefault("BASE_DIR", "sites/aarhus")

from maya.core.middleware import SameOriginMiddleware


class FakeRequest:
    method = "POST"
    headers = {"origin": "https://blocked.example"}
    url = URL("http://testserver/records/1")


class MiddlewareTest(IsolatedAsyncioTestCase):
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
