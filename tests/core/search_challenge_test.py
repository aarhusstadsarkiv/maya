import hashlib
import re
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

import httpx2
from itsdangerous import URLSafeTimedSerializer
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from maya.core.search_challenge import COOKIE, NONCE_COOKIE, VERIFY_PATH, SearchChallengeMiddleware


class SearchChallengeTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = 0
        self.events = []

        async def search(request):
            self.calls += 1
            return PlainTextResponse("search results")

        app = Starlette(
            routes=[Route("/search", search), Route("/search/json", search), Route("/records/1", search)],
            middleware=[
                Middleware(
                    SearchChallengeMiddleware,
                    secret="test-secret",
                    allowed_ips=["198.51.100.6"] + [f"192.0.2.{n}" for n in range(34, 39)],
                )
            ],
        )

        async def observed(scope, receive, send):
            await app(scope, receive, send)
            self.events.append(dict(scope.get("state", {})))

        self.transport = httpx2.ASGITransport(app=observed, client=("203.0.113.10", 1234))
        self.client = httpx2.AsyncClient(transport=self.transport, base_url="https://testserver")

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

    def assert_outcome(self, outcome, reason=None):
        self.assertEqual(self.events[-1], {"challenge_outcome": outcome, "challenge_reason": reason})

    async def test_challenge_prevents_search_and_preserves_filters_after_verification(self):
        response, fields = await self.challenge()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls, 0)
        self.assert_outcome("issued", "missing_cookie")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("script-src 'nonce-", response.headers["content-security-policy"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])
        response = await self.verify(fields)
        self.assertEqual(response.status_code, 303)
        self.assert_outcome("passed")
        self.assertEqual(response.headers["location"], "/search?subjects=3&subjects=64&q=%3Cscript%3E")
        self.assertIn("Max-Age=1800", response.headers["set-cookie"])
        with patch("maya.core.search_challenge.time.time", return_value=1004):
            response = await self.client.get(response.headers["location"])
            json_response = await self.client.get("/search/json")
        self.assertEqual(response.text, "search results")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(self.calls, 2)
        self.assert_outcome("allowed")

    async def test_wait_is_enforced_on_server(self):
        _, fields = await self.challenge()
        self.assertEqual((await self.verify(fields, now=1001.99)).status_code, 400)
        self.assert_outcome("failed", "too_early")
        self.assertEqual((await self.verify(fields, now=1002)).status_code, 303)

    async def test_tampered_expired_and_wrong_proof_are_rejected(self):
        _, fields = await self.challenge()
        self.assertEqual((await self.verify({**fields, "token": fields["token"] + "x"})).status_code, 400)
        self.assert_outcome("failed", "invalid_signature")
        self.assertEqual((await self.verify(fields, now=1301)).status_code, 400)
        self.assert_outcome("failed", "expired_challenge")
        bad = next(str(n) for n in range(100) if not hashlib.sha256(f'{fields["token"]}:{n}'.encode()).hexdigest().startswith("000"))
        self.assertEqual((await self.verify({**fields, "solution": bad})).status_code, 400)
        self.assert_outcome("failed", "invalid_proof")
        self.assertEqual(self.calls, 0)

    async def test_nonce_and_same_origin_are_required(self):
        _, fields = await self.challenge()
        self.assertEqual((await self.verify(fields, headers={"Origin": "https://evil.example"})).status_code, 403)
        self.assert_outcome("failed", "invalid_origin")
        self.client.cookies.delete(NONCE_COOKIE)
        self.assertEqual((await self.verify(fields)).status_code, 400)
        self.assert_outcome("failed", "nonce_mismatch")

    async def test_json_cannot_bypass_and_unrelated_routes_are_unchanged(self):
        response = await self.client.get("/search/json")
        self.assertEqual(response.status_code, 403)
        self.assert_outcome("failed", "missing_cookie")
        self.assertEqual(response.json()["challenge_url"], "/search")
        self.assertEqual(self.calls, 0)
        self.assertEqual((await self.client.get("/records/1")).text, "search results")
        self.assertEqual(self.events[-1], {})

    async def test_clearance_cannot_be_forged_or_reused_after_expiry(self):
        self.client.cookies.set(COOKIE, "verified")
        self.assertIn("Checking your browser", (await self.client.get("/search")).text)
        self.assert_outcome("issued", "invalid_signature")
        self.client.cookies.clear()
        _, fields = await self.challenge()
        await self.verify(fields)
        expired_cookie = self.client.cookies.get(COOKIE)
        with patch("maya.core.search_challenge.time.time", return_value=2804):
            response = await self.client.get("/search", headers={"Cookie": f"{COOKIE}={expired_cookie}"})
            self.assertIn("Checking your browser", response.text)
            self.assert_outcome("issued", "expired_cookie")
        self.assertEqual(self.calls, 0)

    async def test_verification_request_limits(self):
        self.assertEqual((await self.client.get(VERIFY_PATH)).status_code, 405)
        self.assert_outcome("failed", "invalid_method")
        self.assertEqual((await self.client.post(VERIFY_PATH, content=b"x" * 16385)).status_code, 413)
        self.assert_outcome("failed", "request_too_large")
        self.assertEqual((await self.client.post(VERIFY_PATH, content=b"token=invalid")).status_code, 400)
        self.assert_outcome("failed", "invalid_request")

    async def test_signed_external_redirect_is_rejected(self):
        _, fields = await self.challenge()
        signer = SearchChallengeMiddleware(None, "test-secret").challenge
        with patch("maya.core.search_challenge.time.time", return_value=1000):
            data = signer.loads(fields["token"])
            data["target"] = "//evil.example"
            token = signer.dumps(data)
        solution = next(str(n) for n in range(1000000) if hashlib.sha256(f"{token}:{n}".encode()).hexdigest().startswith("000"))
        self.assertEqual((await self.verify({"token": token, "solution": solution})).status_code, 400)
        self.assert_outcome("failed", "invalid_redirect")

    async def test_clearance_cannot_be_copied_to_another_ip_or_spoofed_with_headers(self):
        _, fields = await self.challenge()
        await self.verify(fields)
        cookie = self.client.cookies.get(COOKIE)
        payload = SearchChallengeMiddleware(None, "test-secret").clearance.loads(cookie)
        self.assertNotIn("203.0.113.10", str(payload))
        self.transport.client = ("203.0.113.11", 5678)
        with patch("maya.core.search_challenge.time.time", return_value=1004):
            response = await self.client.get("/search", headers={"X-Forwarded-For": "203.0.113.10", "CF-Connecting-IP": "203.0.113.10"})
            self.assertIn("Checking your browser", response.text)
            self.assert_outcome("issued", "ip_mismatch")
            self.assertEqual((await self.client.get("/search/json")).status_code, 403)
        self.assertEqual(self.calls, 0)
        self.transport.client = ("203.0.113.10", 9999)
        with patch("maya.core.search_challenge.time.time", return_value=1004):
            self.assertEqual((await self.client.get("/search")).text, "search results")

    async def test_solved_challenge_cannot_be_exchanged_from_another_ip(self):
        _, fields = await self.challenge()
        self.transport.client = ("203.0.113.11", 1234)
        self.assertEqual((await self.verify(fields)).status_code, 400)
        self.assert_outcome("failed", "ip_mismatch")
        self.assertIsNone(self.client.cookies.get(COOKIE))

    async def test_old_clearance_and_challenge_are_invalidated(self):
        with patch("maya.core.search_challenge.time.time", return_value=1000):
            old_cookie = URLSafeTimedSerializer("test-secret", salt="maya-search-clearance-v1").dumps("verified")
        self.client.cookies.set(COOKIE, old_cookie)
        with patch("maya.core.search_challenge.time.time", return_value=1003):
            self.assertIn("Checking your browser", (await self.client.get("/search")).text)
        _, fields = await self.challenge()
        signer = SearchChallengeMiddleware(None, "test-secret").challenge
        with patch("maya.core.search_challenge.time.time", return_value=1000):
            old_token = URLSafeTimedSerializer("test-secret", salt="maya-search-challenge-v1").dumps(signer.loads(fields["token"]))
        self.assertEqual((await self.verify({**fields, "token": old_token})).status_code, 400)
        self.assertEqual(self.calls, 0)

    async def test_ipv6_is_normalized_but_different_address_requires_challenge(self):
        self.transport.client = ("2001:db8::1", 1234)
        _, fields = await self.challenge()
        await self.verify(fields)
        self.transport.client = ("2001:0db8:0:0:0:0:0:1", 5678)
        with patch("maya.core.search_challenge.time.time", return_value=1004):
            self.assertEqual((await self.client.get("/search")).text, "search results")
            self.transport.client = ("2001:db8::2", 5678)
            self.assertIn("Checking your browser", (await self.client.get("/search")).text)

    async def test_missing_address_fails_closed(self):
        _, fields = await self.challenge()
        await self.verify(fields)
        self.transport.client = None
        with patch("maya.core.search_challenge.time.time", return_value=1004):
            self.assertEqual((await self.client.get("/search")).status_code, 503)
            self.assert_outcome("failed", "missing_client_ip")
        self.assertEqual((await self.verify(fields)).status_code, 400)
        self.assertEqual(self.calls, 0)

    async def test_browser_language_selects_danish_or_english(self):
        for accepted, language in [
            ("da-DK,da;q=0.9,en;q=0.8", "da"),
            ("en;q=0.5,DA;q=0.9", "da"),
            ("en,da;q=0.8", "en"),
            ("de,da;q=0.8", "en"),
            ("da;q=0,en;q=1", "en"),
            ("da;q=invalid,en", "en"),
            ("da;q=NaN", "en"),
            ("", "en"),
        ]:
            with self.subTest(accepted=accepted):
                response = await self.client.get("/search", headers={"Accept-Language": accepted})
                self.assertEqual(response.headers["content-language"], language)
                self.assertIn(f'<html lang="{language}">', response.text)
                self.assertIn("Fortsæt til søgning" if language == "da" else "Continue to search", response.text)
                self.assertIn('data-ready="', response.text)
                self.assertIn('data-error="', response.text)
        self.assertEqual(self.calls, 0)

    async def test_verification_error_uses_browser_language(self):
        response = await self.client.post(VERIFY_PATH, content=b"invalid", headers={"Accept-Language": "da"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["content-language"], "da")
        self.assertIn("Bekræftelsen mislykkedes", response.text)
        self.assertIn("prøv igen", response.text)

    async def test_office_allowlist_skips_challenge_without_setting_cookie(self):
        for ip in ["198.51.100.6", "::ffff:198.51.100.6"] + [f"192.0.2.{n}" for n in range(34, 39)]:
            self.transport.client = (ip, 1234)
            for path in ("/search?q=office", "/search/json"):
                response = await self.client.get(path)
                self.assertEqual(response.text, "search results")
                self.assert_outcome("allowed", "allowlisted_ip")
                self.assertNotIn("set-cookie", response.headers)
                self.assertEqual(response.headers["cache-control"], "private, no-store")

    async def test_allowlist_does_not_match_neighbours_or_forwarded_headers(self):
        for ip in ("192.0.2.33", "192.0.2.39", "198.51.100.7"):
            self.transport.client = (ip, 1234)
            response = await self.client.get("/search", headers={"X-Forwarded-For": "198.51.100.6"})
            self.assertIn("Checking your browser", response.text)
            self.assert_outcome("issued", "missing_cookie")
        self.assertEqual(self.calls, 0)

    def test_allowlist_configuration_requires_exact_ip_addresses(self):
        self.assertEqual(SearchChallengeMiddleware(None, "secret").allowed_ips, frozenset())
        for value in ("198.51.100.6", ["192.0.2.34-38"], ["192.0.2.0/24"], ["office.example"], [123]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SearchChallengeMiddleware(None, "secret", allowed_ips=value)
