---
name: project-etl-field-gaps
description: Known schema gaps between 實價登錄 CSV source and transactions table — decisions resolved 2026-06-22
metadata:
  type: project
---

Key gaps identified during TASK-002 ETL implementation (see `etl/field_gap_report.md` for full detail):

**RESOLVED — DB stores m², not ping (決策 1, 2026-06-22):**
`area_sqm` and `price_per_sqm` columns store the raw MOI source values in m² and TWD/m².
ETL functions are `parse_area_sqm` and `parse_price_per_sqm` (no unit conversion).
Frontend is responsible for converting: 坪 = m² ÷ 3.305785; 元/坪 = 元/m² × 3.305785.
Column names `area_sqm` / `price_per_sqm` now match their actual units — do NOT rename.

**RESOLVED — building_type is TEXT (決策 2, 2026-06-22):**
`building_type` was changed from VARCHAR(20) to TEXT via Alembic migration 002_building_type_to_text.
Model in `shared/models.py` uses `Text` (no length limit).

**PENDING — Idempotency key performance (決策 3, 2026-06-22, no change yet):**
Current dedup uses per-row SELECT before INSERT (O(n) queries). Kept as-is for now.
Future TASK: add DB unique index on `(address, transaction_date, floor, area_sqm, price_total)`
and switch to `INSERT … ON CONFLICT DO NOTHING`.
Trigger: full-country import, historical backfill, or scheduled ETL.

**Source has no stable unique key:** The `編號` field in MOI CSV is not stable across re-downloads;
composite key `(address, transaction_date, floor, area_sqm, price_total)` is the approved dedup strategy.

**Fields dropped (no table column):** 交易標的, 土地移轉總面積, 都市土地使用分區, 主要用途, 主要建材, 格局(房/廳/衛), 有無管理組織, 備註, 編號, etc.

**Why:** Documented as output of AC-25/AC-26 for post-import schema discussion.

**How to apply:** When a future TASK changes units or adds columns, the unit decision (m² in DB, ping in frontend) is final as of 2026-06-22. Check `etl/field_gap_report.md` for the authoritative record.
