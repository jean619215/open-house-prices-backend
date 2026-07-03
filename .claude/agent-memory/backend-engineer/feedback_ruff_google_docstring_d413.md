---
name: feedback-ruff-google-docstring-d413
description: ruff pydocstyle (Google convention) requires a blank line after the LAST docstring section before the closing triple-quote — easy to miss, safe to autofix
metadata:
  type: feedback
---

When this project's ruff config enables pydocstyle with the Google convention, `uv run ruff check --select D` flags D413 ("Missing blank line after last section") whenever a docstring's final section (`Args:`, `Returns:`, `Raises:`, `Yields:`, `Note:`, etc.) is immediately followed by the closing `"""` with no blank line in between. This is easy to write correctly for the *first* section but forget on the *last* one, especially when a docstring has just one section.

Also note: ruff prints benign warnings about incompatible docstring rules being auto-ignored (`D203`/`D211`, `D212`/`D213`) — these are not errors and don't affect exit code; don't mistake them for failures.

**Why:** TASK-002 shipped with 23 D413 violations across 7 `etl/` files (constants.py, downloader.py, loader.py, parser.py, pipeline.py, run.py, transform.py) that were only caught when a coordinator independently re-ran the AC-24/TC-16 command list — the previous "Code Review" handoff had skipped this specific `--select D` check.

**How to apply:** Before marking any card's docstring-related AC as done, run `uv run ruff check --select D etl/` (or the relevant package) specifically — don't rely on the default `ruff check` ruleset, since D-rules are often not in the default select set. `ruff check --select D413 --fix` auto-fixes this safely (it only inserts a blank line), but still diff-review the result to confirm no logic/formatting beyond the blank line changed. See [[feedback-verify-full-tc-checklist-before-handoff]] for the broader lesson this incident taught.
