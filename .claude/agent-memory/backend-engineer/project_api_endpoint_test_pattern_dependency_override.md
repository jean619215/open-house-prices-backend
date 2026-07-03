---
name: project-api-endpoint-test-pattern-dependency-override
description: New DB-backed FastAPI endpoints (unlike /health) should use Depends(get_db_session) and be tested via app.dependency_overrides, not by mocking get_engine directly
metadata:
  type: project
---

`api/routers/health.py` (TASK-001) mocks `get_engine()` directly and opens its own `engine.connect()` because it needs a raw connectivity probe, not an ORM/query session. That is a special case for a health check, not the general pattern.

For TASK-003's `GET /api/prices/city` (and presumably future data endpoints), the right shape is: declare `session: AsyncSession = Depends(get_db_session)` (from `shared/database.py`) as a route parameter, then in tests override it via `app.dependency_overrides[get_db_session] = fake_dependency` (an async function/generator returning a mock `AsyncSession`), and always clear it in an `autouse` fixture (`app.dependency_overrides.clear()`) so overrides don't leak between test functions. See `tests/test_api_prices.py::_install_override` / `_clear_overrides` for the reusable shape.

To assert on the exact SQL text issued (e.g. verifying `ORDER BY city ASC` is present, or that a view is queried directly with no `GROUP BY`/`transactions` reference), inspect `session.execute.await_args` and `str()` the first positional arg (the `TextClause` from `sqlalchemy.text(...)`) rather than trying to introspect a compiled query object.

To simulate a query-time DB failure (AC-22-style "DB exception → 500" test), set `session.execute = AsyncMock(side_effect=SQLAlchemyError(...))` and use `ASGITransport(app=app, raise_app_exceptions=False)` in the `AsyncClient` — otherwise httpx's test transport re-raises the exception into the test instead of letting FastAPI's default handler turn it into a 500 response.

**Why:** keeps new endpoint tests decoupled from real DB/engine internals while still being able to assert both response shape and the exact query issued — mirrors AC-16's "must query the view directly, not GROUP BY transactions" requirement in a way a black-box HTTP response assertion alone couldn't catch.

**How to apply:** for any new `api/routers/*.py` endpoint that reads/writes via SQLAlchemy, prefer `Depends(get_db_session)` + `dependency_overrides` testing over ad-hoc engine mocking, unless the endpoint specifically needs raw connection-level behavior like `/health` does.
