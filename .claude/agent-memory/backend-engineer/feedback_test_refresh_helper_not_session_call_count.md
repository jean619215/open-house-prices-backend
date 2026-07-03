---
name: feedback-test-refresh-helper-not-session-call-count
description: When adding a post-write step (e.g. REFRESH MATERIALIZED VIEW) inside an existing async-session block, extract it into its own private async function and patch/assert on THAT in tests, rather than counting session.execute/commit calls
metadata:
  type: feedback
---

TASK-003 added a `REFRESH MATERIALIZED VIEW city_stats` step to `etl/pipeline.py::run_pipeline()`, executed on the same `AsyncSession` right after `load_rows()` inside the same `async with factory() as session:` block. The natural instinct is to test it by asserting on `session.execute.call_count` or `session.commit.call_count`, but this couples the test to exactly how many other calls `load_rows`/`bulk_insert_rows` happen to make internally (dedup SELECT, flush, etc.) — it breaks silently whenever the loader's internals change, even if refresh behavior itself didn't.

Instead: extract the refresh into its own private function (`_refresh_city_stats(session)`), and in tests `patch("etl.pipeline._refresh_city_stats", new=AsyncMock())` to assert `assert_awaited_once()` / `assert_not_called()` / `assert_awaited_once_with(session)`. This is exactly what TC-10 in the TASK-003 card explicitly hinted at ("可用 mock 的 assert_not_called() 驗證") and made the four scenarios (normal run, all-duplicate run, empty-CSV early return, no-cities early return, refresh-raises-propagates) trivial one-liners instead of fragile call-count arithmetic. Separately, unit-test the helper itself (`_refresh_city_stats` called directly with a session mock) to verify it issues the right SQL text and re-raises `SQLAlchemyError` after logging — see `tests/test_etl_pipeline.py::TestRefreshCityStats`.

**Why:** call-count assertions on a shared mock session are a common source of flaky/coupled tests whenever the collaborator function's internal call pattern changes for unrelated reasons.

**How to apply:** any time a new side-effecting step is added to an existing multi-step pipeline function on the same session/connection, factor it out as its own async helper first, then test the helper directly plus its "was/wasn't invoked" behavior at the call site via `patch(..., new=AsyncMock())`.
