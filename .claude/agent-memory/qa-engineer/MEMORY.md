# QA Engineer Memory Index

## Project Context
- [Project overview](project-overview.md) — ports, stack, task workflow for this project

## Feedback & Lessons
- [TC-07 env var testing](feedback-tc07-env-testing.md) — pydantic-settings reads .env at class init; must swap real .env file to test missing vars
- [断线情境 timeout verification](feedback-disconnect-timeout.md) — TC-04/TC-05 response time and JSON field validation pattern
- [ETL 邊界條件清單](feedback-etl-boundary-conditions.md) — ETL 類任務 13 個常遺漏的驗收面向（含換算公式驗算、BOOLEAN三態、冪等反向、特殊邊界值、時間動態描述、sentinel 值需對每個消費欄位補測案、批次寫入單列隔離）
- [無實際 DB 時的驗收方式](feedback-no-live-db-verification.md) — docker daemon 不存在時如何用現有 pytest 替代驗證、卡片記錄驗證方式的原則、grep/ruff exit code 易誤判細節
- [Materialized View 均價 API 測試陷阱](feedback-materialized-view-api-testing.md) — /api/prices/{level} 系列：WITH DATA vs WITH NO DATA 500 陷阱、GROUP BY NULL 分組鍵、均價/筆數分母分子分離、四捨五入精度依據、ETL 兩種 0 筆情境的 REFRESH 判斷、回傳排序未定案處理
- [Lint TC 與 AC scope 不一致](feedback-lint-tc-scope-mismatch.md) — 程式碼規範類 TC 的 ruff --select ANN/D 檢查目標須與對應 AC 的檔案範圍完全一致，否則會被既有無關檔案的違規拖累誤判失敗
