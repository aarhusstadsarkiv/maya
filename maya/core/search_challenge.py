"""Cheap search admission check; no API, database, or server-side waiting.

This discourages basic crawlers, not determined browser automation. Signed
tokens work across workers; a browser nonce prevents replaying a solved token
without also possessing its cookie.
"""

import hashlib
import html
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs

from itsdangerous import BadData, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

VERIFY_PATH = "/_search-challenge"
COOKIE = "maya_search_verified"
NONCE_COOKIE = "maya_search_nonce"
MIN_WAIT = 2
TOKEN_TTL = 300
CLEARANCE_TTL = 1800
DIFFICULTY = 3  # SHA-256 hexadecimal zeroes: approximately 4096 attempts.
SCRIPT = (Path(__file__).resolve().parent.parent / "static/js/search-challenge.js").read_text(encoding="utf-8")
STYLE = (Path(__file__).resolve().parent.parent / "static/css/search-challenge.css").read_text(encoding="utf-8")


class SearchChallengeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret: str):
        super().__init__(app)
        if not secret or secret.strip() == "None":
            raise ValueError("Search challenge requires a persistent session_secret")
        self.challenge = URLSafeTimedSerializer(secret, salt="maya-search-challenge-v1")
        self.clearance = URLSafeTimedSerializer(secret, salt="maya-search-clearance-v1")

    def verified(self, request):
        try:
            return self.clearance.loads(request.cookies.get(COOKIE, ""), max_age=CLEARANCE_TTL) == "verified"
        except BadData:
            return False

    @staticmethod
    def set_cookie(response, request, name, value, max_age):
        response.set_cookie(name, value, max_age=max_age, httponly=True, secure=request.url.scheme == "https", samesite="lax")

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path == VERIFY_PATH:
            return await self.verify(request)
        if path != "/search" and not path.startswith("/search/"):
            return await call_next(request)
        if self.verified(request):
            response = await call_next(request)
            response.headers["Cache-Control"] = "private, no-store"
            return response
        if path not in ("/search", "/search/"):
            return JSONResponse(
                {"error": "search_verification_required", "challenge_url": "/search"},
                status_code=403,
                headers={"Cache-Control": "no-store"},
            )
        if request.method not in ("GET", "HEAD"):
            return PlainTextResponse("Method not allowed", status_code=405, headers={"Allow": "GET, HEAD"})
        nonce = request.cookies.get(NONCE_COOKIE, "")
        if len(nonce) != 32:
            nonce = secrets.token_hex(16)
        target = "/search"
        if request.url.query:
            target += "?" + request.url.query
        token = self.challenge.dumps({"nonce": nonce, "target": target, "issued": time.time(), "random": secrets.token_hex(16)})
        script_nonce = secrets.token_hex(16)
        response = HTMLResponse(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>Checking your browser</title><style nonce=\"{script_nonce}\">{STYLE}</style>"
            '<body><main><h1>Checking your browser</h1>'
            '<div id="loader" class="loadingspinner" aria-hidden="true" hidden></div>'
            '<p id="status" role="status">Please wait a moment before continuing to search.</p>'
            "<noscript>JavaScript and cookies are required to search. Please enable them and reload this page.</noscript>"
            f'<form id="challenge" method="post" action="{VERIFY_PATH}">'
            f'<input type="hidden" name="token" value="{html.escape(token, quote=True)}">'
            '<input type="hidden" name="solution" value="">'
            f'<input type="hidden" id="difficulty" value="{DIFFICULTY}">'
            f'<input type="hidden" id="wait" value="{MIN_WAIT * 1000 + 250}">'
            '<button id="continue-search" type="submit" disabled>Continue to search</button></form>'
            f'<script nonce="{script_nonce}">{SCRIPT}</script></main></body></html>',
            headers={
                "Cache-Control": "no-store",
                "X-Robots-Tag": "noindex, nofollow",
                "Referrer-Policy": "same-origin",
                "Content-Security-Policy": (
                    f"default-src 'none'; script-src 'nonce-{script_nonce}'; style-src 'nonce-{script_nonce}'; "
                    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
                ),
            },
        )
        self.set_cookie(response, request, NONCE_COOKIE, nonce, TOKEN_TTL)
        return response

    async def verify(self, request):
        headers = {"Cache-Control": "no-store"}
        if request.method != "POST":
            return PlainTextResponse("Method not allowed", status_code=405, headers={**headers, "Allow": "POST"})
        # The signed token and matching HttpOnly nonce are required even when
        # Origin is absent. Reject explicitly cross-origin submissions.
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return PlainTextResponse("Forbidden", status_code=403, headers=headers)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 16384:
                return PlainTextResponse("Request too large", status_code=413, headers=headers)
            body.extend(chunk)
        try:
            fields = parse_qs(body.decode("utf-8"), max_num_fields=4)
            (token,) = fields["token"]
            (solution,) = fields["solution"]
            if not solution.isascii() or not solution.isdecimal() or len(solution) > 12:
                raise ValueError("Invalid solution")
            data = self.challenge.loads(token, max_age=TOKEN_TTL)
            if not secrets.compare_digest(data["nonce"], request.cookies.get(NONCE_COOKIE, "")):
                raise ValueError("Missing browser nonce")
            if not MIN_WAIT <= time.time() - data["issued"] <= TOKEN_TTL:
                raise ValueError("Challenge not ready or expired")
            digest = hashlib.sha256(f"{token}:{solution}".encode()).hexdigest()
            if not digest.startswith("0" * DIFFICULTY):
                raise ValueError("Invalid proof")
            target = data["target"]
            if target != "/search" and not target.startswith("/search?"):
                raise ValueError("Invalid redirect")
        except (BadData, ValueError, KeyError, TypeError):
            return HTMLResponse(
                '<p>Verification failed or expired. Enable cookies and <a href="/search">try again</a>.</p>',
                status_code=400,
                headers=headers,
            )
        response = RedirectResponse(target, status_code=303, headers=headers)
        self.set_cookie(response, request, COOKIE, self.clearance.dumps("verified"), CLEARANCE_TTL)
        return response
