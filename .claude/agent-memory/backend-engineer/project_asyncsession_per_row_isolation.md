---
name: project-asyncsession-per-row-isolation
description: How to isolate a single bad row's DB error in a batch insert loop using AsyncSession.begin_nested() (SAVEPOINT), and how to mock it in tests
metadata:
  type: project
---

TASK-002 Code Review Major #3 (2026-07-03): `etl/loader.py`'s `bulk_insert_rows` originally did `session.add(txn)` per row and one `session.commit()` at the very end. A single malformed row (e.g. `floor` value too long for its column, common for 實價登錄's multi-building 合併交易 strings) would leave the whole PostgreSQL transaction aborted, killing the entire batch — a bare `try/except` around `session.add()` does NOT help, because SQLAlchemy/asyncpg only raises the DB-level error at flush/commit time, by which point the connection is already in "current transaction is aborted" state and unusable until rolled back.

**Why:** Without a SAVEPOINT, catching the exception per-row is cosmetic — the surrounding session is still poisoned for all subsequent statements (including the next row's dedup SELECT). The correct fix is to wrap each row's insert in its own nested transaction so only that row's SAVEPOINT rolls back on error, leaving the outer transaction and the rest of the batch intact.

**How to apply:**
```python
try:
    async with session.begin_nested():
        txn = Transaction(**row)
        session.add(txn)
        await session.flush()
except SQLAlchemyError:
    logger.error("單列寫入失敗，略過此列：...", exc_info=True)
    continue
inserted += 1
```
Key gotcha: `session.begin_nested()` is a **synchronous call** that returns an async-context-manager object (like `session.begin()`) — do NOT `await` the call itself, only `async with` it.

**Mocking this in tests:** a plain `AsyncMock()` session does not auto-generate a working `begin_nested()` context manager. You must explicitly wire it:
```python
def _make_nested() -> AsyncMock:
    nested = AsyncMock()
    nested.__aenter__ = AsyncMock(return_value=nested)
    nested.__aexit__ = AsyncMock(return_value=False)  # False = don't suppress, re-raise like real SAVEPOINT rollback
    return nested

session.begin_nested = MagicMock(side_effect=_make_nested)  # fresh CM per call
session.flush = AsyncMock()  # set side_effect=[...] per-row to simulate a specific row failing
```
Any session mock fixture used for `etl.loader` (directly or transitively via `etl.pipeline.run_pipeline`) needs both `begin_nested` and `flush` wired, or the loader code will raise `AttributeError`/`TypeError` before it even reaches real logic. See `tests/test_etl_loader.py` and `tests/test_etl_pipeline.py`.
