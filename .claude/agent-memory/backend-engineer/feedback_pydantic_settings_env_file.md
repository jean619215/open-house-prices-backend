---
name: pydantic-settings-env-file-bypass
description: How to test ValidationError for missing env vars when a .env file exists on disk
metadata:
  type: feedback
---

When a `.env` file is present on disk, `pydantic-settings` silently reads it even after clearing `lru_cache` and removing the var from `os.environ`. This means `get_settings()` will not raise `ValidationError` in tests.

**Why:** `Settings()` (with `SettingsConfigDict(env_file=".env")`) always reads the .env file unless told otherwise. Just removing a key from `os.environ` is insufficient.

**How to apply:** In unit tests that must verify missing-var behaviour, instantiate `Settings` directly with `_env_file=None` to disable .env loading:

```python
Settings(_env_file=None)  # type: ignore[call-arg]
```

This is the correct pattern for TC-07-style tests. Do not rely on `get_settings.cache_clear()` + `os.environ.pop()` alone.
