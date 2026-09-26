# Cloudflare setup for firmware.gl-i.net

The site is static (GitHub Pages behind Cloudflare), so it cannot answer differently
for `curl` and for a browser by itself. The generator therefore writes a plain-text
twin next to every page (`/index.txt`, `/<model>/index.txt`), and a Cloudflare
**Transform Rule** sends terminal clients there. No Worker is needed.

**Status:** both rules below are live in the zone `gl-i.net` (ruleset phase
`http_request_transform`, created 2026-09-26). This file documents them so they
can be recreated or adjusted.

Classic *Page Rules* cannot do this: they only match on the URL, not on the
User-Agent or Accept header. Transform Rules (their successor) can, and the free
plan includes them.

## URL rewrite rules

Cloudflare dashboard → zone `gl-i.net` → **Rules** → **Transform Rules** →
**Rewrite URL** → *Create rule*. Two rules, both with a custom filter expression
and a *dynamic* path rewrite:

### Rule 1: `curl: plain text (directory)`

Filter expression:

```
http.host eq "firmware.gl-i.net"
and (
  http.user_agent contains "curl" or
  http.user_agent contains "Wget" or
  http.user_agent contains "HTTPie" or
  http.user_agent contains "xh/" or
  http.request.headers["accept"][0] eq "text/plain"
)
and not starts_with(http.request.uri.path, "/api/")
and not http.request.uri.path contains "."
and ends_with(http.request.uri.path, "/")
```

The `http.host` check keeps the rule away from other subdomains of the zone.

Path → *Rewrite to* → *Dynamic*:

```
concat(http.request.uri.path, "index.txt")
```

### Rule 2: `curl: plain text (no trailing slash)`

Same filter expression, but with the last line replaced by
`and not ends_with(http.request.uri.path, "/")`, and the dynamic rewrite:

```
concat(http.request.uri.path, "/index.txt")
```

Rule 2 also spares terminal users the GitHub Pages redirect from `/mt3000` to
`/mt3000/`, which `curl` would not follow without `-L`.

## Response header rule

GitHub Pages serves the extension-less files under `/api/` as
`application/octet-stream`, so a browser offers a download instead of showing
the text. A **Modify Response Header** rule (Rules → Transform Rules → Modify
Response Header, also live in the zone) fixes that:

Filter expression:

```
http.host eq "firmware.gl-i.net"
and starts_with(http.request.uri.path, "/api/")
and not ends_with(http.request.uri.path, ".json")
```

Action: *Set static* header `Content-Type` = `text/plain; charset=utf-8`.

The JSON files (`all.json`, `status.json`) keep their `application/json`.
Cloudflare caches these files per URL, so a response cached before the rule
was created keeps its old type until the cache entry expires.

## What this gives you

The generator writes a small menu tree of text pages; the two rules above cover
all of them, no per-page rule is needed:

```
curl https://firmware.gl-i.net/                          menu
curl https://firmware.gl-i.net/routers                   one category (iot, kvm, all)
curl https://firmware.gl-i.net/mt3000                    one model
curl https://firmware.gl-i.net/mt3000/release            one build with its changelog
curl -s https://firmware.gl-i.net/cli | sh               interactive menu (cli.sh)
curl https://firmware.gl-i.net/api/mt3000/branches       flat-file API (always plain text)
```

Browsers keep getting the HTML pages; the directories that only exist for their
`index.txt` (`/routers/`, `/all/`, `/<model>/<stage>/`) carry a tiny redirect
page, and `/cli/` a page that explains the terminal menu. The `.txt` twins can
always be fetched directly as well (`/index.txt`, `/mt3000/index.txt`).

## Notes

- `/api/...` is excluded from the rewrite rules because everything there is
  plain text already. Directory URLs under `/api/` without a trailing slash still
  go through the GitHub Pages redirect, so use the trailing slash or `curl -L`.
- Cloudflare caches `.txt` files by default per URL. GitHub Pages sends
  `Cache-Control: max-age=600`, so a fresh build is visible within ten minutes.
- The custom domain itself is configured in the GitHub repository under
  *Settings → Pages → Custom domain*. With the Actions-based deploy no `CNAME`
  file is needed.
