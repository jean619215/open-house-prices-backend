---
name: feedback-grep-stale-docs-on-decision-change
description: When a 決策 (requirement decision) changes field semantics (unit, precision, meaning), grep the WHOLE repo for old wording — not just the etl/ module under direct review — before marking the card ready for review
metadata:
  type: feedback
---

TASK-002's 決策 1 (2026-06-22, area/price switched from ping 坪 to raw m² passthrough, transaction_date switched from month-1st to full date) was implemented and re-verified twice in `etl/` (transform.py, tests, AC/TC text) — but `shared/models.py`'s `Transaction` docstring (`price_per_sqm: Price per ping (坪)`, `transaction_date: ... stored as the 1st of that month`) was never updated, and this stale wording was only caught by Senior Reviewer on 2026-07-03, a full Code Review cycle later (Major #1).

**Why:** A decision that changes field semantics usually originates in one module (e.g. `etl/transform.py`) but the same semantics are often *documented* in a completely different layer (`shared/models.py` ORM docstrings, which API/ML developers read directly and don't necessarily open `etl/` to cross-check). Fixing only the layer you're actively working in leaves misleading docs alive elsewhere.

**How to apply:** After implementing a 決策 that changes a field's unit, precision, or meaning, run `grep -rn "<old term>" --include=*.py .` (e.g. `grep -rn "ping\|坪\|1st of that month"` ) across the *entire* repo, not just the directory you're editing, before calling the card review-ready. Treat `shared/` model docstrings as a first-class doc surface, equal priority to the ETL code itself. See [[project-etl-field-gaps]] for the broader unit-mismatch history on this same field.
