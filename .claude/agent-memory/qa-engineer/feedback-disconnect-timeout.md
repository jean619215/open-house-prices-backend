---
name: feedback-disconnect-timeout
description: 斷線情境（DB/Redis 中斷）QA 驗收的三個關鍵判準：HTTP 狀態、JSON 欄位、回應時間
metadata:
  type: feedback
---

/health 斷線情境（TC-04 DB 斷線、TC-05 Redis 斷線）有三個必須同時驗證的判準，缺一不可：

1. **HTTP 狀態碼**：必須是 503（不是 200、也不是 500）
2. **JSON 欄位**：
   - `status` 必須是 `"error"`（不是 `"ok"`）
   - 斷線的服務欄位必須是 `"disconnected"`
   - 正常的服務欄位必須仍是 `"connected"`（確認部分降級而非全掛）
3. **回應時間**：必須在 3 秒內（B3 規格），用 `curl -w "%{time_total}"` 量測

**驗證指令範本：**
```bash
time curl -s -w "\nHTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}" http://localhost:8000/health
```

**Why:** 斷線情境最容易忽略「回應時間」驗證。若 timeout 設定錯誤，API 可能掛住超過 3 秒才回 503，用戶端體感為服務無回應。此情境在 code review 階段也常未手動驗證，屬於高風險盲點。

**How to apply:** 每次有 /health 變動的 TASK，TC-04/TC-05 務必手動執行（不能只靠 AsyncMock unit test 覆蓋），並記錄實際 time_total 數值。

See also: [[project-overview]]
