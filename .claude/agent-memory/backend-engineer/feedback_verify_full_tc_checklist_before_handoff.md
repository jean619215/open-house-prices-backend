---
name: feedback-verify-full-tc-checklist-before-handoff
description: Before moving a card to Code Review, run every individual command listed in its TC (not just a generic `ruff check .`) — subsets of rules like pydocstyle are opt-in and easy to silently skip
metadata:
  type: feedback
---

When a task card's TC lists a specific sequence of verification commands (e.g. TASK-002's TC-16: `ruff check etl/`, `ruff format --check etl/`, `ruff check --select ANN etl/`, `ruff check --select D etl/`, `grep -r "print(" etl/`), run that exact list verbatim before updating the card status — do not substitute a single broader command and assume it covers everything. Rule subsets like `--select D` (pydocstyle) or `--select ANN` (annotations) are not part of default `ruff check` output and can pass "ruff check ." clean while still failing the card's actual AC.

**Why:** TASK-002 was marked "開發中→Code Review-ready" once already, but a `--select D` docstring check (23 D413 violations, see [[feedback-ruff-google-docstring-d413]]) had not actually been run, and this was only caught when the upstream coordinator independently re-verified against the card's AC/TC text rather than trusting the handoff note.

**How to apply:** Treat the TC command list on the card as the literal acceptance script, not a paraphrase. Run each command separately, capture its exit code, and only write "全部通過" in the history log after every single one has actually been executed in this session (not inferred from a prior partial run).
