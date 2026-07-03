---
name: health-check-async-pattern
description: Pattern for /health endpoint with per-service timeouts and non-blocking disconnect handling
metadata:
  type: feedback
---

The /health endpoint must not block the event loop on disconnect. Use `asyncio.timeout()` (Python 3.11+) rather than `asyncio.wait_for()` for cleaner cancellation semantics.

**Why:** A broken DB/Redis connection can hang indefinitely if no timeout is set, violating the 3-second SLA in B3.

**How to apply:**

- DB probe: open engine connection inside `asyncio.timeout(2.0)`, then `SET LOCAL statement_timeout = 2000` before `SELECT 1`.
- Redis probe: pass `socket_connect_timeout=1.0, socket_timeout=1.0` to `aioredis.from_url()`.
- Wrap both with `asyncio.gather()` inside an outer `asyncio.timeout(3.0)`.
- Always call `await client.aclose()` on the redis client in a `finally` block to avoid connection leaks.
- Return 503 when either service fails; return 200 only when both are "connected".

For unit tests: mock `get_engine` (return value, not side_effect) and `aioredis.from_url` (return value). The engine mock needs `connect()` to return a context manager (AsyncMock with `__aenter__`/`__aexit__`).
