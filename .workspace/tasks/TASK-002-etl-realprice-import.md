# TASK-002 實價登錄 ETL — 匯入 pipeline（最小可運作版）

## 狀態
開發中

## 類型
後端（ETL）

## 需求描述
建立第一條實價登錄 ETL pipeline，把內政部實價登錄資料抓取、做最低限度的格式轉換後寫入 `transactions` 表。
本期目標是「**讓一條完整 pipeline 跑通並產出可檢視的真實資料**」，而非完整清洗與全台覆蓋。
進階處理（geocoding、捷運距離、業務過濾、自動排程）一律拆成後續 TASK。

技術決策（2026-06-16 與需求方討論確認）：
- 資料源：內政部實價登錄**官方整批下載**（不動產買賣，最近 1 期）
- 範圍：**台北市 + 新北市，最近 1 期**
- 觸發：**手動 CLI**（例如 `python -m etl.run`），不接排程
- 寫入目標：TASK-001 已建立的 `transactions` 表

---

## 本期範圍（要做）

### 抓取
- 從內政部實價登錄整批下載取得台北市、新北市最近 1 期的不動產買賣 CSV。

### 必要格式/單位轉換（為了寫進強型別欄位，務必做；但**不做業務篩除**）
| 目標欄位 | 來源 → 轉換 |
|----------|-------------|
| `transaction_date` (DATE) | 交易年月日（民國，如 `1130515`）→ 西元 DATE |
| `area_sqm` (NUMERIC) | 建物移轉總面積（平方公尺）→ **直接存平方公尺原始值，不做坪換算**；坪換算為前端責任（坪 = m² ÷ 3.305785） |
| `price_per_sqm` (NUMERIC) | 單價元/平方公尺 → **直接存元/m² 原始值，不做坪換算**；坪換算為前端責任（元/坪 = 元/m² × 3.305785） |
| `price_total` (NUMERIC) | 總價元 |
| `floor` (VARCHAR) | 移轉層次：**保留原始字串** |
| `building_age` (SMALLINT) | 由建築完成年月推算屋齡（民國換算） |
| `building_type` (TEXT) / `city` / `district` / `address` | 直接對應；building_type 已改 TEXT（無長度限制） |
| `has_parking` (BOOLEAN) | 由車位類別/車位總價推導 |

- **無法解析的值存 NULL，不丟棄整筆。**
- `location`、`mrt_distance` 本期一律寫 **NULL**（無資料來源，見後續 TASK）。

### 冪等性
- 重跑同一期不得重複寫入。需定義去重鍵（實價登錄無穩定唯一 key，採組合鍵或內容 hash，實作時提案）。

### 寫入
- 透過 `shared/database.py` 的 async session 批次寫入 PostGIS。
- 使用 logging（禁 print）、所有函式 type hint、Google 風格 docstring、ruff。

### ⚠️ 必產出物：欄位落差清單
- ETL 完成後，產出一份「**來源 CSV 欄位 vs 現有 `transactions` 表設計**」的對照與落差紀錄，
  包含：來源有但表沒有的欄位、表有但來源無法直接對應的欄位、型別/單位不一致處。
- 此清單作為後續「是否調整 `transactions` 表欄位」討論的依據（見後續 TASK）。

---

## 不在本期範圍（已記錄，之後開單處理）
| 項目 | 說明 |
|------|------|
| **geocoding（`location` 經緯度）** | 地址 → 經緯度，地圖均價核心，獨立 TASK |
| **`mrt_distance` 捷運距離計算** | 實價登錄無此資料，需另算，獨立 TASK |
| **業務過濾/清洗規則** | 車位-only、親友交易、含大幅增建等篩除；**等本期真實資料匯入後再討論**怎麼清洗 |
| **表單欄位調整** | 依「欄位落差清單」討論是否新增/修改 `transactions` 欄位 |
| **Celery beat 自動排程** | 每旬（1/11/21 公告）自動抓取，獨立 TASK |
| **全台 22 縣市 / 歷史回補** | 本期僅台北+新北最近 1 期 |

## 後續 Schema / 效能優化待辦（決策 3，2026-06-22 記錄）

