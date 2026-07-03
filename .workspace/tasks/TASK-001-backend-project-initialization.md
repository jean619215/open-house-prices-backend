# TASK-001 Backend Project Initialization

## 狀態
完成

## 類型
後端

## 需求描述
建立後端專案基礎結構。
完成後，所有後續 TASK 的開發者可以直接開始寫功能，不需要再處理環境與設定問題。

技術決策：
- 使用 Async（asyncpg + SQLAlchemy async engine）
- 套件管理：uv
- 本地環境：Docker Compose

---

## 驗收標準

- [x] `docker compose up -d` 可成功啟動 PostgreSQL 15 + PostGIS 3.3 + Redis 7
- [x] `uv run uvicorn api.main:app --reload` 可成功啟動 FastAPI
- [x] `GET /health` 回傳 HTTP 200，確認 DB 與 Redis 連線正常
- [x] `alembic upgrade head` 成功執行，transactions 表建立完成
- [x] `.env.example` 包含所有必要環境變數
- [x] 缺少必要環境變數時，啟動失敗並顯示明確錯誤訊息
- [x] `uv run ruff check .` 無錯誤
- [x] `uv run pytest` 全數通過

---

## 測案

### TC-01 Docker 服務啟動
- Given：本機已安裝 Docker
- When：執行 `docker compose up -d`
- Then：postgres、redis 容器狀態皆為 healthy

### TC-02 FastAPI 啟動
- Given：Docker 服務正常、.env 設定完整
- When：執行 `uv run uvicorn api.main:app --reload`
- Then：服務啟動成功，無錯誤訊息

### TC-03 健康檢查 - 正常
- Given：FastAPI、PostgreSQL、Redis 皆正常運行
- When：`GET /health`
- Then：HTTP 200，回傳 `{"status": "ok", "db": "connected", "redis": "connected"}`

### TC-04 健康檢查 - DB 斷線
- Given：PostgreSQL 容器停止
- When：`GET /health`
- Then：HTTP 503，回傳 `{"status": "error", "db": "disconnected", "redis": "connected"}`

### TC-05 健康檢查 - Redis 斷線
- Given：Redis 容器停止
- When：`GET /health`
- Then：HTTP 503，回傳 `{"status": "error", "db": "connected", "redis": "disconnected"}`

### TC-06 Alembic Migration
- Given：PostgreSQL 正常運行
- When：執行 `alembic upgrade head`
- Then：無錯誤，alembic_version 表存在，transactions 表建立完成，欄位型別依下方「Transaction 欄位型別表」。

### TC-07 環境變數缺失
- Given：.env 缺少 DATABASE_URL
- When：啟動 FastAPI
- Then：啟動失敗，顯示明確錯誤訊息說明哪個變數缺失，不拋出 KeyError

### TC-08 Async 並發連線
- Given：FastAPI 啟動，DB 正常
- When：同時發送 10 個 `GET /health` 請求
- Then：全部回傳 200，無 timeout 或連線錯誤

---

## 完成後的專案結構

```
open-house-prices-backend/
├── api/
│   ├── __init__.py
│   ├── main.py              ← FastAPI app、middleware、router 掛載
│   └── routers/
│       └── health.py        ← GET /health
├── etl/                     ← 空目錄，TASK-002 使用
├── ml/                      ← 空目錄，後續使用
├── shared/
│   ├── __init__.py
│   ├── config.py            ← pydantic-settings 環境變數管理
│   ├── database.py          ← async SQLAlchemy engine + session
│   └── models.py            ← Transaction SQLAlchemy Model
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_create_transactions.py
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── .env.example
├── .env                     ← gitignore
├── docker-compose.yml
├── pyproject.toml
└── alembic.ini
```

---

## 技術規格

### Transaction 欄位型別表（B1）
> 金額相關一律使用 `Numeric`，禁止 `Float`（精度問題）。

