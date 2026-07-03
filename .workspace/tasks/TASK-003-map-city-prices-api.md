# TASK-003 地圖縣市均價 API — GET /api/prices/city

## 狀態
Code Review

## 類型
後端（API + DB）

## 需求描述
提供「房地產交易地圖」前端所需的縣市層級均價 API，讓地圖能以 Choropleth 顯示各縣市房價與成交筆數。
本期目標是「讓地圖能正確顯示縣市層級均價」，屬 Phase 1 MVP 的第一個對外 API 端點，非鄉鎮市區/村里層級。

技術決策（2026-07-03 與需求方討論確認）：
- **層級範圍**：本期僅支援縣市層級 `GET /api/prices/city`，不做 Notion 規劃中的 `GET /api/prices/{level}` 動態層級。鄉鎮市區、村里層級留待後續 TASK（依賴地址 geocoding 與行政區邊界資料，目前 `transactions.location` 全為 NULL，尚未有這些資料）。
- **均價計算方式**：建立 `city_stats` Materialized View（依 Notion 系統規劃），對 `transactions` 表以 `city` 分組，預先算好均價與成交筆數；API 直接查詢這張 View，不對 `transactions` 做即時 GROUP BY。
- **Refresh 機制**：`etl/pipeline.py` 的 ETL pipeline 執行成功後，自動執行 `REFRESH MATERIALIZED VIEW city_stats`，確保每次手動跑完 ETL 後均價資料是最新的。本期不做獨立的排程或手動 refresh 端點（Notion 規劃的 `POST /api/etl/trigger` 留待後續 TASK）。
- **Cache**：本期不加 Redis cache，先確保功能正確；待資料量變大或有效能疑慮時再開後續 TASK 補上 cache-aside 邏輯。

---

## 本期範圍（要做）

### 資料庫
- 新增 Alembic migration，建立 `city_stats` Materialized View：
  - 依 `transactions.city` 分組
  - 欄位至少包含：`city`（縣市）、`avg_price_per_sqm`（均價，元/平方公尺）、`transaction_count`（成交筆數）
  - `price_per_sqm` 為 NULL 的列不計入均價分母，但仍計入該縣市的 `transaction_count`（成交筆數應反映實際成交數，均價僅反映有單價資料的成交）

### ETL 整合
- `etl/pipeline.py` 的 pipeline 執行成功寫入 `transactions` 後，自動執行 `REFRESH MATERIALIZED VIEW city_stats`。
- 若 ETL 本次匯入 0 筆新資料（如重跑冪等、或空 CSV），仍需視情況決定是否 refresh（避免每次都做不必要的 refresh，或者無害則一律 refresh，由開發時再定案並記錄）。

### API 端點
- 新增 `api/routers/prices.py`，實作 `GET /api/prices/city`：
  - 回傳 JSON array，每筆包含 `city`、`avg_price_per_sqm`、`transaction_count`
  - 對於目前完全沒有任何成交資料的縣市，不需出現在回傳結果中（因為 `city_stats` 是對 `transactions` 分組產生，沒有資料就沒有分組）
  - 需在 `api/main.py` 掛載此 router

---

## 不在本期範圍（已記錄，之後開單處理）
| 項目 | 說明 |
|------|------|
| 鄉鎮市區 / 村里層級 | 依賴 geocoding（`location`）與行政區邊界資料，獨立 TASK |
| `GET /api/prices/{level}` 動態層級 | 本期先做死縣市層級，之後有更多層級需求再重構為動態 `{level}` |
| Redis Cache | 本期不加，效能有疑慮時另開 TASK |
| `POST /api/etl/trigger` 手動觸發/refresh 端點 | Notion 規劃項目，本期靠 CLI + pipeline 內建 refresh 取代 |
| Materialized View 排程自動 refresh（非隨 ETL 觸發） | 本期 ETL 本身就是手動觸發，refresh 隨 ETL 走即可，獨立排程留待 ETL 排程化的後續 TASK |

---

## 驗收標準

> 每條標準皆可獨立判定「通過」或「失敗」。
> 通過：符合描述行為。失敗：不符合，或有額外非預期行為。
>
> 標記「（技術判斷）」者為卡片定案時尚未明確、由 QA 依專案慣例與現有程式脈絡做出的合理判斷，理由已寫在該條標準內，開發時若有更佳方案可提出討論，但預設以此為準。

### A. 資料庫（`city_stats` Materialized View）

