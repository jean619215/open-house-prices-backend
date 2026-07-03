# QA Engineer Memory Index

## Project Context
- [Project overview](project-overview.md) — ports, stack, task workflow for this project

## Feedback & Lessons
- [TC-07 env var testing](feedback-tc07-env-testing.md) — pydantic-settings reads .env at class init; must swap real .env file to test missing vars
- [断线情境 timeout verification](feedback-disconnect-timeout.md) — TC-04/TC-05 response time and JSON field validation pattern
- [ETL 邊界條件清單](feedback-etl-boundary-conditions.md) — ETL 類任務 13 個常遺漏的驗收面向（含換算公式驗算、BOOLEAN三態、冪等反向、特殊邊界值、時間動態描述、sentinel 值需對每個消費欄位補測案、批次寫入單列隔離）
- [無實際 DB 時的驗收方式](feedback-no-live-db-verification.md) — docker daemon 不存在時如何用現有 pytest 替代驗證、卡片記錄驗證方式的原則、grep/ruff exit code 易誤判細節
