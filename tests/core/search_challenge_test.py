import hashlib
import re
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

import httpx2
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from maya.core.search_challenge import COOKIE, NONCE_COOKIE, VERIFY_PATH, SearchChallengeMiddleware


class SearchChallengeTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = 0

        async def search(request):
            self.calls += 1
            return PlainTextResponse("search results")

        app = Starlette(
            routes=[Route("/search", search), Route("/search/json", search), Route("/records/1", search)],
            middleware=[Middleware(SearchChallengeMiddleware, secret="test-secret")],
        )
        self.client = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="https://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def challenge(self):
        with patch("maya.core.search_challenge.time.time", return_value=1000):
            response = await self.client.get("/search?subjects=3&subjects=64&q=%3Cscript%3E")
        token = re.search(r'name="token" value="([^"]+)"', response.text)[1]
        solution = next(str(n) for n in range(1000000) if hashlib.sha256(f"{token}:{n}".encode()).hexdigest().startswith("000"))
        return response, {"token": token, "solution": solution}

    async def verify(self, fields, now=1003, **kwargs):
        with patch("maya.core.search_challenge.time.time", return_value=now):
            return await self.client.post(VERIFY_PATH, data=fields, **kwargs)

    async def test_challenge_prevents_search_and_preserves_filters_after_verification(self):
        response, fields = await self.challenge()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls, 0)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("script-src 'nonce-", response.headers["content-security-policy"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])
        response = await self.verify(fields)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/search?subjects=3&subjects=64&q=%3Cscript%3E")
        self.assertIn("Max-Age=1800", response.headers["set-cookie"])
        with patch("maya.core.search_challenge.time.time", return_value=1004):
            response = await self.client.get(response.headers["location"])
            json_response = await self.client.get("/search/json")
        self.assertEqual(response.text, "search results")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(self.calls, 2)

    async def test_wait_is_enforced_on_server(self):
        _, fields = await self.challenge()
        self.assertEqual((await self.verify(fields, now=1001.99)).status_code, 400)
        self.assertEqual((await self.verify(fields, now=1002)).status_code, 303)

    async def test_tampered_expired_and_wrong_proof_are_rejected(self):
        _, fields = await self.challenge()
        self.assertEqual((await self.verify({**fields, "token": fields["token"] + "x"})).status_code, 400)
        self.assertEqual((await self.verify(fields, now=1301)).status_code, 400)
        bad = next(str(n) for n in range(100) if not hashlib.sha256(f'{fields["token"]}:{n}'.encode()).hexdigest().startswith("000"))
        self.assertEqual((await self.verify({**fields, "solution": bad})).status_code, 400)
        self.assertEqual(self.calls, 0)

    async def test_nonce_and_same_origin_are_required(self):
        _, fields = await self.challenge()
        self.assertEqual((await self.verify(fields, headers={"Origin": "https://evil.example"})).status_code, 403)
        self.client.cookies.delete(NONCE_COOKIE)
        self.assertEqual((await self.verify(fields)).status_code, 400)

    async def test_json_cannot_bypass_and_unrelated_routes_are_unchanged(self):
        response = await self.client.get("/search/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["challenge_url"], "/search")
        self.assertEqual(self.calls, 0)
        self.assertEqual((await self.client.get("/records/1")).text, "search results")

    async def test_clearance_cannot_be_forged_or_reused_after_expiry(self):
        self.client.cookies.set(COOKIE, "verified")
        self.assertIn("Checking your browser", (await self.client.get("/search")).text)
        self.client.cookies.clear()
        _, fields = await self.challenge()
        await self.verify(fields)
        with patch("maya.core.search_challenge.time.time", return_value=2804):
            self.assertIn("Checking your browser", (await self.client.get("/search")).text)
        self.assertEqual(self.calls, 0)

    async def test_verification_request_limits(self):
        self.assertEqual((await self.client.get(VERIFY_PATH)).status_code, 405)
        self.assertEqual((await self.client.post(VERIFY_PATH, content=b"x" * 16385)).status_code, 413)
        self.assertEqual((await self.client.post(VERIFY_PATH, content=b"token=invalid")).status_code, 400)

    async def test_signed_external_redirect_is_rejected(self):
        _, fields = await self.challenge()
        signer = SearchChallengeMiddleware(None, "test-secret").challenge
        with patch("maya.core.search_challenge.time.time", return_value=1000):
            data = signer.loads(fields["token"])
            data["target"] = "//evil.example"
            token = signer.dumps(data)
        solution = next(str(n) for n in range(1000000) if hashlib.sha256(f"{token}:{n}".encode()).hexdigest().startswith("000"))
        self.assertEqual((await self.verify({"token": token, "solution": solution})).status_code, 400)
