---
name: project-overview
description: Open House Prices Backend — ports, tech stack, task workflow, and QA-relevant environment facts
metadata:
  type: project
---

本專案後端服務（台灣房地產價格地圖）QA 相關環境事實：

**Port 配置（不可混淆）：**
- 本專案 postgres → host 5434（容器內 5432）
- 本專案 redis → host 6380（容器內 6379）
- pf-postgres（其他專案）→ host 5433，絕對不動
- pf-redis（其他專案）→ host 6379，絕對不動

**容器管理：**
- 停/啟容器一律用 `docker compose stop <service>` / `docker compose start <service>`
- 驗證容器狀態：`docker compose ps`

**執行工具：**
- 套件管理：uv（不用 pip）
- 測試：`uv run pytest`
- Lint：`uv run ruff check .`
- Migration：`uv run alembic upgrade head`
- Server：`uv run uvicorn api.main:app --port 8000`

**任務卡片狀態流程：**
需求確認中 → QA撰寫測案 → 開發中 → Code Review → QA測試 → 完成

**Why:** 本機有多個 Postgres/Redis 容器並行，port 混淆會污染其他專案。
**How to apply:** 每次測試前先 `docker compose ps` 確認本專案容器 port，不假設預設 5432/6379。