- [ ] AC-01：新增 Alembic migration（revision `003`，`down_revision = "002"`，比照 `001_create_transactions.py`／`002_building_type_to_text.py` 的檔頭 docstring 慣例，說明建立目的與依據），`upgrade()` 建立 `city_stats` Materialized View，`downgrade()` 執行 `DROP MATERIALIZED VIEW city_stats`。
- [ ] AC-02：`city_stats` 至少包含三個欄位：`city`（字串，對應 `transactions.city`）、`avg_price_per_sqm`（數值，均價，元/平方公尺）、`transaction_count`（整數，成交筆數）。
- [ ] AC-03：`transactions.city IS NULL` 的列不得產生任何 `city_stats` 分組列（view 定義需排除 `city IS NULL`），即 `SELECT COUNT(*) FROM city_stats WHERE city IS NULL` 恆為 0。
- [ ] AC-04：`avg_price_per_sqm` 計算時，分母排除 `transactions.price_per_sqm IS NULL` 的列；但該縣市中 `price_per_sqm IS NULL` 的列仍計入 `transaction_count`。
- [ ] AC-05：若某縣市所有成交列的 `price_per_sqm` 皆為 NULL（該縣市有成交但完全無單價資料），`avg_price_per_sqm` 該列存 NULL（不得為 0，不得使 REFRESH 拋出除以零例外），`transaction_count` 仍為該縣市實際成交筆數（> 0）。
- [ ] AC-06（技術判斷）：`avg_price_per_sqm` 以 `ROUND(AVG(price_per_sqm), 2)` 計算，四捨五入至小數點後 2 位。理由：對齊 `transactions.price_per_sqm` 的 `Numeric(12, 2)` 來源精度，避免 `AVG()` 產生過多無意義小數位回傳給前端。
- [ ] AC-07（技術判斷）：migration 建立 Materialized View 時使用 `CREATE MATERIALIZED VIEW city_stats AS ... WITH DATA`（而非 `WITH NO DATA`）。理由：PostgreSQL 對「尚未 populate（`WITH NO DATA`）」的 matview 執行 `SELECT` 會拋出 `materialized view "city_stats" has not been populated` 錯誤；使用 `WITH DATA` 可確保 migration 執行完當下 view 即為已填入狀態（即使當時 `transactions` 為空、結果為 0 列），避免全新環境在第一次 ETL 執行前呼叫 API 就先出現 500 錯誤。
- [ ] AC-08：對全新資料庫依序執行 `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`，三個指令皆不拋出例外（exit code 0），downgrade 後 `city_stats` 不存在、再次 upgrade 後恢復存在。

### B. ETL 整合（自動 refresh）

- [ ] AC-09：`etl/pipeline.py` 的 `run_pipeline()` 在寫入步驟（`load_rows`）成功完成、且未拋出例外之後，執行 `REFRESH MATERIALIZED VIEW city_stats`（透過既有 async session 執行）。
- [ ] AC-10：若本次 ETL 下載或解析後無任何資料列可寫入（現有程式中 `city_csvs` 或 `all_rows` 為空、提前 `return` 的分支），不執行 REFRESH（因為根本未進入寫入步驟）。
- [ ] AC-11（技術判斷）：若本次 ETL 有進入寫入步驟，但本批資料因冪等性檢查全數判定為重複（`inserted == 0`），**仍然**執行 `REFRESH MATERIALIZED VIEW city_stats`。理由：REFRESH 為冪等操作，即使沒有新增列也不會產生錯誤結果；若改為「僅在 inserted > 0 才 refresh」需要額外判斷邏輯與風險（例如漏判某些會改變既有列均價的情境），本期以「只要進入寫入步驟就 refresh」換取實作簡單與資料一致性保證，待資料量大到 REFRESH 成本明顯時再開後續 TASK 優化為條件式 refresh 或 `CONCURRENTLY`。
- [ ] AC-12：若 `REFRESH MATERIALIZED VIEW city_stats` 執行失敗（拋出 DB 例外），`run_pipeline()` 以 logging（ERROR 層級）記錄錯誤，並讓例外往外拋出（不得吞掉），使 CLI（`python -m etl.run`）以非 0 exit code 結束。

### C. API 端點行為（正常情境）

