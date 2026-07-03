# Open House Prices — Backend

## 專案簡介
台灣全台房地產價格地圖後端服務。
串接實價登錄資料，提供地圖均價、趨勢圖表、地址估價等 API。

## 技術棧
- 語言：Python 3.11+
- 框架：FastAPI（Async）
- 資料庫：PostgreSQL 15 + PostGIS 3.3
- Cache：Redis 7
- Migration：Alembic
- 背景任務：Celery + Redis
- 套件管理：uv

## 目錄結構
```
open-house-prices-backend/
├── api/              ← FastAPI 端點
├── etl/              ← 資料管線（實價登錄抓取、清洗、寫入）
├── ml/               ← ML 估價模型
├── shared/           ← 共用 models、DB 連線、設定
├── tests/            ← pytest 測試
├── agents/           ← 各角色 CLAUDE.md
│   ├── backend-engineer.md
│   ├── qa-engineer.md
│   └── senior-engineer.md
└── .workspace/
    └── tasks/        ← TASK-001-{標題}.md
```

## 環境變數
所有設定從 .env 讀取，不得 hardcode。
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/realestate
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ENVIRONMENT=development
```

## 程式碼規範
- 套件安裝：uv add {package}，不使用 pip
- DB 連線：統一從 shared/database.py 引入
- 設定：統一從 shared/config.py 讀取（pydantic-settings）
- Log：使用 Python logging 模組，禁止使用 print
- Type hint：所有函式必須標註
- Docstring：Google 風格
- 格式化：ruff format
- Lint：ruff check
- 命名：檔案 snake_case、Class PascalCase、常數 UPPER_SNAKE_CASE

## 啟動各角色 Agent
```bash
# 後端工程師
claude --append agents/backend-engineer.md

# QA 工程師
claude --append agents/qa-engineer.md

# Code Reviewer
claude --append agents/senior-engineer.md
```

## 工作區
任務卡片位置：.workspace/tasks/TASK-{編號}-{標題}.md

卡片狀態流程：
需求確認中 → QA撰寫測案 → 開發中 → Code Review → QA測試 → 完成

Code Review 退回超過 3 次 → 退回需求確認中，與需求方重新討論。
