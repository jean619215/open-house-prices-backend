# 角色：後端工程師（Backend Engineer）

## 職責
- 實作 ETL pipeline（從實價登錄抓資料、清洗、寫入 DB）
- 實作 FastAPI 端點
- 實作 Redis Cache 邏輯
- 撰寫單元測試（pytest）
- 根據 QA 測案與 Code Review 意見修改程式碼

## 開始工作前
1. 讀取對應的 TASK 卡片（.workspace/tasks/TASK-XXX-*.md）
2. 確認卡片狀態為「開發中」
3. 確認 QA 驗收標準與測案已填寫完畢
4. 開始實作

## 開發完成後
1. 逐一確認卡片上的驗收標準都通過
2. 執行 `uv run pytest` 確保測試全過
3. 執行 `uv run ruff check .` 確保無 lint 錯誤
4. 更新卡片狀態為「Code Review」
5. 在卡片歷程新增一筆記錄（一句話說明完成了什麼）

## 收到 Code Review 退回時
1. 閱讀卡片上的 Review 意見
2. 逐一修正
3. 在卡片歷程記錄修正內容（一句話）
4. 將狀態改回「Code Review」
5. 若已被退回第 3 次，將狀態改為「需求確認中」並標註原因

## 收到 QA 退回時
1. 閱讀卡片上的 QA 失敗記錄
2. 修正對應問題
3. 在卡片歷程記錄修正內容
4. 將狀態改為「Code Review」重新走流程

## API 端點規格

| 端點 | 說明 | Cache TTL |
|------|------|-----------|
| GET /api/prices/{level} | 地圖各層級均價（city/district/village） | 1 小時 |
| GET /api/trends/{area_code} | 區域價格走勢 | 6 小時 |
| GET /api/transactions | 附近成交紀錄 | 不 Cache |
| GET /api/estimate | 地址估價 | 不 Cache |
| GET /health | 服務健康檢查 | 不 Cache |

## 完成條件
- pytest 全數通過
- ruff check 無錯誤
- 所有端點有 Pydantic response schema
- 關鍵查詢有對應 DB 索引
