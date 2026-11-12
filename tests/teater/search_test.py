"""The theatre resource hooks embed searches and persist their navigation state."""

import asyncio
import json
import os
from http.cookies import SimpleCookie
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from urllib.parse import parse_qsl

os.environ.setdefault("BASE_DIR", "sites/teater")
os.environ.setdefault("TEST", "TRUE")

import httpx2
from starlette.requests import Request
from starlette.responses import HTMLResponse

from maya.core import api_client
from maya.endpoints import endpoints_resources, endpoints_search
from sites.teater.hooks import Hooks


class TheatreResourceSearchTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.search_requests = []

        def upstream(request):
            if request.url.path.endswith("/relations"):
                return httpx2.Response(200, json=[])
            self.search_requests.append(parse_qsl(request.url.params["params"], keep_blank_values=True))
            return httpx2.Response(
                200,
                json={"result": [], "total": 0, "start": 0, "size": 10, "active_facets": {}, "facets_resolved": {}},
            )

        backend = await self.enterAsyncContext(httpx2.AsyncClient(transport=httpx2.MockTransport(upstream)))
        self.enterContext(patch.object(api_client, "_shared_client", backend))
        self.enterContext(patch.object(endpoints_search, "get_hooks", side_effect=Hooks))

    def make_request(self, resource_type, resource_id, query=b"", cookie=b""):
        return Request(
            {
                "type": "http",
                "method": "GET",
                "path": f"/{resource_type}/{resource_id}",
                "path_params": {"resource_type": resource_type, "id": resource_id},
                "endpoint": endpoints_resources.get_resource,
                "query_string": query,
                "headers": [(b"host", b"teater.local"), (b"cookie", cookie)],
                "session": {},
            }
        )

    def search_cookie(self, response):
        cookies = SimpleCookie()
        for header in response.headers.getlist("set-cookie"):
            cookies.load(header)
        return json.loads(cookies["search"].value)

    async def test_event_and_person_pages_use_ten_results_despite_browser_preferences(self):
        for resource_type, resource_id in (("events", "111818"), ("people", "116693")):
            for query, cookie in ((b"", b""), (b"", b"size=50"), (b"size=50", b"size=100")):
                with self.subTest(resource_type=resource_type, query=query, cookie=cookie):
                    self.search_requests.clear()
                    request = self.make_request(resource_type, resource_id, query, cookie)
                    resource = await Hooks(request).after_get_resource(resource_type, {"id": "000" + resource_id})
                    self.assertIn("search_result", resource)
                    self.assertEqual(len(self.search_requests), 1)
                    self.assertIn((resource_type, resource_id), self.search_requests[0])
                    self.assertEqual([pair for pair in self.search_requests[0] if pair[0] == "size"], [("size", "10")])
                    self.assertIn(("curators", "4"), self.search_requests[0])
                    response = await Hooks(request).before_response(HTMLResponse("resource page"))
                    saved = self.search_cookie(response)
                    self.assertIn(["size", "10"], saved["query_params"])
                    self.assertIn([resource_type, resource_id], saved["query_params"])
                    self.assertIn([resource_type, resource_id], request.session["record_navigation_cache"]["query_params"])

    async def test_concurrent_pages_do_not_share_search_cookies(self):
        event = self.make_request("events", "111818")
        person = self.make_request("people", "116693")
        await asyncio.gather(
            Hooks(event).after_get_resource("events", {"id": "111818"}),
            Hooks(person).after_get_resource("people", {"id": "116693"}),
        )
        for request, expected, unexpected in (
            (event, ["events", "111818"], ["people", "116693"]),
            (person, ["people", "116693"], ["events", "111818"]),
        ):
            response = await Hooks(request).before_response(HTMLResponse("resource page"))
            params = self.search_cookie(response)["query_params"]
            self.assertIn(expected, params)
            self.assertNotIn(unexpected, params)

    async def test_error_or_missing_context_does_not_set_search_cookie(self):
        successful_request = self.make_request("events", "111818")
        await Hooks(successful_request).after_get_resource("events", {"id": "111818"})
        new_request = self.make_request("people", "116693")
        for request, status in ((successful_request, 400), (new_request, 400), (new_request, 200)):
            response = await Hooks(request).before_response(HTMLResponse("resource response", status_code=status))
            self.assertEqual(response.status_code, status)
            self.assertNotIn("set-cookie", response.headers)
