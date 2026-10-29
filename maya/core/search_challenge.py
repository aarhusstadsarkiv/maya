"""Cheap search admission check; no API, database, or server-side waiting.

This discourages basic crawlers, not determined browser automation. Signed
tokens work across workers. Both tokens are bound to the client IP; a browser
nonce also prevents exchanging a solved challenge without its nonce cookie.
"""

import hashlib
import hmac
import html
import ipaddress
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs

from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
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

MESSAGES = {
    "en": {
        "title": "Checking your browser",
        "wait": "Please wait a moment before continuing to search.",
        "noscript": "JavaScript and cookies are required to search. Please enable them and reload this page.",
        "button": "Continue to search",
        "ready": "Your browser is ready. Select “Continue to search” to proceed.",
        "continuing": "Continuing to search…",
        "error": "Unable to verify this browser. Enable JavaScript and cookies, use HTTPS, and reload to try again.",
        "failed": "Verification failed or expired. Enable cookies and",
        "retry": "try again",
    },
    "da": {
        "title": "Vi tjekker din browser",
        "wait": "Vent et øjeblik, før du fortsætter til søgningen.",
        "noscript": "JavaScript og cookies er nødvendige for at søge. Aktivér dem, og genindlæs siden.",
        "button": "Fortsæt til søgning",
        "ready": "Din browser er klar. Vælg “Fortsæt til søgning” for at fortsætte.",
        "continuing": "Fortsætter til søgningen…",
        "error": "Vi kunne ikke bekræfte din browser. Aktivér JavaScript og cookies, brug HTTPS, og genindlæs siden for at prøve igen.",
        "failed": "Bekræftelsen mislykkedes eller er udløbet. Aktivér cookies, og",
        "retry": "prøv igen",
    },
}


def challenge_language(request):
    """Use Danish only when the browser's highest-priority language is Danish."""
    preferred, best_quality = "en", 0.0
    for entry in request.headers.get("accept-language", "").split(","):
        language, *parameters = entry.strip().lower().split(";")
        quality = 1.0
        try:
            for parameter in parameters:
                key, _, value = parameter.strip().partition("=")
                if key == "q":
                    quality = float(value)
        except ValueError:
            continue
        if language and best_quality < quality <= 1:
            preferred, best_quality = language.strip(), quality
    return "da" if preferred.split("-")[0] == "da" else "en"


class _ChallengeRejected(ValueError):
    """Contains only a fixed, non-sensitive reason code."""


def record_challenge_outcome(request, outcome, reason=None):
    # AccessLogMiddleware is outside this middleware and logs this once, after
    # the final response status and duration are known. Never attach tokens.
    request.state.challenge_outcome = outcome
    request.state.challenge_reason = reason


class SearchChallengeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret: str):
        super().__init__(app)
        if not secret or secret.strip() == "None":
            raise ValueError("Search challenge requires a persistent session_secret")
        self.challenge = URLSafeTimedSerializer(secret, salt="maya-search-challenge-v2")
        self.clearance = URLSafeTimedSerializer(secret, salt="maya-search-clearance-v2")
        self.ip_key = hmac.digest(secret.encode(), b"maya-search-ip-v1", "sha256")

    def ip_fingerprint(self, request):
        # Only use the ASGI server's client address. Forwarded headers must be
        # resolved by the server using its trusted-proxy configuration.
        if request.client is None:
            return None
        try:
            address = ipaddress.ip_address(request.client.host)
        except ValueError:
            return None
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        return hmac.new(self.ip_key, str(address).encode(), hashlib.sha256).hexdigest()

    def clearance_rejection_reason(self, request):
        cookie = request.cookies.get(COOKIE, "")
        if not cookie:
            return "missing_cookie"
        try:
            fingerprint = self.ip_fingerprint(request)
            data = self.clearance.loads(cookie, max_age=CLEARANCE_TTL)
            if fingerprint is None:
                return "missing_client_ip"
            if not isinstance(data, dict) or not isinstance(data.get("ip"), str) or not data["ip"].isascii():
                return "invalid_cookie"
            if not secrets.compare_digest(data["ip"], fingerprint):
                return "ip_mismatch"
            return None
        except SignatureExpired:
            return "expired_cookie"
        except BadData:
            return "invalid_signature"

    @staticmethod
    def set_cookie(response, request, name, value, max_age):
        response.set_cookie(name, value, max_age=max_age, httponly=True, secure=request.url.scheme == "https", samesite="lax")

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path == VERIFY_PATH:
            return await self.verify(request)
        if path != "/search" and not path.startswith("/search/"):
            return await call_next(request)
        reason = self.clearance_rejection_reason(request)
        if reason is None:
            record_challenge_outcome(request, "allowed")
            response = await call_next(request)
            response.headers["Cache-Control"] = "private, no-store"
            return response
        if path not in ("/search", "/search/"):
            record_challenge_outcome(request, "failed", reason)
            return JSONResponse(
                {"error": "search_verification_required", "challenge_url": "/search"},
                status_code=403,
                headers={"Cache-Control": "no-store"},
            )
        if request.method not in ("GET", "HEAD"):
            record_challenge_outcome(request, "failed", "invalid_method")
            return PlainTextResponse("Method not allowed", status_code=405, headers={"Allow": "GET, HEAD"})
        fingerprint = self.ip_fingerprint(request)
        if fingerprint is None:
            record_challenge_outcome(request, "failed", "missing_client_ip")
            return PlainTextResponse("Unable to verify client address", status_code=503, headers={"Cache-Control": "no-store"})
        nonce = request.cookies.get(NONCE_COOKIE, "")
        if len(nonce) != 32:
            nonce = secrets.token_hex(16)
        target = "/search"
        if request.url.query:
            target += "?" + request.url.query
        token = self.challenge.dumps(
            {"nonce": nonce, "target": target, "issued": time.time(), "random": secrets.token_hex(16), "ip": fingerprint}
        )
        script_nonce = secrets.token_hex(16)
        language = challenge_language(request)
        messages = {key: html.escape(value, quote=True) for key, value in MESSAGES[language].items()}
        response = HTMLResponse(
            f'<!doctype html><html lang="{language}"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{messages["title"]}</title><style nonce="{script_nonce}">{STYLE}</style>'
            f'<body><main><h1>{messages["title"]}</h1>'
            '<div id="loader" class="loadingspinner" aria-hidden="true" hidden></div>'
            f'<p id="status" role="status" data-ready="{messages["ready"]}" '
            f'data-continuing="{messages["continuing"]}" data-error="{messages["error"]}">{messages["wait"]}</p>'
            f'<noscript>{messages["noscript"]}</noscript>'
            f'<form id="challenge" method="post" action="{VERIFY_PATH}">'
            f'<input type="hidden" name="token" value="{html.escape(token, quote=True)}">'
            '<input type="hidden" name="solution" value="">'
            f'<input type="hidden" id="difficulty" value="{DIFFICULTY}">'
            f'<input type="hidden" id="wait" value="{MIN_WAIT * 1000 + 250}">'
            f'<button id="continue-search" type="submit" disabled>{messages["button"]}</button></form>'
            f'<script nonce="{script_nonce}">{SCRIPT}</script></main></body></html>',
            headers={
                "Cache-Control": "no-store",
                "Content-Language": language,
                "X-Robots-Tag": "noindex, nofollow",
                "Referrer-Policy": "same-origin",
                "Content-Security-Policy": (
                    f"default-src 'none'; script-src 'nonce-{script_nonce}'; style-src 'nonce-{script_nonce}'; "
                    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
                ),
            },
        )
        self.set_cookie(response, request, NONCE_COOKIE, nonce, TOKEN_TTL)
        record_challenge_outcome(request, "issued", reason)
        return response

    async def verify(self, request):
        headers = {"Cache-Control": "no-store"}
        if request.method != "POST":
            record_challenge_outcome(request, "failed", "invalid_method")
            return PlainTextResponse("Method not allowed", status_code=405, headers={**headers, "Allow": "POST"})
        # The signed token and matching HttpOnly nonce are required even when
        # Origin is absent. Reject explicitly cross-origin submissions.
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            record_challenge_outcome(request, "failed", "invalid_origin")
            return PlainTextResponse("Forbidden", status_code=403, headers=headers)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 16384:
                record_challenge_outcome(request, "failed", "request_too_large")
                return PlainTextResponse("Request too large", status_code=413, headers=headers)
            body.extend(chunk)
        try:
            fields = parse_qs(body.decode("utf-8"), max_num_fields=4)
            (token,) = fields["token"]
            (solution,) = fields["solution"]
            if not solution.isascii() or not solution.isdecimal() or len(solution) > 12:
                raise _ChallengeRejected("invalid_proof")
            data = self.challenge.loads(token, max_age=TOKEN_TTL)
            fingerprint = self.ip_fingerprint(request)
            if fingerprint is None:
                raise _ChallengeRejected("missing_client_ip")
            if not secrets.compare_digest(data["ip"], fingerprint):
                raise _ChallengeRejected("ip_mismatch")
            if not secrets.compare_digest(data["nonce"], request.cookies.get(NONCE_COOKIE, "")):
                raise _ChallengeRejected("nonce_mismatch")
            age = time.time() - data["issued"]
            if age < MIN_WAIT:
                raise _ChallengeRejected("too_early")
            if age > TOKEN_TTL:
                raise _ChallengeRejected("expired_challenge")
            digest = hashlib.sha256(f"{token}:{solution}".encode()).hexdigest()
            if not digest.startswith("0" * DIFFICULTY):
                raise _ChallengeRejected("invalid_proof")
            target = data["target"]
            if target != "/search" and not target.startswith("/search?"):
                raise _ChallengeRejected("invalid_redirect")
        except SignatureExpired:
            return self.verification_failed(request, "expired_challenge")
        except BadData:
            return self.verification_failed(request, "invalid_signature")
        except _ChallengeRejected as exc:
            return self.verification_failed(request, str(exc))
        except (ValueError, KeyError, TypeError):
            return self.verification_failed(request, "invalid_request")
        response = RedirectResponse(target, status_code=303, headers=headers)
        self.set_cookie(response, request, COOKIE, self.clearance.dumps({"ip": fingerprint}), CLEARANCE_TTL)
        record_challenge_outcome(request, "passed")
        return response

    @staticmethod
    def verification_failed(request, reason):
        record_challenge_outcome(request, "failed", reason)
        language = challenge_language(request)
        messages = MESSAGES[language]
        return HTMLResponse(
            f'<!doctype html><html lang="{language}"><meta charset="utf-8">'
            f'<title>{messages["title"]}</title><p>{messages["failed"]} <a href="/search">{messages["retry"]}</a>.</p></html>',
            status_code=400,
            headers={"Cache-Control": "no-store", "Content-Language": language},
        )