> 現行去重實作：逐列 SELECT 查重，效能足夠用於本期小規模匯入，**維持現狀，不改程式**。
> 以下待辦在擴大規模時必須處理，請屆時另開 TASK。

- **DB unique index + ON CONFLICT DO NOTHING**：
  為去重鍵 `(address, transaction_date, floor, area_sqm, price_total)` 建立 DB unique index，
  並將 loader 改用 `INSERT ... ON CONFLICT DO NOTHING`，消除 N+1 SELECT 效能瓶頸。
  **觸發時機**：要做全台匯入、歷史回補、或排程自動跑時必須處理。

---

## 驗收標準

> 每條標準皆可獨立判定「通過」或「失敗」。  
> 通過：符合描述行為。失敗：不符合，或有額外非預期行為。

### A. CLI 觸發與下載

- [ ] AC-01：執行 `python -m etl.run`（或等效入口）不需任何互動，指令在無使用者輸入的情況下自行完成並退出（exit code 0）。
- [ ] AC-02：程式下載台北市（A 縣市代碼）與新北市（F 縣市代碼）的不動產買賣最近 1 期 CSV；其他縣市資料不被下載或寫入。
- [ ] AC-03：若無法連線至內政部下載端點（模擬 network error 或 HTTP 4xx/5xx），程式以非 0 exit code 結束，並以 logging（非 print）輸出明確錯誤訊息；`transactions` 表不新增任何資料。
- [ ] AC-04：若下載後的 CSV 為空檔案（0 bytes 或僅含 header 無資料列），程式正常結束（exit code 0），logging 輸出警告，`transactions` 表不新增任何資料。

### B. 欄位轉換——正常路徑

- [ ] AC-05：`transaction_date` 欄位型別為 PostgreSQL DATE，民國年日期字串 `1130515` 轉換後儲存為 `2024-05-15`；民國 `1120101` 儲存為 `2023-01-01`。
- [ ] AC-06：`area_sqm` 的值 = 來源「建物移轉總面積（平方公尺）」原始值，直接儲存，精度誤差不超過 ±0.01 m²。**不做坪換算**；坪換算為前端責任（坪 = m² ÷ 3.305785）。
- [ ] AC-07：`price_per_sqm` 的值 = 來源「單價元/平方公尺」原始值，直接儲存，精度誤差不超過 ±0.01 元。**不做坪換算**；坪換算為前端責任（元/坪 = 元/m² × 3.305785）。（決策 1，2026-06-22：面積、單價皆存來源平方公尺原始值，不做坪換算；坪換算為前端責任）
- [ ] AC-08：`floor` 欄位為 VARCHAR，儲存原始字串（如 `「三層」`、`「全」`、`「地下一層」`），不做任何額外轉換。
- [ ] AC-09：`building_age` 為 SMALLINT，計算方式為：西元匯入年（執行當年）-（建築完成年月民國年 + 1911），**只取整數年、無條件捨去到年（不計月份）**；結果為負數時存 NULL。此為刻意設計：以「建築完成年」而非精確月份計算，避免跨月邊界造成測案不穩定。
- [ ] AC-10：`has_parking` 為三態 BOOLEAN：有車位（來源「車位類別」非空白且非 `「無」`，或「車位總價」> 0）→ `TRUE`；明確無車位（「車位類別」= `「無」` 且「車位總價」= 0 或為空）→ `FALSE`；來源欄位缺失或無法判斷 → `NULL`（見 AC-18）。
- [ ] AC-11：`city`、`district`、`address`、`building_type`、`price_total` 欄位直接對應來源，型別相符。
- [ ] AC-12：`location` 欄位對所有匯入列均為 NULL（不論來源是否有地址）。
- [ ] AC-13：`mrt_distance` 欄位對所有匯入列均為 NULL。

### C. 欄位轉換——異常/缺值路徑

