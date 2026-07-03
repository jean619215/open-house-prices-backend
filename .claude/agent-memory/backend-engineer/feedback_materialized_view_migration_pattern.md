---
name: feedback-materialized-view-migration-pattern
description: Alembic has no native op for materialized views — use op.execute() raw SQL, always WITH DATA (never WITH NO DATA), and validate migration syntax offline with `alembic upgrade head --sql` when no DB is reachable
metadata:
  type: feedback
---

Alembic's `op` module has no `create_materialized_view`/`drop_materialized_view` helper (unlike `op.create_table`). Use `op.execute("CREATE MATERIALIZED VIEW ... AS SELECT ... WITH DATA")` in `upgrade()` and `op.execute("DROP MATERIALIZED VIEW view_name")` in `downgrade()`.

Critical gotcha (TASK-003, `city_stats` view): always end the `CREATE MATERIALIZED VIEW` statement with `WITH DATA`, never `WITH NO DATA` (Alembic/Postgres default behavior can vary, so be explicit). A matview created `WITH NO DATA` raises `materialized view "X" has not been populated` on the very first `SELECT` against it — this turns a brand-new environment's first API call into a 500 before any ETL has ever run. `WITH DATA` guarantees the view is queryable immediately after migration, even if it evaluates to zero rows (source table empty).

If you also add a unique index on the view (e.g. for a future `REFRESH ... CONCURRENTLY` upgrade, which *requires* one), it can be created the normal way: `op.execute("CREATE UNIQUE INDEX ix_name ON view_name (col)")`. `DROP MATERIALIZED VIEW` cascades and drops that index too, so `downgrade()` doesn't need a separate `DROP INDEX`.

**Verifying without a live DB:** this environment has no docker daemon (`docker ps` fails to connect to `/var/run/docker.sock`), so `alembic upgrade head` / `downgrade` against a real Postgres cannot be run. Alembic supports an **offline mode** that only needs `alembic.ini` + the migration files (no DB connection at all): `DATABASE_URL=... alembic upgrade head --sql` and `alembic downgrade 003:002 --sql` print the exact SQL that would run, and fail loudly on Python/SQL syntax errors. This caught nothing wrong in TASK-003 but is the right first check before shipping a migration untested against a real DB — always run it and paste the generated SQL into the card's history as partial evidence, then clearly flag which TCs still need a real-DB run.

**Why:** matches the project's existing 001/002 migration docstring conventions ([[project_floor_field_decision]]) and avoids an easy-to-miss production incident (500 on cold start).

**How to apply:** for any future materialized view migration, copy this upgrade/downgrade shape, always use `WITH DATA`, and run the offline `--sql` check before marking Code Review when no DB is reachable.