- [ ] AC-13：新增 `api/routers/prices.py`，以 `APIRouter` 定義 `GET /api/prices/city`，並在 `api/main.py` 以 `application.include_router(prices.router)` 掛載（比照現有 `health.router` 掛載方式）。
- [ ] AC-14：正常情況下端點回傳 HTTP 200，`Content-Type: application/json`。
- [ ] AC-15（技術判斷：JSON 欄位命名）：回傳 body 為 JSON array（非包在 `{"data": [...]}` 等外層物件中），陣列中每個元素僅包含 `city`（string）、`avg_price_per_sqm`（number 或 null）、`transaction_count`（number，整數）三個 key，欄位命名一律 snake_case。理由：與卡片「本期範圍」指定的欄位名稱一致，並比照 `/health` 現有回傳（`db`、`redis`）的 snake_case 慣例。
- [ ] AC-16：端點實作直接查詢 `city_stats` view（不得對 `transactions` 表另外做即時 `GROUP BY`／聚合查詢）。
- [ ] AC-17：單次回傳陣列中不得出現重複的 `city` 值。
- [ ] AC-18（技術判斷：排序）：回傳陣列依 `city` 字串遞增排序。理由：卡片未指定排序方式，為使回傳結果可預期、測案可穩定斷言，選擇最簡單的字典序排序；之後若前端需要依均價或成交筆數排序，另開後續 TASK 調整。

### D. 異常/邊界情況

- [ ] AC-19：目前完全沒有任何成交資料的縣市，不出現在回傳陣列中。
- [ ] AC-20：`city_stats` 中某縣市 `avg_price_per_sqm IS NULL`（見 AC-05）時，對應回傳物件的 `avg_price_per_sqm` 欄位值為 JSON `null`（不得省略此 key、不得回傳 0 或字串 `"null"`），`transaction_count` 仍為該縣市實際成交筆數。
- [ ] AC-21：`transactions` 表完全無資料（如全新環境剛執行完 migration、尚未跑過任何 ETL）時，`GET /api/prices/city` 回傳 HTTP 200 與空陣列 `[]`，不得回傳 500 或拋出「materialized view has not been populated」例外（依賴 AC-07 的 `WITH DATA` 設計）。
- [ ] AC-22（技術判斷）：DB 連線失敗或查詢拋出例外時，端點回傳 HTTP 500（沿用 FastAPI 對未捕捉例外的預設處理，本期不做自訂錯誤回應格式；待有統一錯誤格式規範時另開 TASK 處理）。
- [ ] AC-23：對 `GET /api/prices/city` 帶入未定義的 query string 參數（如 `?foo=bar`）不影響回傳結果、不拋錯（FastAPI 對未宣告的 query 參數預設忽略）。

### E. 程式碼規範

- [ ] AC-24：`api/routers/prices.py` 所有公開函式（含 router handler）均有 type hint 與 Google 風格 docstring。
- [ ] AC-25：`uv run ruff check api/` 與 `uv run ruff format --check api/` 皆通過，無 error。
- [ ] AC-26：`api/routers/prices.py` 全程使用 Python logging 模組，不得出現任何 `print(` 呼叫。
- [ ] AC-27：新增的 migration 檔案本身亦有檔頭 docstring，說明建立 `city_stats` 的目的與依據（比照 001／002 慣例）。

---

## 測案

### TC-01 Migration 建立 city_stats，欄位與型別正確

- Given：全新資料庫，已執行至 `alembic upgrade 002`。
- When：執行 `alembic upgrade 003`（或 head，即含 city_stats 的 migration）。
- Then：
  1. 指令 exit code 0，無例外。
  2. `SELECT column_name FROM information_schema.columns WHERE table_name='city_stats'` 至少包含 `city`、`avg_price_per_sqm`、`transaction_count`。
  3. `SELECT relkind FROM pg_class WHERE relname='city_stats'` 回傳 `'m'`（materialized view）。

### TC-02 Migration downgrade 可逆

- Given：已執行 `alembic upgrade head`（含 city_stats migration）。
- When：依序執行 `alembic downgrade -1`，再 `alembic upgrade head`。
- Then：
  1. 兩個指令皆 exit code 0，無例外。
  2. downgrade 後 `SELECT COUNT(*) FROM pg_class WHERE relname='city_stats'` 回傳 0。
  3. 再次 upgrade 後回傳 1（`city_stats` 恢復存在）。

### TC-03 均價計算——排除 NULL price_per_sqm 分母，但計入筆數