- [ ] AC-14：來源「交易年月日」欄位為空字串、格式非 7 位數字、或值為 `0000000`（7 碼但代表日期不詳）時，`transaction_date` 存 NULL，整筆其他欄位仍正常寫入，程式不中止。`0000000` 不得被解析為任何有效日期。
- [ ] AC-15：來源「建物移轉總面積」欄位為空字串或非數值時，`area_sqm` 存 NULL，整筆仍正常寫入。
- [ ] AC-16：來源「單價元/平方公尺」欄位為空字串或非數值時，`price_per_sqm` 存 NULL，整筆仍正常寫入。
- [ ] AC-17：來源「建築完成年月」欄位為空字串或格式無法解析時，`building_age` 存 NULL，整筆仍正常寫入。
- [ ] AC-18：來源「車位類別」與「車位總價」欄位皆缺失或無法判斷時，`has_parking` 存 NULL（不得存 FALSE 或 TRUE），整筆仍正常寫入。（三態邏輯與 AC-10 一致：有車位=TRUE、明確無車位=FALSE、欄位缺失/無法判斷=NULL）

### D. 冪等性

- [ ] AC-19：對同一期資料連續執行兩次 CLI，第二次執行後 `transactions` 表中同一批資料的筆數與第一次相同（無重複列）。
- [ ] AC-20：第二次執行以 logging 輸出「已存在，跳過」或等效訊息（或靜默跳過），不拋出 exception、不中止程式，exit code 為 0。

### E. 寫入規範

- [ ] AC-21：所有寫入透過 `shared/database.py` 的 async session 完成（不得使用 psycopg2 直接連線或 synchronous SQLAlchemy session）。
- [ ] AC-22：程式全程使用 Python logging 模組，不出現任何 `print(` 呼叫。
- [ ] AC-23：所有公開函式均有 type hint 與 Google 風格 docstring。
- [ ] AC-24：`ruff check etl/` 與 `ruff format --check etl/` 皆通過，無 error。

### F. 必產出物：欄位落差清單

- [ ] AC-25：ETL 完成後，專案中存在一份欄位落差清單（格式：Markdown 表格或純文字），明確列出以下三類項目：
  1. 來源 CSV 有、但 `transactions` 表沒有對應欄位的欄位名稱。
  2. `transactions` 表有、但來源 CSV 無法直接對應的欄位名稱（含 `location`、`mrt_distance`）。
  3. 型別或單位不一致處（如：民國/西元、平方公尺/坪）。
- [ ] AC-26：落差清單檔案路徑已在 PR 描述或 TASK 卡片中明確標示，QA 可直接開啟驗閱。

---

## 測案

### TC-01 正常匯入——台北市 + 新北市資料寫入 transactions 表

- Given：`transactions` 表為空；網路可連線至內政部下載端點；台北市與新北市最近 1 期不動產買賣 CSV 可正常下載。
- When：執行 `python -m etl.run`。
- Then：
  1. 指令以 exit code 0 結束。
  2. `SELECT COUNT(*) FROM transactions WHERE city IN ('台北市','新北市')` 回傳 > 0。
  3. `SELECT COUNT(*) FROM transactions WHERE city NOT IN ('台北市','新北市')` 回傳 0。
  4. logging 輸出包含「匯入完成」或等效字串，無 CRITICAL/ERROR 層級訊息。

### TC-02 交易日期轉換——民國年 → 西元 DATE

- Given：來源 CSV 包含交易年月日欄位值 `1130515`。
- When：ETL 完成後，查詢對應列。
- Then：
  1. `transaction_date` 值為 `2024-05-15`（PostgreSQL DATE）。
  2. 來源值 `1120101` 對應 `transaction_date = 2023-01-01`。

### TC-03 面積與單價單位——平方公尺原始值直接儲存（決策 1，2026-06-22）

- Given：來源 CSV 某一列的「建物移轉總面積」= `66.10`（平方公尺）、「單價元/平方公尺」= `290000`。
- When：ETL 完成後，查詢對應列。
- Then（已依決策 1 訂正）：
  1. `area_sqm` = `66.10`（±0.01 m²；來源值直接儲存，不做坪換算）。
     坪換算為前端責任：66.10 ÷ 3.305785 ≈ 19.995 坪（僅供參考，不驗此值）。
  2. `price_per_sqm` = `290000.00`（±0.01 元；來源值直接儲存，不做坪換算）。
     坪換算為前端責任：290000 × 3.305785 ≈ 958678 元/坪（僅供參考，不驗此值）。

