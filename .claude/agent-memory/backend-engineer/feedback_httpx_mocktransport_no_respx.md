---
name: feedback-httpx-mocktransport-no-respx
description: Use httpx.MockTransport (stdlib-adjacent, already a dependency) to test download/HTTP-error code paths instead of adding a new mocking dependency like respx
metadata:
  type: feedback
---

TASK-002 Code Review Major #3 required direct tests for `etl/downloader.py` (`_extract_csv_from_zip`, `_build_download_url`, HTTP 4xx/5xx and network-error propagation) that don't go through real network calls. No `respx` or similar package was added — `httpx` is already a project dependency and ships `httpx.MockTransport`, which is enough.

**Why:** Project convention is `uv add {package}` only when actually needed; adding a whole mocking library for a handful of HTTP tests would be unnecessary dependency growth when the HTTP library itself already provides a fake-transport mechanism.

**How to apply:**
```python
def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="Internal Server Error")  # or raise httpx.ConnectError(...) for network errors

transport = httpx.MockTransport(handler)

@asynccontextmanager
async def _client_with_transport(transport):
    async with httpx.AsyncClient(transport=transport) as client:
        yield client

with patch("etl.downloader._make_http_client", return_value=_client_with_transport(transport)):
    ...  # exercise download_csv() etc.
```
Patch the module's internal client-factory function (e.g. `_make_http_client`) rather than `httpx.AsyncClient` globally — it's the seam the downloader code already calls through, so no production code needs to change to become testable. See [[project-moi-download-pattern]] for the URL/zip format this is testing against.