- Given：`transactions` 表中「台北市」有 3 筆：`price_per_sqm` 分別為 `100000`、`200000`、`NULL`。
- When：執行 `REFRESH MATERIALIZED VIEW city_stats`，查詢 `SELECT * FROM city_stats WHERE city='台北市'`。
- Then：
  1. `avg_price_per_sqm = 150000.00`（(100000+200000)÷2，NULL 不計入分母，四捨五入至小數 2 位）。
  2. `transaction_count = 3`（NULL 單價那筆仍計入筆數）。

### TC-04 均價計算——某縣市所有列 price_per_sqm 皆為 NULL

- Given：`transactions` 表中「新北市」有 2 筆，`price_per_sqm` 皆為 `NULL`。
- When：REFRESH 後查詢 `SELECT * FROM city_stats WHERE city='新北市'`。
- Then：
  1. `avg_price_per_sqm IS NULL`（不得為 0，REFRESH 不得拋出除以零例外）。
  2. `transaction_count = 2`。

### TC-05 city 為 NULL 的列不產生分組

- Given：`transactions` 表中有 1 筆 `city IS NULL` 的資料（其餘欄位任意有效值）。
- When：REFRESH 後查詢 `SELECT COUNT(*) FROM city_stats WHERE city IS NULL`。
- Then：回傳 `0`。

### TC-06 完全無成交資料的縣市不出現於 city_stats

- Given：`transactions` 表中不存在任何 `city='高雄市'` 的列。
- When：REFRESH 後查詢 `SELECT COUNT(*) FROM city_stats WHERE city='高雄市'`。
- Then：回傳 `0`。

### TC-07 尚未執行過 ETL（全新環境）時 API 行為

- Given：全新環境，migration 已執行到含 city_stats 的 head，但尚未跑過任何 ETL、`transactions` 為空、`city_stats` 自建立後未曾手動 REFRESH。
- When：呼叫 `GET /api/prices/city`。
- Then：HTTP 200，body 為 `[]`；不得出現 500 錯誤或「materialized view has not been populated」例外。

### TC-08 ETL 執行完成後自動 refresh，city_stats 反映最新資料

- Given：`city_stats` 目前資料落後於 `transactions`（如剛新增一批 `transactions` 但尚未 REFRESH）。
- When：執行 `python -m etl.run` 且本次成功寫入至少 1 筆新資料。
- Then：
  1. CLI exit code 0。
  2. ETL 完成後（不需另外手動下 REFRESH 指令）查詢 `city_stats`，新寫入列已計入對應縣市的 `avg_price_per_sqm`／`transaction_count`。

### TC-09 ETL 本批全數重複（inserted=0）仍執行 refresh

- Given：
  1. `transactions` 已有資料，且已知某縣市在 `city_stats` 中的 `avg_price_per_sqm` 為舊值。
  2. 測試前置以 SQL 直接 `UPDATE` 一筆該縣市 `transactions.price_per_sqm` 為新值（模擬「`city_stats` 落後於 transactions 最新狀態」），但不新增/刪除任何列（不影響去重鍵）。
  3. 本次 ETL 來源 CSV 內容與現有 `transactions` 去重鍵完全相同（預期 `inserted=0`，全數判定為重複跳過）。
- When：執行 `python -m etl.run`。
- Then：
  1. CLI exit code 0。
  2. `city_stats` 中該縣市的 `avg_price_per_sqm` 已反映步驟 2 的 UPDATE 後新值（而非 REFRESH 前的舊值），驗證「即使 inserted=0 仍執行 REFRESH」（AC-11）。

### TC-10 ETL 無可匯入資料時不執行 refresh

- Given：以 mock 使下載或解析後回傳空結果，使 `run_pipeline()` 在進入寫入步驟前提前 `return`（沿用 `tests/test_etl_pipeline.py` 既有 mock 手法）。
- When：呼叫 `run_pipeline()`。
- Then：對應 `REFRESH MATERIALIZED VIEW` 的 SQL 執行（或其 mock）未被呼叫（可用 mock 的 `assert_not_called()` 驗證）。

### TC-11 API 正常回傳——基本欄位與型別

- Given：`city_stats` 中存在資料 `('台北市', 150000.00, 3)`。
- When：呼叫 `GET /api/prices/city`。
- Then：
  1. HTTP 200。
  2. body 為 JSON array。
  3. 陣列中恰有一筆 `city == "台北市"` 的物件，其 `avg_price_per_sqm == 150000.0`、`transaction_count == 3`。
  4. 每個物件恰好只有 `city`、`avg_price_per_sqm`、`transaction_count` 三個 key，無其他多餘欄位。

