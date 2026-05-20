# 個人閱讀與觀影紀錄系統 (Read & Watch Tracker)

前後端分離 Web App：FastAPI REST API + 純 HTML/JS 前端。正式資料庫為 PostgreSQL；本機 Demo 可用 SQLite。

完整規格見 [`PRD.md`](PRD.md)。

## 依賴

```powershell
pip install -r requirements.txt
```

## 環境變數

| 變數 | 說明 | 預設 |
| --- | --- | --- |
| `TRACKER_DB` | `sqlite` 或 `postgresql` | `sqlite` |
| `TRACKER_SQLITE_PATH` | SQLite 檔案路徑 | `data/tracker.sqlite3` |
| `DATABASE_URL` | PostgreSQL DSN | — |

範例見 [`env.example`](env.example)。

## 啟動（SQLite Demo）

```powershell
$env:TRACKER_DB = "sqlite"
python -m uvicorn app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

## 啟動（PostgreSQL）

```powershell
$env:TRACKER_DB = "postgresql"
$env:DATABASE_URL = "postgresql://USER:PASS@127.0.0.1:5432/read_watch_tracker"
python scripts/init_postgres.py
python -m uvicorn app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

載入範例資料：`python scripts/seed_demo.py` 或前端「載入範例資料」。

## 頁面與 API

- `/` — 主畫面（新增、編輯、清單、儀表板）
- `/search` — 紀錄搜尋（對應 repo 根目錄 `網站搜尋.html`）
- `/healthz` — 健康檢查
- `/docs` — OpenAPI
- `/api/records` — CRUD 與篩選
- `/api/dashboard` — 儀表板統計

## 驗證

```powershell
pytest -q
```