| 欄位 | 型別 | 備註 |
|------|------|------|
| id | BIGINT PK（autoincrement） | |
| address | TEXT NOT NULL | |
| city | VARCHAR(10) | |
| district | VARCHAR(20) | |
| location | GEOMETRY(Point, 4326) | PostGIS，SRID 4326 |
| price_total | NUMERIC(14, 0) | 單位：元 |
| price_per_sqm | NUMERIC(12, 2) | 元/坪 |
| area_sqm | NUMERIC(8, 2) | 坪數 |
| floor | **由 backend-engineer 依實價登錄實際資料格式提案後決定** | 需處理「全」「地下」等非數字樓層；提案請寫進歷程 |
| building_age | SMALLINT | 年數 |
| building_type | VARCHAR(20) | |
| has_parking | BOOLEAN | |
| mrt_distance | NUMERIC(8, 1) | 公尺 |
| transaction_date | DATE | 實價登錄為月精度，存當月 1 日 |
| created_at | TIMESTAMPTZ DEFAULT now() | |

### Alembic env.py async 規格（B2）
- async engine（asyncpg）無法直接套 Alembic 預設 env.py。
- online migration 需以 `asyncio.run()` + `connection.run_sync()` 包裝執行。
- offline 模式可省略（本 TASK 不要求產生 SQL script）。
- migration 檔名採用 `--rev-id 001` 並於 `alembic.ini` 設 `file_template`，以維持 `001_create_transactions.py` 命名（M3）。

### /health timeout 規格（B3）
- DB 存活探測：`SELECT 1`，statement timeout 2 秒。
- Redis 存活探測：`PING`，socket timeout 1 秒。
- 整體 /health 須於 3 秒內回應，逾時視為失敗回傳 503。
- 探測須避免 block event loop（斷線情境不得無限等待）。

### Docker / 連線池 / 設定（M1、M2、N1、N2、N3）
- docker-compose healthcheck：postgres 用 `pg_isready`、redis 用 `redis-cli ping`，建議 `interval 5s / timeout 3s / retries 5 / start_period 10s`（M1）。
- SQLAlchemy async engine：`pool_size=10, max_overflow=5`（由 config.py 控制），確保 TC-08 通過（M2）。
- SECRET_KEY 在本 TASK 無端點使用，允許在 `.env` 給 dummy 值；但仍須從 `.env` 讀取，禁止 hardcode 於程式碼（N1）。
- 測試策略：`test_health.py` 以 `AsyncMock` mock DB/Redis 連線做 unit test（涵蓋 TC-03 及模擬斷線）；TC-04/TC-05/TC-08 需真實停容器/並發，列為 integration 手動驗證（N2）。
- `etl/`、`ml/` 空目錄需加 `.gitkeep` 以進版控（N3）。