### TC-12 API 回傳排序——依 city 字串遞增

- Given：`city_stats` 中存在「新北市」、「台北市」、「高雄市」三筆資料。
- When：呼叫 `GET /api/prices/city`。
- Then：回傳陣列中三筆的 `city` 順序符合字串遞增排序（依 AC-18）。

### TC-13 API 回傳——avg_price_per_sqm 為 null 的縣市

- Given：`city_stats` 中「新北市」列 `avg_price_per_sqm IS NULL`、`transaction_count = 2`。
- When：呼叫 `GET /api/prices/city`。
- Then：回傳陣列中 `city == "新北市"` 的物件，其 `avg_price_per_sqm` 的 JSON 值為 `null`（非省略欄位、非 `0`、非字串 `"null"`），`transaction_count == 2`。

### TC-14 API 回傳——city_stats 完全無資料時回傳空陣列

- Given：`city_stats` 為空（無任何分組列）。
- When：呼叫 `GET /api/prices/city`。
- Then：HTTP 200，body `== []`。

### TC-15 API 忽略未定義的 query 參數

- Given：`city_stats` 有資料。
- When：分別呼叫 `GET /api/prices/city` 與 `GET /api/prices/city?foo=bar`。
- Then：兩次呼叫皆 HTTP 200，且回傳內容完全相同，不因未知 query 參數拋錯。

### TC-16 DB 連線/查詢失敗時回傳 500

- Given：以 mock 使 DB session／engine 在查詢 `city_stats` 時拋出例外（如 `SQLAlchemyError`）。
- When：呼叫 `GET /api/prices/city`。
- Then：回傳 HTTP 5xx（500），不得回傳 200 或使伺服器 process 崩潰無回應。

### TC-17 程式碼規範驗證

- Given：`api/routers/prices.py` 實作完成。
- When：依序執行：
  1. `uv run ruff check api/`
  2. `uv run ruff format --check api/`
  3. `uv run ruff check --select ANN api/`
  4. `uv run ruff check --select D api/`
  5. `grep -r "print(" api/`
- Then：
  1. 指令 1～4 皆 exit code 0，無 error 輸出。
  2. 指令 5 輸出為空（無 `print(` 呼叫）。

---

## 歷程

