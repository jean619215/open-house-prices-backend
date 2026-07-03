---
name: feedback-no-live-db-verification
description: 當環境沒有可用的實際 PostgreSQL 時，如何驗收 DB 依賴的 AC/TC 並在卡片上記錄清楚
metadata:
  type: feedback
---

TASK-002 QA 測試階段發現：這個環境不一定有可用的 docker daemon（`docker ps` 直接因
`dial unix /var/run/docker.sock: connect: no such file or directory` 失敗，不是「容器沒啟動」
而是 daemon 根本不存在），且專案只有 `.env.example`、沒有 `.env`。這與 [[feedback-disconnect-timeout]]
描述的「容器有跑但被手動斷線」情境不同，是更早一層的「整個 DB 基礎設施在此次執行環境中不存在」。

**判斷步驟（下次先做，別預設有 DB）：**
1. `docker ps` — 若因 daemon 不存在而報錯（非「no containers」），確定沒有容器可用。
2. `pg_isready -h localhost -p <docker-compose.yml 裡定義的 host port>` — 確認真的連不上。
3. `ls -la .env*` — 若只有 `.env.example` 沒有 `.env`，代表沒人設定過本機連線。

三者皆確認後，才能判定「無可用實際 DB」，不能只憑其中一項就下結論。

**替代驗收方式：**
- 有 DB 依賴的 AC/TC（查詢 `transactions` 表筆數、欄位值等），改用專案既有 `tests/test_etl_*.py`
  （用 `AsyncMock` 模擬 `AsyncSession`、`httpx.MockTransport` 模擬下載）逐條比對是否覆蓋對應行為。
  **不能只看測試命名或 PASS 就採信**——要逐一打開對應原始碼（transform/parser/loader/pipeline 等）
  確認測試斷言與程式邏輯、與卡片上的 AC 描述三者一致，才算完成驗證。
- 不依賴 DB、可獨立重現的驗收項（程式碼規範指令、產出文件內容）**必須真的執行/開啟**，
  不能也用「有測試覆蓋」帶過——這類項目正是「客觀可重現」判準最容易落地的地方，跳過會削弱整體驗收的可信度。
- 在卡片歷程記錄時，必須明確寫出「這條是靠實跑驗證，還是靠現有測試覆蓋驗證」，讓後續讀卡片的人知道
  驗證的實際強度，不要混著寫成同一種語氣。

**易誤判的小細節：**
- `grep -r "print(" etl/` 找不到符合字串時，**exit code 是 1、標準輸出為空**——這是「通過」訊號
  （AC 要求「輸出為空」），不要看到 exit code 非 0 就誤判為指令失敗。
- `uv run ruff check --select D etl/` 可能印出 D203/D211、D212/D213 規則互斥的 warning，這是 ruff
  設定層級的訊息，不算 lint error；只要沒有實際的 D-系列 violation、整體訊息是 `All checks passed!`
  就算通過。

**Why:** 若不先確認「daemon 不存在」vs「容器只是沒啟動」的差異，容易誤以為只是要 `docker compose up`
就能驗收，浪費時間嘗試啟動一個根本不存在的 daemon；若不區分「實跑驗證」與「測試覆蓋驗證」，卡片歷程
會讓後續開發/審查誤以為所有項目都是同等強度的驗證。

**How to apply:** 任何一張卡片進入 QA 測試階段，先花一分鐘做上述三步判斷，再決定驗收策略；記錄時逐條
標明驗證方式（實跑 or 測試覆蓋），可獨立驗證的項目（規範檢查指令、產出文件）一律實跑，絕不用測試代替。

See also: [[project-overview]], [[feedback-etl-boundary-conditions]], [[feedback-disconnect-timeout]]
