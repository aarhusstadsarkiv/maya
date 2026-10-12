import asyncio
import json

from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

import httpx2
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from maya.core import api_client, exception_handlers
from maya.core.middleware import ApiLogMiddleware, RequestBeginMiddleware


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
            api_client.collect_timings(),
            patch.object(api_client.httpx2, "AsyncClient", side_effect=lambda **kwargs: client_class(transport=transport, **kwargs)),
        ):
            async with api_client.get_async_client() as client:
                response = await client.get("https://api.example/records")
            self.assertEqual(response.json(), {"ok": True})
            self.assertGreaterEqual(api_client.get_time_used()["GET_/records"][0], 0)
            self.assertTrue(client.is_closed)

    async def test_shared_client_reuse_shutdown_and_authentication_isolation(self):
        seen = []

        async def respond(request):
            await asyncio.sleep(0)
            seen.append((request.headers.get("authorization"), request.headers.get("cookie")))
            return httpx2.Response(200, headers={"Set-Cookie": "session=private; Path=/"})

        client_class = httpx2.AsyncClient
        with patch.object(
            api_client.httpx2,
            "AsyncClient",
            side_effect=lambda **kwargs: client_class(transport=httpx2.MockTransport(respond), **kwargs),
        ) as create_client:
            async with api_client.client_lifespan():

                async def fetch(token):
                    async with api_client.get_async_client() as client:
                        await client.get("https://api.example/records", headers={"Authorization": token})
                        return client

                first, second = await asyncio.gather(fetch("Bearer first"), fetch("Bearer second"))
                self.assertIs(first, second)
                self.assertFalse(first.is_closed)
                async with api_client.get_async_client() as client:
                    response = await client.get("https://api.example/records")
                    self.assertEqual(response.cookies["session"], "private")
                self.assertEqual(len(first.cookies), 0)
                create_client.assert_called_once()
            self.assertTrue(first.is_closed)
            self.assertIsNone(api_client._shared_client)
        self.assertCountEqual(seen, [("Bearer first", None), ("Bearer second", None), (None, None)])

    async def test_connection_is_reused_across_api_calls(self):
        connections = 0
        disconnected = asyncio.Event()

        async def serve(reader, writer):
            nonlocal connections
            connections += 1
            try:
                while True:
                    await reader.readuntil(b"\r\n\r\n")
                    writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                    await writer.drain()
            except asyncio.IncompleteReadError:
                pass
            finally:
                writer.close()
                await writer.wait_closed()
                disconnected.set()

        server = await asyncio.start_server(serve, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            async with api_client.client_lifespan():
                for _ in range(2):
                    async with api_client.get_async_client() as client:
                        response = await client.get(f"http://127.0.0.1:{port}/records")
                        self.assertEqual(response.text, "OK")
            await asyncio.wait_for(disconnected.wait(), timeout=2)
        self.assertEqual(connections, 1)

    async def test_middleware_keeps_concurrent_request_timings_separate(self):
        async def upstream(request):
            await asyncio.sleep(0)
            return httpx2.Response(200, json={})

        async def endpoint(request):
            async with api_client.get_async_client() as client:
                await client.get("https://api.example" + request.url.path)
            return JSONResponse({})

        app = Starlette(
            routes=[Route("/{name}", endpoint)],
            middleware=[Middleware(ApiLogMiddleware), Middleware(RequestBeginMiddleware)],
        )
        client_class = httpx2.AsyncClient
        with (
            patch.object(
                api_client.httpx2,
                "AsyncClient",
                side_effect=lambda **kwargs: client_class(transport=httpx2.MockTransport(upstream), **kwargs),
            ),
            patch("maya.core.middleware.log") as log,
        ):
            async with api_client.client_lifespan():
                async with client_class(transport=httpx2.ASGITransport(app=app), base_url="http://testserver") as client:
                    first, second = await asyncio.gather(client.get("/first"), client.get("/second"))
                    self.assertEqual((first.status_code, second.status_code), (200, 200))
            logged = [json.loads(call.args[0])["api_calls"] for call in log.debug.call_args_list]
        self.assertCountEqual([list(timings) for timings in logged], [["GET_/first"], ["GET_/second"]])
        self.assertEqual(api_client.get_time_used(), {})

    async def test_shared_client_closes_after_lifespan_error(self):
        async with api_client.get_async_client() as standalone:
            self.assertFalse(standalone.is_closed)
        self.assertTrue(standalone.is_closed)
        with self.assertRaisesRegex(RuntimeError, "failed"):
            async with api_client.client_lifespan():
                async with api_client.get_async_client() as shared:
                    raise RuntimeError("failed")
        self.assertTrue(shared.is_closed)
        self.assertIsNone(api_client._shared_client)

    async def test_timings_are_optional_isolated_and_inherited_by_child_tasks(self):
        api_client.set_time_used("disabled", 1)
        self.assertEqual(api_client.get_time_used(), {})
        both_started = asyncio.Event()
        started = 0

        async def request(name):
            with api_client.collect_timings():

                async def child():
                    nonlocal started
                    started += 1
                    if started == 2:
                        both_started.set()
                    await both_started.wait()
                    api_client.set_time_used(name, 0.5)

                await asyncio.create_task(child())
                return api_client.get_time_used()

        first, second = await asyncio.gather(request("first"), request("second"))
        self.assertEqual(first, {"first": [0.5]})
        self.assertEqual(second, {"second": [0.5]})
        self.assertEqual(api_client.get_time_used(), {})

    async def test_timing_context_resets_after_error(self):
        with self.assertRaises(RuntimeError):
            with api_client.collect_timings():
                api_client.set_time_used("failed", 1)
                raise RuntimeError("failed")
        self.assertEqual(api_client.get_time_used(), {})


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