### TC-04 floor 原始字串保留

- Given：來源 CSV 某一列「移轉層次」= `「三層」`。
- When：ETL 完成後，查詢對應列。
- Then：`floor` = `「三層」`，字元與來源完全一致（不做數字轉換）。

### TC-05 building_age 計算

- Given：來源 CSV 某一列「建築完成年月」= `0920630`（民國 92 年 6 月 30 日，對應西元建築完成年 2003）。
- When：ETL 完成後（在執行當年 CURRENT_YEAR 執行），查詢對應列。
- Then：`building_age = CURRENT_YEAR - 2003`（SMALLINT；只取整數年，無條件捨去到年，不計月份）。
  - 驗證方式：`SELECT building_age FROM transactions WHERE ... ; SELECT EXTRACT(YEAR FROM NOW())::INT - 2003 AS expected;` 兩值相等。
  - 注意：斷言不可寫死數字 `23`；應以「執行當年 − 2003」動態計算期望值後比對。

### TC-06 has_parking 推導——有車位

- Given：來源 CSV 某一列「車位類別」= `「坡道平面」`、「車位總價」= `1500000`。
- When：ETL 完成後，查詢對應列。
- Then：`has_parking = TRUE`。

### TC-07 has_parking 推導——無車位

- Given：來源 CSV 某一列「車位類別」= `「無」`、「車位總價」= `0`。
- When：ETL 完成後，查詢對應列。
- Then：`has_parking = FALSE`。

### TC-08 location 與 mrt_distance 為 NULL

- Given：ETL 正常執行完成，`transactions` 表已有資料。
- When：執行 `SELECT COUNT(*) FROM transactions WHERE location IS NOT NULL OR mrt_distance IS NOT NULL`。
- Then：回傳 `0`（所有列的 location 與 mrt_distance 均為 NULL）。

### TC-09 缺值欄位存 NULL——交易日期格式異常

- Given：測試用 CSV 包含三列：
  - 列 A：「交易年月日」= `""`（空字串），其他欄位格式正常。
  - 列 B：「交易年月日」= `"0000000"`（7 碼但代表日期不詳），其他欄位格式正常。
  - 列 C：「交易年月日」= `"1130515"`（正常值），其他欄位格式正常。
- When：執行 ETL。
- Then：
  1. ETL 正常完成（exit code 0），不拋出 exception。
  2. 列 A 的 `transaction_date = NULL`，其他欄位（如 `city`、`price_total`）有值。
  3. 列 B 的 `transaction_date = NULL`（`0000000` 不得被解析為任何有效日期）。
  4. 列 C 的 `transaction_date = 2024-05-15`（正常轉換）。
  5. 三列均正常寫入，程式不中止。

### TC-10 缺值欄位存 NULL——面積/單價非數值

- Given：測試用 CSV 中某一列「建物移轉總面積」= `「--」`（非數值），「單價元/平方公尺」= `「」`（空字串），其他欄位正常。
- When：執行 ETL。
- Then：
  1. `area_sqm = NULL`，`price_per_sqm = NULL`。
  2. 整筆其他欄位正常寫入。
  3. ETL 不中止。

### TC-11 缺值欄位存 NULL——建築完成年月無法解析

- Given：測試用 CSV 中某一列「建築完成年月」= `「不詳」`。
- When：執行 ETL。
- Then：`building_age = NULL`，整筆正常寫入。

### TC-12 缺值欄位存 NULL——車位欄位缺失

- Given：測試用 CSV 中某一列「車位類別」與「車位總價」皆為空字串或欄位不存在。
- When：執行 ETL。
- Then：`has_parking = NULL`（不得為 FALSE），整筆正常寫入。

### TC-13 無法下載（網路失敗）

- Given：模擬內政部下載端點不可達（如：修改 URL 為無效位址，或以 mock 讓 HTTP request 回傳 ConnectionError）。
- When：執行 `python -m etl.run`。
- Then：
  1. 程式以非 0 exit code 結束。
  2. logging 輸出 ERROR 層級訊息，內含下載失敗原因。
  3. `transactions` 表無新增資料。

