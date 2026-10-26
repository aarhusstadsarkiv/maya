import json
import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

import httpx2
from bs4 import BeautifulSoup

from maya.app import app
from maya.core import api_client


class VerifyEmailResendTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.verification_requests = []
        self.user = {
            "id": "resend-test-user",
            "email": "user@example.invalid",
            "display_name": "Test User",
            "is_active": True,
            "is_verified": False,
            "permissions": [{"name": "user", "grant_id": 1}],
        }

        def upstream(request):
            if request.url.path.endswith("/auth/jwt/login"):
                return httpx2.Response(200, json={"access_token": "resend-test-token", "token_type": "bearer"})
            if request.url.path.endswith("/users/me"):
                if request.headers.get("authorization") == "Bearer resend-test-token":
                    return httpx2.Response(200, json=self.user)
                return httpx2.Response(401, json={"detail": "Unauthorized"})
            if request.url.path.endswith("/auth/request-verify-token"):
                self.verification_requests.append(request)
                return httpx2.Response(202, json={})
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
        response = await self.client.post("/auth/login", data={"email": self.user["email"], "password": "fixture"})
        self.assertFalse(response.json()["error"])

    async def test_profile_offers_post_form(self):
        response = await self.client.get("/auth/me")
        self.assertEqual(response.status_code, 200)
        page = BeautifulSoup(response.text, "html.parser")
        form = page.select_one('form[action="/auth/send-verify-email"]')
        self.assertIsNotNone(form)
        self.assertEqual(form.get("method", "").lower(), "post")
        self.assertIsNotNone(form.select_one('button[type="submit"]'))
        self.assertIsNone(page.select_one('a[href="/auth/send-verify-email"]'))
        self.assertEqual(self.verification_requests, [])

    async def test_same_origin_form_submission_sends_once_and_redirects_to_profile(self):
        response = await self.client.post("/auth/send-verify-email", data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.history), 1)
        self.assertEqual(response.history[0].status_code, 303)
        self.assertEqual(response.request.method, "GET")
        self.assertEqual(response.url.path, "/auth/me")
        self.assertEqual(response.url.query, b"sent_mail=1")
        self.assertEqual(len(self.verification_requests), 1)
        self.assertEqual(self.verification_requests[0].method, "POST")
        self.assertEqual(json.loads(self.verification_requests[0].content), {"email": self.user["email"]})
        self.assertNotIn('action="/auth/send-verify-email"', response.text)

    async def test_get_and_head_cannot_send_mail(self):
        for method in ("GET", "HEAD"):
            with self.subTest(method=method):
                response = await self.client.request(method, "/auth/send-verify-email", headers={"Origin": "https://untrusted.example"})
                # The catch-all public resource route may turn an unsupported
                # method into a 404 instead of the router's usual 405.
                self.assertIn(response.status_code, (404, 405))
                self.assertEqual(self.verification_requests, [])

    async def test_post_requires_a_trusted_origin(self):
        for origin in (None, "null", "https://untrusted.example"):
            with self.subTest(origin=origin):
                request = self.client.build_request("POST", "/auth/send-verify-email", data={})
                if origin is None:
                    del request.headers["origin"]
                else:
                    request.headers["origin"] = origin
                response = await self.client.send(request)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(self.verification_requests, [])

    async def test_anonymous_post_cannot_send_mail(self):
        self.client.cookies.clear()
        await self.client.post("/auth/send-verify-email", data={})
        self.assertEqual(self.verification_requests, [])
