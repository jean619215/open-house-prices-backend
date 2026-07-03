---
name: feedback-lint-tc-scope-mismatch
description: 撰寫程式碼規範類 TC 時，ruff --select ANN/D 的檢查目標必須與對應 AC 的檔案範圍完全一致，否則 TC 會對既有無關檔案的違規誤判失敗
metadata:
  type: feedback
---

TASK-003 QA測試階段發現：TC-17 第 3/4 步驟寫成 `uv run ruff check --select ANN api/`／`--select D api/`（對整個 `api/` 目錄執行），但對應的 AC-24／AC-26 明確限定範圍是「本次新增的 `api/routers/prices.py`」。專案既有檔案（`api/main.py`、`api/routers/health.py`、`api/__init__.py`、`api/routers/__init__.py`）本身就有既有 D413/D104 違規（`pyproject.toml` 未把 `ANN`／`D` 納入預設 `[tool.ruff.lint].select`，這些檔案從未被此規則檢查過），一旦 TC 把 `--select D` 的目標寫成整個目錄，指令必定 exit 1，即使本次新增/修改的程式碼完全乾淨。

這與 TASK-002 就已經記錄的「`grep -r print( etl/) exit 1 代表沒找到=通過」不是同一類問題——這次是 TC 本身的**檢查範圍（scope）**寫錯，不是誤判 exit code 的意義。

**判斷方式：**
1. 先看清楚該 TC 對應的 AC 實際限定範圍是「整個目錄」還是「特定檔案」。AC-24/26 這類「程式碼規範」條款，若措辭是「`api/routers/prices.py` 所有公開函式...」，範圍就是那一個檔案，不是整個套件。
2. 若 TC 把檢查指令寫成比 AC 更大的範圍（如整個 `api/`），先用 `--select ANN,D <確切檔案路徑>` 針對 AC 實際範圍單獨重跑一次，確認新增/修改的程式碼本身乾淨。
3. 若整個目錄範圍確實有 error，但全部落在本次未觸碰的既有檔案，判定為「TC 本身的 scope 撰寫缺陷」，不是程式碼缺陷、不阻斷本卡片；但必須在卡片上寫明兩次指令的差異與各自結果，不能只挑對自己有利的那次結果寫上去、隱藏文字上明寫的失敗結果。

**Why:** 若不區分「TC 寫錯 scope」與「程式碼真的有問題」，QA 要嘛會誤退一張其實乾淨的卡片（傷團隊效率），要嘛會為了讓 TC 通過而悄悄縮小 scope 卻不記錄（喪失可重現性、掩蓋了 TC 本身需要修正的事實）。

**How to apply:** 未來任何「程式碼規範」類 TC，撰寫時應直接把檢查目標寫成與同一條 AC 完全相同的檔案路徑（而非套件目錄），除非 AC 本身明確要求全套件層級的規範（如「全專案 ruff check 需綠燈」這種没有排除既有檔案的 AC）。QA 執行驗收時，若發現 TC 指令目標比 AC 寬，兩個 scope 都要實跑、都要記錄，並在卡片上明確判定屬於「TC scope 缺陷」還是「新程式碼缺陷」。

Related: [[feedback-no-live-db-verification]], [[feedback-etl-boundary-conditions]], [[feedback-materialized-view-api-testing]]
