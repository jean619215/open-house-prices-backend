---
name: floor-field-type-decision
description: Decision to use VARCHAR(10) for the floor column in transactions table
metadata:
  type: project
---

The `floor` column in the `transactions` table uses `VARCHAR(10)` (not `SMALLINT`).

**Why:** Taiwan's 實價登錄 raw data contains non-numeric floor strings: '3F', 'B1', 'B全', '全', '頂層'. A SMALLINT cannot store these values. The raw string must be preserved in the DB; numeric parsing (e.g. extracting floor number for ML features) is deferred to ETL or query time.

**How to apply:** When the ETL (TASK-002) parses the floor field, convert to an integer only in a derived/computed column or at query time — never lose the original string in the primary column. If a numeric floor representation is needed for ML, consider adding a separate `floor_num SMALLINT` column populated by ETL.
