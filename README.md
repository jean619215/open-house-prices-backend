# Open House Prices — Backend

台灣全台房地產價格地圖後端服務。詳細專案規範見 [CLAUDE.md](./CLAUDE.md)。

## 環境需求
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（套件管理）
- Docker Desktop（本地 PostgreSQL + PostGIS + Redis）

## 初次設定
```bash
# 1. 安裝相依套件
uv sync

# 2. 建立 .env（首次）
cp .env.example .env
```

## 本地 Docker 服務

### 啟動
```bash
docker compose up -d            # 啟動 postgres + redis（背景）
docker compose ps               # 確認兩個容器 STATUS 皆為 healthy
```

> **對外 port**：postgres → host **5434**、redis → host **6380**（容器內仍是 5432 / 6379）。
> 改用非預設 port 是為了避開本機常駐 postgres（5432）與其他專案容器（pf-postgres 5433、pf-redis 6379），
> 讓多個專案的 DB 可同時並存。`.env` 的 `DATABASE_URL` / `REDIS_URL` 已分別對應 `localhost:5434` 與 `localhost:6380`。
>
> **Port 被佔用時**：若看到 `Bind for 0.0.0.0:<port> failed: port is already allocated`，
> 先找出佔用者再處理：
> ```bash
> lsof -nP -iTCP:6379 -sTCP:LISTEN                                # 找佔用 port 的 process
> docker ps --format "table {{.Names}}\t{{.Ports}}" | grep 6379   # 若是其他容器
> docker stop <容器名稱>                                          # 停掉它，或改 docker-compose.yml 的對外 port
> docker compose up -d
> ```

### 停止
```bash
docker compose stop             # 暫停容器（保留資料，下次 start 即可）
docker compose down             # 移除容器（保留 volume / 資料）
docker compose down -v          # 移除容器並清空資料（重置 DB）
```

## 啟動服務
```bash
uv run alembic upgrade head                       # 建立資料表
uv run uvicorn api.main:app --reload              # 啟動 FastAPI（http://127.0.0.1:8000）
```

## 健康檢查
```bash
curl -i http://127.0.0.1:8000/health
# 正常：HTTP 200 {"status":"ok","db":"connected","redis":"connected"}
```

## 測試與檢查
```bash
uv run pytest                   # 單元測試
uv run ruff check .             # Lint
uv run ruff format .            # 格式化
```

### 斷線情境手動驗證（需 Docker）
```bash
docker compose stop postgres && curl -i http://127.0.0.1:8000/health   # 預期 503, db disconnected
docker compose start postgres

docker compose stop redis && curl -i http://127.0.0.1:8000/health      # 預期 503, redis disconnected
docker compose start redis
```

### 並發驗證
```bash
seq 10 | xargs -P10 -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:8000/health | sort | uniq -c                        # 預期 10 200
```