### TC-14 空 CSV（無資料列）

- Given：下載回來的 CSV 僅含 header 列，無任何資料列（或為 0 bytes）。
- When：執行 ETL。
- Then：
  1. 程式以 exit code 0 結束。
  2. logging 輸出 WARNING 層級訊息（如「無可匯入資料」）。
  3. `transactions` 表無新增資料。

### TC-15 冪等性——重跑同一期不重複寫入

去重鍵定義：`(address, transaction_date, floor, area_sqm, price_total)`。同地址但 transaction_date 不同視為不同筆、不算重複。

注意：`area_sqm` 欄位自 2026-06-22 決策 1 起儲存平方公尺原始值（非坪），去重鍵中的 area_sqm 值亦為平方公尺。

- Given：
  1. `transactions` 表中已存在一筆記錄，其 `(address, transaction_date, floor, area_sqm, price_total)` = `('台北市信義區松仁路100號', '2024-05-15', '三層', 66.10, 6000000)`（area_sqm 為 m² 原始值），筆數為 N（N > 0）。
  2. 來源 CSV 包含與上述記錄去重鍵完全相同的一列，以及另一列去重鍵不同的新資料（用以確認新資料仍可寫入）。
- When：對同一期資料再次執行 `python -m etl.run`。
- Then：
  1. 程式以 exit code 0 結束，無 exception 拋出。
  2. `SELECT COUNT(*) FROM transactions WHERE city IN ('台北市','新北市')` 回傳 N + 1（重複筆不增加、新筆正常寫入）。
  3. 去重鍵相同的列在表中仍只有一筆。
  4. logging 輸出「已存在，跳過」或等效訊息（對重複列），無 ERROR 層級訊息。

### TC-16 程式碼規範驗證

- Given：ETL 實作完成，`etl/` 目錄下有對應 Python 檔案。
- When：依序執行以下指令：
  1. `uv run ruff check etl/`
  2. `uv run ruff format --check etl/`
  3. `uv run ruff check --select ANN etl/`（type hint 缺漏檢查）
  4. `uv run ruff check --select D etl/`（Google 風格 docstring 檢查，需 ruff 設定啟用 pydocstyle）
  5. `grep -r "print(" etl/`
- Then：
  1. 指令 1 exit code 0，無 error 輸出。
  2. 指令 2 exit code 0，無 error 輸出（格式已符合）。
  3. 指令 3 exit code 0，無 ANN 系列 error（所有公開函式參數與回傳值均有 type hint）。
  4. 指令 4 exit code 0，無 D 系列 error（所有公開函式均有 Google 風格 docstring）。
  5. 指令 5 輸出為空（無 `print(` 呼叫）。

### TC-17 欄位落差清單存在且內容完整

- Given：ETL 實作完成，PR 已提交。
- When：依照 PR 描述或 TASK 卡片指示的路徑開啟欄位落差清單檔案。
- Then：
  1. 檔案存在且可開啟。
  2. 包含「來源有、表沒有」的欄位清單（至少列出欄位名稱）。
  3. 包含「表有、來源無法對應」的欄位清單（至少包含 `location`、`mrt_distance`）。
  4. 包含型別/單位不一致說明（至少涵蓋民國/西元、平方公尺/坪兩項）。

---

## 歷程

