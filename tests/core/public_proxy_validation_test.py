import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

import httpx2
from starlette.exceptions import HTTPException
from starlette.requests import Request

from maya.app import app
from maya.core import api, api_client, proxy_cache

RESOURCE_TYPES = ("collections", "people", "locations", "creators", "events", "organisations", "collectors")
INVALID_IDS = (
    "abc",
    "-1",
    "+1",
    "1.0",
    "%2e",
    "%2e%2e",
    "%252e%252e",
    "1%3fadmin=true",
    "1%23fragment",
    "1%5cusers",
    "1%2f..%2fusers",
    "1%00",
    "%D9%A1",  # Arabic-Indic digit, not an ASCII identifier.
)


class PublicProxyValidationTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend_requests = []

        def upstream(request):
            self.backend_requests.append(request)
            if request.url.path.endswith("/relations"):
                return httpx2.Response(200, json=[])
            return httpx2.Response(200, json={"id": "000123", "schema": "person", "display_label": "Public fixture"})

        backend = await self.enterAsyncContext(httpx2.AsyncClient(transport=httpx2.MockTransport(upstream)))
        self.enterContext(patch.object(api_client, "_shared_client", backend))
        # Record adapter tests must not read or write the site's persistent cache.
        self.enterContext(patch.object(proxy_cache, "PROXY_CACHE_EXPIRE", None))
        self.client = await self.enterAsyncContext(
            httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="https://aarhus.local")
        )

    async def assert_rejected_without_backend(self, path):
        self.backend_requests.clear()
        response = await self.client.get(path)
        self.assertEqual(response.status_code, 404, path)
        self.assertEqual(self.backend_requests, [], path)

    async def test_original_encoded_dot_bypass_never_reaches_backend(self):
        await self.assert_rejected_without_backend("/%2e%2e/users/json/api")

    async def test_resource_types_are_validated_for_html_and_both_json_formats(self):
        for resource_type in ("users", "%2e%2e", "%252e%252e", "people%3f", "people%23", "people%5c"):
            for suffix in ("", "/json/api", "/json/resource_and_types"):
                with self.subTest(resource_type=resource_type, suffix=suffix):
                    await self.assert_rejected_without_backend(f"/{resource_type}/123{suffix}")

    async def test_resource_ids_are_validated_for_html_and_both_json_formats(self):
        for resource_id in INVALID_IDS:
            for suffix in ("", "/json/api", "/json/resource_and_types"):
                with self.subTest(resource_id=resource_id, suffix=suffix):
                    await self.assert_rejected_without_backend(f"/people/{resource_id}{suffix}")

    async def test_record_and_relation_routes_reject_malformed_paths(self):
        for resource_id in INVALID_IDS:
            for path in (
                f"/records/{resource_id}",
                f"/records/{resource_id}/json/record_original",
                f"/records/{resource_id}/html/record",
                f"/relations/people/{resource_id}",
                f"/relations/records/{resource_id}",
            ):
                with self.subTest(path=path):
                    await self.assert_rejected_without_backend(path)
        for resource_type in ("users", "%2e%2e", "people%3f"):
            await self.assert_rejected_without_backend(f"/relations/{resource_type}/123")

    async def test_unsupported_json_formats_do_not_contact_backend(self):
        await self.assert_rejected_without_backend("/people/123/json/unknown")
        await self.assert_rejected_without_backend("/records/123/json/unknown")

    async def test_supported_resource_types_preserve_leading_zeroes(self):
        for resource_type in RESOURCE_TYPES:
            with self.subTest(resource_type=resource_type):
                self.backend_requests.clear()
                response = await self.client.get(f"/{resource_type}/000123/json/api")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["display_label"], "Public fixture")
                self.assertEqual(len(self.backend_requests), 1)
                self.assertEqual(self.backend_requests[0].url.path, f"{httpx2.URL(api.base_url).path}/proxy/{resource_type}/000123")

    async def test_people_html_and_formatted_json_still_work(self):
        for suffix in ("", "/json/resource_and_types"):
            with self.subTest(suffix=suffix):
                self.backend_requests.clear()
                response = await self.client.get(f"/people/000123{suffix}")
                self.assertEqual(response.status_code, 200)
                self.assertIn("Public fixture", response.text)
                self.assertEqual(len(self.backend_requests), 1)
                self.assertTrue(self.backend_requests[0].url.path.endswith("/proxy/people/000123"))

    async def test_relations_for_supported_resources_and_records_still_work(self):
        for resource_type in (*RESOURCE_TYPES, "records"):
            with self.subTest(resource_type=resource_type):
                self.backend_requests.clear()
                response = await self.client.get(f"/relations/{resource_type}/000123")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(self.backend_requests), 1)
                self.assertTrue(self.backend_requests[0].url.path.endswith(f"/proxy/{resource_type}/000123/relations"))

    async def test_adapters_reject_unsafe_paths_even_without_route_validation(self):
        request = Request({"type": "http", "session": {}})
        for resource_type in ("..", "users", "people?", "people#", "people\\"):
            for adapter in (api.proxies_get_resource, api.proxies_get_relations):
                with self.subTest(adapter=adapter.__name__, resource_type=resource_type):
                    with self.assertRaises(HTTPException) as error:
                        await adapter(request, resource_type, "123")
                    self.assertEqual(error.exception.status_code, 404)
                    self.assertEqual(self.backend_requests, [])
        for resource_id in ("", "..", "1?admin=true", "1#fragment", "1/../users", "1\\users", "١"):
            for adapter, args in (
                (api.proxies_get_resource, (request, "people", resource_id)),
                (api.proxies_get_relations, (request, "records", resource_id)),
                (api.proxies_record_get_by_id, (request, resource_id)),
            ):
                with self.subTest(adapter=adapter.__name__, resource_id=resource_id):
                    with self.assertRaises(HTTPException) as error:
                        await adapter(*args)
                    self.assertEqual(error.exception.status_code, 404)
                    self.assertEqual(self.backend_requests, [])

    async def test_record_adapter_preserves_valid_id(self):
        request = Request({"type": "http", "session": {}})
        record = await api.proxies_record_get_by_id(request, "000123")
        self.assertEqual(record["id"], "000123")
        self.assertEqual(len(self.backend_requests), 1)
        self.assertTrue(self.backend_requests[0].url.path.endswith("/proxy/records/000123"))
