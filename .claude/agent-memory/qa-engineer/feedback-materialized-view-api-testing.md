---
name: feedback-materialized-view-api-testing
description: Materialized View 支撐的地圖均價 API（/api/prices/{level} 系列）撰寫 AC/TC 時必須涵蓋的技術陷阱
metadata:
  type: feedback
---

TASK-003（`GET /api/prices/city`，第一個對外均價端點）撰寫 AC/TC 時發現的、未來所有 `/api/prices/*`（city／district／village）與其他依賴 Materialized View 聚合的端點都會重複遇到的技術陷阱：

**1. Materialized View 建立時的 `WITH DATA` vs `WITH NO DATA` 是會不會 500 的關鍵分水嶺**
PostgreSQL 對 `CREATE MATERIALIZED VIEW ... WITH NO DATA` 建立、且從未 `REFRESH` 過的 view 執行 `SELECT` 會直接拋出 `materialized view "xxx" has not been populated` 例外。若 migration 用 `WITH NO DATA`，全新環境跑完 migration、ETL 還沒執行過第一次時，API 會 500 而非回傳空陣列。
- **How to apply**：任何「migration 建立 Materialized View」的 AC，都要明確指定 `WITH DATA`，並補一條 TC：「全新環境、migration 剛跑完、尚未執行過任何 ETL/REFRESH 時呼叫 API」，預期 HTTP 200 + 空陣列，而非 500。這條測案容易被忽略，因為開發與 QA 手上的測試環境通常早就 refresh 過，不會自然踩到這個情境。

**2. GROUP BY 分組鍵若可為 NULL，必須明確要求排除**
凡是「依某欄位分組產生聚合列」的 View（如依 city、依 district 分組），先去讀該欄位在 ORM model／migration 的 nullable 設定。若可為 NULL，要明確補 AC：「該欄位為 NULL 的來源列不得產生分組列」，並補 TC 用一筆 `city IS NULL` 的資料驗證 `city_stats` 沒有 `city = NULL` 的列。不要假設「反正地圖不會顯示 NULL 縣市」就略過，這是實作時容易漏掉 `WHERE city IS NOT NULL` 的地方。

**3. 聚合欄位「部分來源為 NULL」要與「分母排除、分子不排除」的規則對齊到兩個獨立欄位**
本專案的均價類 View 都有「price_per_sqm 為 NULL 不計入均價分母，但仍計入 transaction_count」的規則（縣市/鄉鎮/村里皆同）。這代表 AC 要分別驗證兩個欄位：
- 均價欄位排除 NULL（`AVG` 天然排除 NULL，不需額外 `WHERE`，但要驗證）。
- 筆數欄位不排除 NULL（用 `COUNT(*)` 而非 `COUNT(price_per_sqm)`，否則會漏算)。
兩者最容易搞混的實作錯誤是誤用 `COUNT(price_per_sqm)` 當作 transaction_count，導致「有成交但無單價」的列被漏算成交筆數。務必補一條「全部列的均價欄位皆 NULL」的邊界 TC（驗證 avg 欄位為 NULL、count 欄位仍 > 0），這是最容易抓到上述實作錯誤的測案。

**4. 均價欄位的四捨五入精度沒有卡片明訂時，要對齊來源欄位的 Numeric 精度，並在 AC 寫明依據**
`price_per_sqm` 若是 `Numeric(12, 2)`，聚合後的 `avg_xxx` 也該 `ROUND(..., 2)`，否則 `AVG()` 會回傳遠超過來源精度的小數位數（對前端沒有意義且會讓測案斷言值一直對不上）。這類「卡片未定案的技術細節」，QA 可以自己做出判斷但必須在 AC 內寫「理由」與「依據哪個既有欄位精度」，不要含糊帶過或跳過不寫。

**5. ETL 觸發的 REFRESH 時機要覆蓋「進入寫入步驟但 inserted=0」與「根本沒進入寫入步驟」兩種不同的 0 筆情境**
這兩種「本次沒有新資料」的情況技術上不同，AC/TC 要分開處理：
- 情境 A：下載/解析後結果是空的，pipeline 提前 `return`（連 `load_rows` 都沒呼叫）→ 不應該 REFRESH。
- 情境 B：有進入 `load_rows`，但全部資料因去重判定為重複、`inserted == 0` → 是否要 REFRESH 得由 QA 判斷並記錄理由（本專案選擇「仍要 REFRESH，因為冪等操作代價低、簡化邏輯」），並補 TC 用「先用 SQL 手動改一筆現有列的值製造 view 與 table 不一致，再跑一次全部重複的 ETL，驗證 REFRESH 後 view 值有跟上」的方式驗證，而不能只驗「exit code 0」這種弱斷言。

**6. 回傳陣列排序若卡片未指定，AC 要明訂一個排序規則，否則測案斷言會不穩定**
多列回傳的地圖均價 API 若沒有明確排序（如依 city 遞增），不同次呼叫在 SQL 執行層面理論上順序不保證一致，會讓「驗證回傳內容」的 TC 難以穩定斷言。QA 應主動選一個簡單、可驗證的排序（字典序即可），寫入 AC 並說明「卡片未指定、為使測案可穩定斷言而選擇」，不要留白讓開發自由發揮。

Related: [[project-overview]], [[feedback-etl-boundary-conditions]], [[feedback-no-live-db-verification]]
