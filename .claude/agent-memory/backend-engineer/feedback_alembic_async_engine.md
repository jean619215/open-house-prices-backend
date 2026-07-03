---
name: alembic-async-engine-pattern
description: Correct pattern for using asyncpg (async engine) with Alembic env.py
metadata:
  type: feedback
---

Alembic's default env.py assumes a synchronous engine. When using `asyncpg` / `SQLAlchemy async`, the online migration function must be wrapped with `asyncio.run()` and `connection.run_sync()`.

**Why:** Alembic's `context.run_migrations()` is synchronous; async engines cannot be used directly.

**How to apply:**

```python
async def run_migrations_online() -> None:
    connectable = create_async_engine(url, future=True)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

Also ensure `sys.path` includes the project root so `shared/` imports work, using `Path(__file__).resolve().parent.parent` (not `os.path` — ruff PTH rules flag os.path usage).
