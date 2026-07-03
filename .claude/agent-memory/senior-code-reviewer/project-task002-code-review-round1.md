---
name: project-task002-code-review-round1
description: TASK-002 ETL 第 1 次程式碼 Code Review（commit bb9a11c）發現的 Major 問題：models.py docstring 殘留決策1前敘述、building_age「0000000」sentinel 未排除、downloader.py 缺測試與批次無單列例外隔離
metadata:
  type: project
---

TASK-002（實價登錄 ETL 匯入 pipeline）2026-07-03 進行第一次「程式碼」Code Review（先前 2026-06-16 的退回是測案審查，非程式碼審查，見 [[project-task002-testcase-review]]）。結論：⚠️ 需修改後通過，退回「開發中」（Code Review 第 1 次退回，未達 3 次門檻）。

**核心邏輯全部正確**：民國年轉換、area_sqm/price_per_sqm 直接存 m²/元-m² 原始值（決策 1 對齊良好，transform.py 本身沒有殘留坪換算邏輯）、floor 原始字串保留、building_age 無條件捨去、has_parking 三態、冪等鍵 ORM 參數化查詢（無 SQL injection）、無 zip slip（`_extract_csv_from_zip` 只 `zf.read()` 到記憶體，不會用 entry name 寫檔案）。

**發現的 Major 問題（可重複出現的模式，供未來審查參考）：**

1. **決策變更後，跨檔案 docstring/comment 未同步更新**：`shared/models.py` 的 `Transaction` model docstring 仍寫著 `price_per_sqm`/`area_sqm` 是 "in ping (坪)"、`transaction_date` 是 "stored as the 1st of that month"，這是決策 1（改存 m² 原始值）之前的舊敘述，developer 只改了 `etl/transform.py`、`etl/constants.py` 和 tests，忘記同步 `shared/models.py`。
   **教訓**：需求變更（尤其是單位/型別語意變更）發生後，審查時要 grep 整個 repo 找舊關鍵字（如「坪」、"ping"、月份相關敘述），不能只看卡片指定的檔案範圍（models.py 不在這次「請審查的檔案」清單內，但問題確實在那裡）。

2. **同一模組內，相同 sentinel 值的處理不一致**：`etl/constants.py` 定義了 `UNKNOWN_DATE_VALUE = "0000000"` 且 `parse_transaction_date` 有特殊處理讓它回傳 `None`，但 `parse_building_age`（同樣是 7 碼民國年月字串輸入）沒有套用同樣的邏輯 — `parse_building_age("0000000", 2026)` 會算出 `completion_year=1911`、`building_age≈115` 的假資料，而不是 NULL。
   **教訓**：ETL 專案中，同一個 sentinel value（如 MOI 資料常見的「0000000 代表日期不詳」）如果在多個欄位/函式都可能出現，要檢查是否每個相關函式都有一致處理，不能只在第一個函式加規則就假設其他函式也涵蓋到。日後看到「民國年月」相關的 parse 函式，記得測試 `"0000000"` 輸入。

3. **downloader.py（涉及外部下載、zip 解壓、HTTP 錯誤 — 也是安全性審查重點）完全沒有專屬單元測試**：`test_etl_downloader.py` 不存在，`_extract_csv_from_zip` / `_build_download_url` 等函式只在 `test_etl_pipeline.py` 被 mock 掉（`patch("etl.pipeline.download_all_target_cities", ...)`），實際下載/解壓邏輯本身從未被直接測試。
   **教訓**：審查涉及外部 I/O 或安全性敏感邏輯（下載、解壓、檔案路徑）的模組時，要主動確認「有沒有直接測試這個模組」而不是「有沒有測試呼叫這個模組的上層」——mock 掉整個模組等於完全沒測到內部邏輯。

4. **批次寫入無單列例外隔離**：`bulk_insert_rows`/`load_rows` 對整批 rows 只在最後 commit 一次，且沒有 try/except 保護單一列。若任何一列因欄位過長或型別不符導致 DB 例外（例如 `floor` 欄位是 `VARCHAR(10)`，但實價登錄「移轉層次」在多筆棟合併交易時常見逗號/頓號分隔多層字串，容易超過 10 字元），會讓兩縣市當次解析出的「所有」資料一起失敗、無法寫入，而不是跳過壞列繼續。`etl/field_gap_report.md` 有提到「應在 ETL 監控截斷警告」但程式碼未實作。
   **教訓**：MVP 階段接受「N+1 SELECT 查重」效能debt（決策 3 已明文記錄）是合理的，但「整批無隔離、一列壞資料拖垮全部」是不同性質的風險（正確性/可用性，不是效能），審查時要分開看待，不能因為卡片說「維持現狀不改程式」就連這個一起放過。

**次要（Minor）發現**：
- `pyproject.toml` 的 `[tool.ruff.lint] select` 未含 `ANN`/`D`，所以 AC-24 要求的一般 `ruff check etl/` 實際上不會抓型別標註/docstring 缺漏，必須靠 TC-16 中額外的 `--select ANN`/`--select D` 指令才會抓到。這是可運作但脆弱的設定，建議之後納入預設 select。
- zip 解壓沒有大小上限（zip bomb）、沒有非 UTF-8 編碼 fallback（寫死 `utf-8-sig`）。官方資料源風險低，MVP 可接受。

相關記憶：[[project-task002-testcase-review]]、[[project-task001-review]]
