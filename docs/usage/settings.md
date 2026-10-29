---
title: Settings
---

Maya indeholder en lang række settings, som man kan overskrive efter behov.

En setting findes i enten `settings.yml`, `facets.yml` eller `language.yml` (oplistet nedenfor), og hvis man vil overskrive en setting, skal man oprette en tilsvarende `yaml`-fil i roden af BASE_DIR. Hvis man eksempelvis vil ændre om Maya gemmer på seneste søgning mens man navigerer rundt på andre sider, sætter man værdien til *false*:

```yaml
# settings.yml
search_keep_results: false
```

## settings.yml

### Search browser challenge

`search_challenge_enabled` defaults to `true`. Before `/search` runs any API
calls, visitors complete an automatic JavaScript proof of work and a minimum
two-second wait, then select **Continue to search**. The button becomes available
only when both checks are complete; there is no automatic redirect. It supports
mouse and keyboard activation. The wait happens in the browser and is checked by the server;
no server worker sleeps. Successful verification sets an HttpOnly, SameSite=Lax
cookie valid for 30 minutes (Secure on HTTPS). Search filters are preserved.
The challenge uses Danish when the browser's preferred language (from
`Accept-Language`, including quality weights) is `da` or a Danish regional
variant such as `da-DK`. All other preferences, or a missing header, use English.
This includes the button, progress messages, and verification-error page, with
no additional translation or API requests.
Both the challenge and verification cookie are bound to the visitor's IP using
a keyed hash, without storing the raw IP in either token. Changing IP requires
a new challenge. Cookies can still be shared by clients using the same public IP.
Deploying the IP-bound version invalidates older challenge and verification
tokens; login/session cookies are unaffected.

Serve the site over HTTPS and keep `SESSION_SECRET` persistent and identical
across workers. The challenge expires after five minutes. Visitors need
JavaScript and cookies. `/search/json` returns HTTP 403 with
`search_verification_required` until the browser has completed `/search`.
Other endpoints, including record pages and autocomplete, are unchanged.
Challenge and verified search responses must not be cached by a shared proxy.

IP binding uses the ASGI client address, also shown in Maya's access logs; it
does not read forwarded headers directly. Configure Gunicorn/Uvicorn's
`FORWARDED_ALLOW_IPS` to trust only Caddy's actual connecting address, never
`*` on a publicly reachable server. For Caddy on the same machine, use a
loopback upstream and bind Maya with `--host 127.0.0.1`. If Caddy connects from
another machine/container, set the trusted proxy address explicitly and restrict
direct access to Gunicorn. Confirm access logs contain actual visitor addresses,
not one shared proxy address, before relying on IP binding.

This deters simple crawlers, not determined browser automation. Clearance can
be reused for its lifetime and requests still reach Python. Keep concurrency
limits and upstream traffic protection. No database or additional service is
required. Restart Maya after deploying; no Caddy plugin is needed.

#### Challenge access logging

The existing access log includes `challenge=issued`, `challenge=passed`,
`challenge=failed`, or `challenge=allowed` on requests handled by the challenge.
An optional `reason=` explains issuance or rejection, for example
`missing_cookie`, `expired_cookie`, `invalid_signature`, `ip_mismatch`,
`too_early`, `expired_challenge`, or `invalid_proof`. No additional log entry is
written. Tokens, cookies, proof solutions, and IP fingerprints are not added to
logs; query strings on `/_search-challenge` are omitted as well.

`issued` means only that a challenge page was served. A visitor who never
submits it creates no `failed` event. `passed` means verification succeeded,
not that the visitor is necessarily human. `allowed` means a valid cookie
admitted the request; check its HTTP status and duration for search failures.
`failed` also covers protected JSON requests rejected without a valid cookie;
filter to `POST /_search-challenge` when counting verification failures.
Requests rejected by concurrency limits before reaching the challenge retain
their ordinary 429 access entry with no challenge outcome.

Browsers usually omit expired cookies, which is logged as `missing_cookie`;
`expired_cookie` is reported only when an expired cookie is actually submitted.
Compare outcome counts over time with search latency, API timeouts, and CPU
load. Counts represent requests, not unique people or bots.

To disable the challenge in a site's settings:

```yaml
search_challenge_enabled: false
```

## facets.yml

## language.yml
