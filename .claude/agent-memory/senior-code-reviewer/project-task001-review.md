---
name: project-task001-review
description: TASK-001 backend project initialization — pre-implementation spec review findings and risk points
metadata:
  type: project
---

TASK-001 是後端初始化任務，審查發生在「實作前」的規格確認階段（Code Review 前置審查，非程式碼審查）。

**Key findings:**

1. Alembic env.py 必須同時支援 async engine（run_async_migrations）與 sync engine（offline migration），卡片未提及此分叉，容易讓 backend engineer 踩坑。
2. TC-08 並發測試（10 req）缺少連線池最小配置要求（pool_size, max_overflow），若未在規格中指定，工程師可能用預設值導致測試不穩定。
3. TC-04/TC-05 健康檢查斷線情境缺少 timeout 規格（斷線時 /health 應在幾秒內回應），沒有 timeout 則 /health 在 DB/Redis 掛掉時可能長時間 hang。
4. Transaction model 缺少欄位型別規格（price_total/price_per_sqm 是 Numeric 還是 Float？transaction_date 是 Date 還是 DateTime？），會影響後續 ETL 與 ML 的 schema 相容性。
5. Alembic migration 腳本名稱 `001_create_transactions.py` 不符合 Alembic 預設命名慣例（應含 revision id），需要明確說明使用 `--rev-id` 或接受自動生成 id。
6. SECRET_KEY 列在 .env.example 但 TASK-001 沒有任何端點需要它，缺少說明為何此階段就要求（可能是 pydantic-settings 驗證必填）。
7. Docker Compose healthcheck 的 interval/timeout/retries 參數未定義，TC-01 的 "healthy" 狀態依賴此設定。

**Why:** 這些缺漏在實作時會造成返工或模糊判斷。
**How to apply:** 審查後續 TASK 時，優先檢查 model 欄位型別規格、async/sync 雙模式、timeout 設定是否在卡片中明確定義。