### 環境變數（.env.example）
> port 改用非預設值以避開本機 postgres(5432) 與其他專案容器（pf-postgres 5433、pf-redis 6379），詳見 README。
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5434/realestate
REDIS_URL=redis://localhost:6380
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
```

### 套件
```
fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg,
alembic, geoalchemy2, pydantic-settings, redis[asyncio],
pytest, pytest-asyncio, httpx, ruff
```

---

---

## QA 測試結果（2026-06-16）

執行人：QA Engineer
環境：postgres:5434、redis:6380（docker compose）、FastAPI:8000

| 測案 | 結果 | 關鍵證據 |
|------|------|----------|
| TC-01 Docker 服務啟動 | ✅ 通過 | postgres、redis 容器 STATUS=healthy |
| TC-02 FastAPI 啟動 | ✅ 通過 | uvicorn PID=79732 啟動無錯誤 |
| TC-03 /health 正常 | ✅ 通過 | HTTP 200 `{"status":"ok","db":"connected","redis":"connected"}` |
| TC-04 /health DB 斷線 | ✅ 通過 | HTTP 503 `{"status":"error","db":"disconnected","redis":"connected"}`，回應時間 0.053s（<3s）|
| TC-05 /health Redis 斷線 | ✅ 通過 | HTTP 503 `{"status":"error","db":"connected","redis":"disconnected"}`，回應時間 0.080s（<3s）|
| TC-06 Alembic Migration | ✅ 通過 | alembic_version=001，transactions 表 15 欄位型別與 B1 規格完全吻合（含 floor VARCHAR(10)、location GEOMETRY(Point,4326)、price_* NUMERIC）|
| TC-07 環境變數缺失 | ✅ 通過 | `ValidationError: 1 validation error for Settings / database_url / Field required`，未拋 KeyError |
| TC-08 Async 並發 | ✅ 通過 | 10/10 全 HTTP 200 `{"status":"ok"...}`，最大回應時間 0.201s |

**通過摘要：8/8 全數通過。無失敗案例。**

TC-04/TC-05 斷線情境為本次 QA 最關鍵的手動驗證項目，確認 /health 在 DB/Redis 中斷時均能於 3 秒內回傳 503 且 JSON 欄位正確。

---

## 不在此 TASK 範圍
- ETL 實作（TASK-002）
- 業務 API 端點（TASK-003 之後）
- Redis Cache 邏輯
- ML 相關
- Retry 機制

---

## 歷程

| 日期 | 角色 | 內容 |
|------|------|------|
| 2026-06-15 | QA | 建立卡片，撰寫驗收標準與測案 |
| 2026-06-15 | QA | 需求確認完畢，狀態更新為開發中 |
| 2026-06-15 | Code Review | 實作前審查：補齊 B1 欄位型別表、B2 Alembic async env.py、B3 /health timeout，及 M1/M2/M3/N1/N2/N3 規格。floor 型別交由 backend-engineer 依實際資料提案。通過後交付開發 |
| 2026-06-16 | Backend Engineer | **floor 型別決策**：採用 VARCHAR(10)。實價登錄原始資料的「樓層」欄位包含 '3F'、'B1'、'B全'、'全'、'頂層' 等非純整數字串，SMALLINT 無法儲存此類值，須以字串保留原始值；數字解析延遲至 ETL/查詢階段執行。 |
| 2026-06-16 | Backend Engineer | 完成 TASK-001 實作：建立完整專案結構（shared/config.py、shared/database.py、shared/models.py、api/main.py、api/routers/health.py）、Alembic async env.py（asyncio.run + run_sync）、001_create_transactions.py migration（含 5 個索引）、docker-compose.yml（healthcheck）、.env.example；uv run pytest 4/4 通過，uv run ruff check 無錯誤。TC-01/04/05/08 需 Docker 環境，以 unit test（AsyncMock）覆蓋等效邏輯，整合驗證請於 Docker 環境手動執行。 |
| 2026-06-16 | Code Review | 環境驗證（TC-06）時發現並修正 2 個會讓 `alembic upgrade head` 失敗的實作 bug：(1) alembic.ini `file_template` 跳脫錯誤 `%(rev)s` → `%%(rev)s`；(2) models.py 用 `Text().with_variant("VARCHAR(10)", ...)` 傳字串給 with_variant 導致 AttributeError，改為 `String(10/20)`（city/district/floor/building_type）。另因本機 postgres(5432) 與 pf-postgres(5433) 佔用，postgres 對外改 5434、redis 讓出 6379；同步更新 .env/.env.example/README。修正後 migration 成功、transactions 表欄位與索引正確、pytest 4/4、ruff 乾淨。TC-03/04/05/08 待手動驗證。 |
| 2026-06-16 | Code Review | redis 對外 port 由讓出 6379 改為映射 **6380**（避免影響其他專案的 pf-redis，兩者可並存）；同步更新 docker-compose.yml / .env / .env.example / README。本專案 redis(6380) 與 pf-redis(6379) 皆 healthy、ping 通。 |
| 2026-06-16 | QA | 狀態更新為「QA測試」，開始執行 TC-01~TC-08 整合驗收。 |
| 2026-06-16 | QA | **QA 驗收全數通過（8/8）**。詳細結果見下方「QA 測試結果」節。狀態更新為「完成」。 |
