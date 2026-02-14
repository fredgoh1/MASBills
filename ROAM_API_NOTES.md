# Roam Research API — Known Quirks & Pitfalls

Reference notes for working with the Roam Research API in this project. These were discovered through debugging real failures and should be consulted before writing or modifying any Roam integration code.

## 1. Auth headers are stripped on redirect

**Problem:** Roam's API at `api.roamresearch.com` redirects requests to a peer host (e.g. `peer-65.api.roamresearch.com:3002`). Python's `requests` library silently drops the `Authorization` header when a redirect crosses to a different host. This results in a `401 Unauthorized` error even though the token is correct.

**Symptom:** `{"message":"You are not authenticated"}` with status 401, despite the token being valid.

**Fix:** Use a `requests.Session` and override `rebuild_auth` to prevent header stripping:

```python
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {token}", ...})
session.rebuild_auth = lambda prepared, response: None
```

**Lesson:** When an API returns 401 but credentials are correct, check whether the request is being redirected to a different host. Inspect `resp.request.headers` (the *actually sent* headers) and `resp.url` (the *final* URL after redirects) to diagnose. Never assume `Authorization` survives cross-host redirects with `requests`.

## 2. Write endpoint returns empty body

**Problem:** The Roam `/write` endpoint (used for `create-block`, `create-page`, etc.) returns HTTP 200 with a completely empty response body (`content-length: 0`). Calling `.json()` on this response raises `JSONDecodeError`.

**Symptom:** `simplejson.errors.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**Fix:** Do not call `.json()` on write responses. Only check `resp.raise_for_status()` for success. If you need to reference the created block later (e.g. to nest children under it), generate a UID yourself and pass it in the request:

```python
import uuid

block_uid = str(uuid.uuid4())[:9]
payload = {
    "action": "create-block",
    "location": {"parent-uid": parent_uid, "order": "last"},
    "block": {"string": text, "uid": block_uid},
}
```

**Lesson:** Never assume an API returns JSON on success. Always check `content-length` or wrap `.json()` in a guard before calling it. When an API doesn't return a resource identifier, check if the API allows client-generated IDs.

## 3. Query endpoint returns `{"result": value}`

The `/q` endpoint returns JSON with a `"result"` key. For scalar queries (`:find ?uid .`), the result is a plain string. For collection queries, it's a list. Always access via `.json().get("result")`.

## 4. Daily page title format

Roam daily page titles use the format `"February 14th, 2026"` — full month name, ordinal day, comma, four-digit year. The ordinal rules:
- 11th, 12th, 13th (special cases)
- 1st, 2nd, 3rd, everything else is "th"

## General Debugging Checklist for Roam API Issues

1. **401 errors** → Check for cross-host redirects stripping auth headers
2. **JSON decode errors** → Check if the endpoint returns an empty body on success
3. **Blocks not appearing** → Verify the parent UID exists and is correct
4. **Page not found** → Verify the page title matches Roam's exact format (ordinal dates, spacing)
