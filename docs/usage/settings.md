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

Serve the site over HTTPS and keep `SESSION_SECRET` persistent and identical
across workers. The challenge expires after five minutes. Visitors need
JavaScript and cookies. `/search/json` returns HTTP 403 with
`search_verification_required` until the browser has completed `/search`.
Other endpoints, including record pages and autocomplete, are unchanged.
Challenge and verified search responses must not be cached by a shared proxy.

This deters simple crawlers, not determined browser automation. Clearance can
be reused for its lifetime and requests still reach Python. Keep concurrency
limits and upstream traffic protection. No database or additional service is
required. Restart Maya after deploying; no Caddy plugin is needed.

To disable the challenge in a site's settings:

```yaml
search_challenge_enabled: false
```

## facets.yml

## language.yml
