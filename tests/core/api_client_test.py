from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

import httpx2
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from maya.core import api_client, exception_handlers


class TestApiClient(IsolatedAsyncioTestCase):
    async def test_request_headers_timeout_and_timing(self):
        def respond(request):
            self.assertEqual(request.headers["x-key"], "test-key")
            self.assertEqual(request.headers["x-client"], "test-client")
            self.assertEqual(request.headers["x-client-domain-url"], "https://client.example")
            self.assertEqual(request.headers["origin"], "https://client.example")
            self.assertEqual(request.extensions["timeout"]["read"], 7)
            return httpx2.Response(200, json={"ok": True})

        client_class = httpx2.AsyncClient
        transport = httpx2.MockTransport(respond)
        with (
            patch.dict(api_client.settings, api_key="test-key", client_name="test-client", client_url="https://client.example"),
            patch.object(api_client, "REQUEST_TIME_USED", {}),
            patch.object(api_client.httpx2, "AsyncClient", side_effect=lambda **kwargs: client_class(transport=transport, **kwargs)),
        ):
            async with api_client.get_async_client() as client:
                response = await client.get("https://api.example/records")
            self.assertEqual(response.json(), {"ok": True})
            self.assertGreaterEqual(api_client.REQUEST_TIME_USED["GET_/records"][0], 0)
            self.assertTrue(client.is_closed)


class TestHttpExceptionHandlers(TestCase):
    def test_httpx2_errors_reach_application_handlers(self):
        upstream_request = httpx2.Request("GET", "https://api.example/records")
        upstream_response = httpx2.Response(503, request=upstream_request)
        with self.assertRaises(httpx2.HTTPStatusError) as raised:
            upstream_response.raise_for_status()

        for error, status in [(raised.exception, 503), (httpx2.ReadTimeout("Timed out", request=upstream_request), 504)]:
            with self.subTest(status=status):

                async def endpoint(request):
                    raise error

                app = Starlette(routes=[Route("/", endpoint)], exception_handlers=exception_handlers.exception_handlers)
                with (
                    patch.object(exception_handlers, "get_context", new_callable=AsyncMock, return_value={}),
                    patch.object(exception_handlers, "templates") as templates,
                    patch.object(exception_handlers, "log"),
                    TestClient(app) as client,
                ):
                    templates.TemplateResponse.return_value = JSONResponse({}, status_code=status)
                    response = client.get("/")
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(templates.TemplateResponse.call_args.kwargs["status_code"], status)
