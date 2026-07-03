---
name: feedback-tc07-env-testing
description: pydantic-settings 讀 .env 的特性：測試缺少環境變數必須替換真實 .env 檔案，env -i 或 os.environ.pop 無效
metadata:
  type: feedback
---

測試「缺少必要環境變數時啟動失敗」時，若 config.py 使用 `SettingsConfigDict(env_file=".env")`，pydantic-settings 會在 `Settings()` 初始化時讀取 `.env` 檔案，覆蓋 shell 環境變數。

**因此以下方式均無效：**
- `env -i ... uv run python`（shell 環境清空但 .env 仍被讀取）
- `os.environ.pop('DATABASE_URL', None)`（在 Settings() 之前 pop 仍無用）
- `uv run --env-file /tmp/...`（與 .env 合併而非取代）

**正確方式：**
1. `cp .env /tmp/.env.backup`
2. 用缺少目標變數的 .env 替換 `cp /tmp/.env.no-db .env`
3. 執行測試
4. 務必 `cp /tmp/.env.backup .env` 還原（即使測試失敗也要還原）

**Why:** pydantic-settings 的 env_file 在類別層級被讀取，優先於 shell 環境。
**How to apply:** 任何以 pydantic-settings 管理設定的 Python 專案，TC-07 類型測案都必須替換實體 .env 檔案。備份還原步驟要在同一個 bash 命令鏈（`&&`）中完成，確保原子性。

See also: [[project-overview]]