| 日期 | 角色 | 內容 |
|------|------|------|
| 2026-07-03 | 需求方 + Claude | 依 Notion「房地產交易地圖」規劃討論並定義本期範圍：僅縣市層級、採 city_stats Materialized View（非即時 GROUP BY）、refresh 隨 ETL pipeline 自動觸發、本期不加 Redis cache。動態 `{level}`、鄉鎮市區/村里層級、手動 refresh 端點皆拆後續 TASK。狀態：需求確認中 |
| 2026-07-03 | QA Engineer | 讀取 `shared/models.py`（Transaction 欄位型別）、`alembic/versions/001_create_transactions.py`／`002_building_type_to_text.py`（migration 慣例）、`etl/pipeline.py`（`run_pipeline()` 寫入完成點）、`api/main.py`／`api/routers/health.py`（router 掛載模式）、`tests/test_health.py`（API 測試手法）、TASK-002 卡片風格後，撰寫驗收標準 AC-01～AC-27（27 條，分 A 資料庫/B ETL 整合/C API 正常情境/D 異常邊界/E 程式碼規範五類）及測案 TC-01～TC-17（17 個，Given/When/Then）。技術判斷與理由（卡片未定案處，已於對應 AC 內註明）：①`avg_price_per_sqm` 以 `ROUND(AVG(price_per_sqm), 2)` 計算，對齊 `price_per_sqm` 來源 `Numeric(12,2)` 精度（AC-06）；②migration 以 `CREATE MATERIALIZED VIEW ... WITH DATA` 建立，避免全新環境在第一次 ETL 前呼叫 API 撞到 PostgreSQL「materialized view has not been populated」例外（AC-07，對應 TC-07/TC-14 情境）；③ETL 匯入 0 筆新資料（全數重複，inserted=0）仍執行 REFRESH，理由是 REFRESH 為冪等操作、判斷「是否真的需要 refresh」的條件邏輯本期不做，以簡單換一致性（AC-11，TC-09 驗證）；④JSON 回傳欄位一律 snake_case（`city`／`avg_price_per_sqm`／`transaction_count`），比照 `/health` 現有慣例（AC-15）；⑤回傳陣列排序依 `city` 字串遞增，卡片未指定排序方式，為使測案可穩定斷言而選擇最簡單的字典序（AC-18）；⑥`transactions.city IS NULL` 的列排除於 city_stats 分組之外（AC-03，TC-05 驗證）——此為讀 `shared/models.py` 發現 `city` 欄位可為 NULL 後額外補上的邊界情況，卡片原文未提及；⑦DB 查詢例外時比照專案目前未特別處理的慣例，回傳 FastAPI 預設 500，不做自訂錯誤格式（AC-22）。狀態更新為「開發中」。 |
| 2026-07-03 | Backend Engineer | 完成實作：①新增 `alembic/versions/003_create_city_stats_view.py`（`down_revision="002"`），以 `CREATE MATERIALIZED VIEW city_stats AS ... WHERE city IS NOT NULL GROUP BY city WITH DATA` 建立、`ROUND(AVG(price_per_sqm), 2)` 計算均價、`COUNT(*)` 計入筆數（含 NULL 單價列），另建 `ix_city_stats_city` 唯一索引供排序查詢與未來 `CONCURRENTLY` 鋪路，`downgrade()` 執行 `DROP MATERIALIZED VIEW city_stats`；②`etl/pipeline.py` 新增 `_refresh_city_stats()`，在 `load_rows` 完成後、同一 session 內執行 `REFRESH MATERIALIZED VIEW city_stats` 並 commit，失敗時 ERROR log 後重新拋出；早期 return 分支（無城市可下載／CSV 解析後無資料列）不會進入該呼叫；③新增 `api/routers/prices.py`：`GET /api/prices/city` 直接以 `text()` 查詢 `city_stats`（`ORDER BY city ASC`），以 Pydantic `CityPriceStat`（`city`／`avg_price_per_sqm`／`transaction_count`）作為 `response_model`，並在 `api/main.py` 以 `application.include_router(prices.router)` 掛載（比照 `health.router` 無 prefix、完整路徑寫在 decorator 的寫法）。驗證方式與結果：AC-01/02/03/04/05/06/07/27（migration 內容與 docstring）與 AC-08（`alembic upgrade head`／`downgrade 002:001`／`downgrade 003:002` 皆用 `--sql` offline 模式跑過，SQL 語法正確生成，含 `CREATE MATERIALIZED VIEW ... WITH DATA`、`DROP MATERIALIZED VIEW`）已驗證語法層級正確；但 TC-01～TC-09（需真的連 PostgreSQL 執行 `alembic upgrade`／`REFRESH`／查 `pg_class`／`information_schema.columns` 等）因本環境無可用 docker daemon（`docker ps` 連不到 daemon），**未實際跑 DB 驗證**，僅以 `tests/test_etl_pipeline.py` 新增之 mock 測試（`test_refresh_called_after_successful_load`、`test_refresh_called_even_when_all_rows_duplicate`、`test_refresh_failure_propagates`、`TestRefreshCityStats` 兩則）邏輯覆蓋 AC-09～AC-12；AC-13～AC-26（API 行為、程式碼規範）以 `tests/test_api_prices.py`（8 個測試，覆蓋 TC-11～TC-16、AC-14/15/16/17/18/19/20/21/22/23）全數以 mock `AsyncSession`（FastAPI `dependency_overrides`）驗證通過，此部分不需真實 DB、已完整驗證。`uv run pytest -q` 全專案 99 個測試全過；`uv run ruff check .`／`ruff format --check .` 全專案乾淨；`uv run ruff check --select ANN api/`／`--select D api/`／`grep -rn print( api/)` 皆乾淨通過（`api/routers/prices.py` 本身對 ANN、D 規則零違規）；惟 whole-project 範圍執行 `--select ANN .`／`--select D .` 時，會在既有檔案（`tests/test_etl_loader.py` 的 `**overrides: Any`、`api/main.py`／`api/routers/health.py`／各 `__init__.py`／`shared/*.py`／`alembic/env.py` 的 D413/D104 缺少空行或套件 docstring）上出現既有違規——這些屬 TASK-003 之前既有程式碼、且 `pyproject.toml` 的 `[tool.ruff.lint].select` 本未包含 `ANN`／`D`，非本次改動引入，留給 Code Review／後續 TASK 決定是否要另開單全面補上。狀態改為「Code Review」。 |
