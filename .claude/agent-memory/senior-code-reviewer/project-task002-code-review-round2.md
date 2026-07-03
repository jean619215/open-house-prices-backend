---
name: project-task002-code-review-round2
description: TASK-002 Code Review round 2 (commit 9369c4e) — verified the 3 round-1 Majors were genuinely fixed; passed to QA測試 with one non-blocking follow-up on exception scope in bulk_insert_rows.
metadata:
  type: project
---

Round 2 review of TASK-002 (etl-realprice-import), diff `3b1358a..9369c4e`. All 3 round-1 Majors (see [[project-task002-code-review-round1]]) verified as genuinely fixed, not just claimed:
1. `shared/models.py` Transaction docstring now correctly says m² raw value / no ping conversion / full transaction date — matches 決策 1.
2. `parse_building_age` now checks `UNKNOWN_DATE_VALUE` sentinel symmetrically with `parse_transaction_date`, with a real (non-trivial) unit test asserting `parse_building_age("0000000", 2026) is None`.
3. `tests/test_etl_downloader.py` added (12 tests) using `httpx.MockTransport` patched at `_make_http_client` — genuinely exercises `download_csv`/`_extract_csv_from_zip`/`_build_download_url` logic, not a re-mock of `download_csv` itself. `etl/loader.py bulk_insert_rows` now wraps each row in `async with session.begin_nested(): add(); await flush()` (SAVEPOINT) with `except SQLAlchemyError: log + continue`.

**Why this matters (reusable pattern for this codebase):** this project's idempotent loader pattern is: `_row_exists()` SELECT (unwrapped) → `begin_nested()` SAVEPOINT around `add`+`flush` (wrapped in try/except) → single `session.commit()` at the very end in `load_rows`. This is the correct async-SQLAlchemy idiom for per-row error isolation inside one larger transaction — `begin_nested()` requires the outer transaction to already be autobegun (guaranteed here because `_row_exists`'s SELECT always runs first), and on exception the nested transaction's `__aexit__` does rollback-to-savepoint + reraise automatically, so the outer session is NOT left unusable.

**Residual finding (🟡 Major, not blocking, flagged for follow-up):** `except SQLAlchemyError` in `bulk_insert_rows` is broader than "single bad row" — it also catches connection-level fatal errors (`OperationalError`, `PendingRollbackError` are both `SQLAlchemyError` subclasses), which would get logged as "單列寫入失敗，略過此列" even when the real cause is a dead DB connection. Verified this does NOT cause a silent false-success exit code, because: (a) the next row's `_row_exists()` SELECT is NOT wrapped in try/except and will raise unhandled if the connection is truly dead; (b) `load_rows` only commits once at the end; (c) `etl/run.py:main()` has a top-level `except Exception` that logs and does `sys.exit(1)`. So worst case is a handful of misleading per-row ERROR logs before a loud crash — not a masked outage. Recommend narrowing the except (e.g. `DataError`/`IntegrityError`, or checking `exc.connection_invalidated`) as a fast-follow, but did not treat as a blocker this round since no AC/TC covers mid-load connection loss and the safety nets already prevent silent success.

**Process note:** this codebase's card convention treats "Major" findings during Code Review as bounce-worthy (round 1 bounced on 3 Majors). When a new Major surfaces on a later round, judge severity against whether it can cause silent/undetected failure — if downstream safety nets (top-level exception handler, single final commit) already prevent that, it's reasonable to pass with a documented follow-up rather than starting another round-trip.

Round 2 outcome: ✅ 通過, card status → QA測試. This was the 2nd rejection-free round (round 1 was rejection #1); still well under the 3-rejection→需求確認中 threshold, no action needed there.
