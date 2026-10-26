import json
import os
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch
from urllib.parse import quote_plus

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

import httpx2

from maya.app import app
from maya.core import api_client
from maya.core.auth import sanitize_next_url

UNSAFE_REDIRECTS = (
    "https://attacker.example/proof",
    "//attacker.example/proof",
    "///attacker.example/proof",
    "////attacker.example/proof",
    "/\\attacker.example/proof",
    "/\t/attacker.example/proof",
    " /search",
    "/auth/login?next=/records/1",
)
SAFE_REDIRECTS = (
    "/",
    "/search?q=city&content_types=1",
    "/records/000000001#details",
    "/search?next=https%3A%2F%2Fexample.invalid%2F",
)


class SanitizeNextUrlTest(TestCase):
    def test_preserves_local_paths_queries_and_fragments(self):
        for target in SAFE_REDIRECTS:
            with self.subTest(target=target):
                self.assertEqual(sanitize_next_url(target), target)

    def test_rejects_external_ambiguous_and_recursive_destinations(self):
        for target in (*UNSAFE_REDIRECTS, None, "", "search", "\\attacker.example", "/search?q=\\bad"):
            with self.subTest(target=target):
                self.assertIsNone(sanitize_next_url(target))

    def test_rejects_control_characters_before_url_parsing(self):
        for codepoint in (*range(32), 127):
            for target in (f"/{chr(codepoint)}/attacker.example", f"/search?q={chr(codepoint)}"):
                with self.subTest(target=target):
                    self.assertIsNone(sanitize_next_url(target))


class LoginRedirectTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        def upstream(request):
            if request.url.path.endswith("/auth/jwt/login"):
                return httpx2.Response(200, json={"access_token": "redirect-test-token", "token_type": "bearer"})
            if request.url.path.endswith("/users/me"):
                return httpx2.Response(401, json={"detail": "Unauthorized"})
            raise AssertionError(f"Unexpected backend request: {request.method} {request.url.path}")

        backend = await self.enterAsyncContext(httpx2.AsyncClient(transport=httpx2.MockTransport(upstream)))
        self.enterContext(patch.object(api_client, "_shared_client", backend))
        self.client = await self.enterAsyncContext(
            httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                base_url="https://aarhus.local",
                headers={"Origin": "https://aarhus.local"},
            )
        )

    async def test_login_form_replaces_unsafe_destinations(self):
        for target in UNSAFE_REDIRECTS:
            with self.subTest(target=target):
                response = await self.client.get("/auth/login", params={"next": target})
                self.assertEqual(response.status_code, 200)
                self.assertIn('action="/auth/login?next=%2Fsearch"', response.text)

    async def test_login_form_preserves_internal_destination(self):
        target = "/records/000000001?view=details#images"
        response = await self.client.get("/auth/login", params={"next": target})
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'action="/auth/login?next={quote_plus(target)}"', response.text)

    async def test_successful_login_replaces_unsafe_destinations(self):
        for target in UNSAFE_REDIRECTS:
            with self.subTest(target=target):
                response = await self.client.post(
                    "/auth/login",
                    params={"next": target},
                    data={
                        "email": "user@example.invalid",
                        "password": "fixture",
                    },
                )
                self.assertEqual(response.json(), {"error": False, "redirect": "/search"})

    async def test_successful_login_preserves_internal_destinations(self):
        for target in SAFE_REDIRECTS:
            with self.subTest(target=target):
                response = await self.client.post(
                    "/auth/login",
                    params={"next": target},
                    data={
                        "email": "user@example.invalid",
                        "password": "fixture",
                    },
                )
                self.assertEqual(response.json(), {"error": False, "redirect": target})

    async def test_unsafe_destination_preserves_last_search_fallback(self):
        self.client.cookies.set("search", json.dumps({"search_query_str": "q=city&content_types=1", "query_params": []}))
        response = await self.client.post(
            "/auth/login",
            params={"next": "/\\attacker.example/proof"},
            data={
                "email": "user@example.invalid",
                "password": "fixture",
            },
        )
        self.assertEqual(response.json(), {"error": False, "redirect": "/search?q=city&content_types=1"})