| 日期 | 角色 | 內容 |
|------|------|------|
| 2026-06-16 | 需求方 + Claude | 討論並定義本期範圍：台北+新北最近 1 期、手動 CLI、location/mrt_distance 留 NULL、不做業務過濾只做必要格式轉換、需產出欄位落差清單。geocoding/捷運距離/清洗規則/排程/表單調整皆拆後續 TASK。狀態：需求確認中 |
| 2026-06-16 | QA Engineer | 需求確認完成，依背景說明定案內容撰寫驗收標準 AC-01～AC-26（26 條）及測案 TC-01～TC-17（17 個），涵蓋正常路徑、欄位轉換、異常/缺值、冪等性、程式碼規範、欄位落差清單。狀態更新為「開發中」。 |
| 2026-06-16 | Senior Reviewer | 測案審查（Code Review 前置）發現多項 Blocker，**退回「需求確認中」，需 QA 修正後才可進入開發**。必改項如下：（1）TC-03 面積期望值 `19.997` 應為 `≈19.995`（66.10÷3.305785=19.9953，現值誤差 0.0017 超出自訂 ±0.01 容差）；（2）TC-03 單價期望值 `958780` 應為 `≈958678`（290000×3.305785=958677.65，現值差 102 元遠超 ±1 元容差，正確實作會被誤判 FAIL）；（3）AC-07 公式 `÷3.305785×3.305785` 數學等於原值（無轉換效果），應改為「單價元/平方公尺 × 3.305785 = 元/坪」；（4）AC-10 寫「否則 FALSE」與 AC-18 寫「欄位缺失存 NULL」邏輯矛盾，需明確三態定義（有車位=TRUE／明確無車位=FALSE／欄位缺失=NULL）；（5）TC-15 去重鍵未定義，測案無法在實作前確認期望行為；（6）TC-05 建築完成年月期望值 `23` 硬編碼 2026 年，跨年後測案自動失效，應改為「執行當年 - 2003」的動態描述。其餘 Major/Minor 問題見審查報告。 |
| 2026-06-17 | QA Engineer | 依 Senior Reviewer 退回清單修正 9 項（Blocker 5、Major 3、Nit 1）：①TC-03 面積期望值更正為 19.995（66.10÷3.305785=19.9953）；②TC-03 單價期望值更正為 958678（290000×3.305785=958677.65）；③AC-07 公式修正為「元/平方公尺 × 3.305785 = 元/坪」，移除無效的 ÷3.305785；④AC-10 改為三態定義（TRUE/FALSE/NULL）、AC-18 補充三態說明，兩者邏輯統一；⑤TC-15 補上去重鍵定義（address, transaction_date, floor, area_sqm, price_total）及明確 Given/When/Then，含「新筆仍可寫入」的反向驗證；⑥TC-05 改為動態描述「執行當年 − 2003」，禁止寫死數字；⑦AC-09 明確標註「只取整數年、無條件捨去到年，不計月份」為刻意設計；⑧AC-14 補上 `0000000` 轉 NULL 規則、TC-09 新增列 B（`0000000`）邊界驗證；⑨TC-16 以可執行指令（uv run ruff check/format、ruff --select ANN、ruff --select D、grep）取代「手動確認」字眼。狀態更新為「開發中」。 |
| 2026-06-22 | Backend Engineer | 實作 ETL pipeline（etl/ 下新增 5 個模組）：constants.py 定義常數、transform.py 實作 6 個欄位轉換函式（民國年、面積坪換算、單價坪換算、屋齡、三態車位）、parser.py 解析 CSV、downloader.py 下載解壓 MOI zip、loader.py 冪等寫入（去重鍵 address+transaction_date+floor+area_sqm+price_total）、pipeline.py 串接流程、run.py CLI 入口（python -m etl.run）。新增 tests/test_etl_transform.py、test_etl_parser.py、test_etl_loader.py、test_etl_pipeline.py 共 69 個單元測試。全測試 73 passed，ruff check/format 全綠。欄位落差清單：etl/field_gap_report.md（詳列來源有表無/表有來源無/型別單位不一致，含 4 項潛在議題：area_sqm/price_per_sqm 命名誤導、building_type VARCHAR(20) 截斷風險、冪等鍵效能、來源無穩定 unique key）。狀態更新為「Code Review」。 |
| 2026-06-22 | Backend Engineer | 依需求方 4 項決策修改（決策 1 為需求變更，移除坪換算改存平方公尺、parse_area_ping→parse_area_sqm、parse_price_per_sqm_to_ping→parse_price_per_sqm、移除 SQM_PER_PING 常數、AC-06/AC-07/TC-03/TC-15 同步訂正為平方公尺版本、tests 斷言更新；決策 2：building_type→Text + migration 002_building_type_to_text；決策 3：去重效能記為後續待辦 TASK，不改程式；決策 4：httpx 升正式 [project] dependencies）。因 AC/TC 有變動，狀態從「Code Review」改回「開發中」，需重新走 QA 複驗。 |
