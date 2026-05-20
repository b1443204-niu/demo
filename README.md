# Read & Watch Tracker（公開版）

個人閱讀與觀影紀錄 Web App：FastAPI + PostgreSQL（正式）/ SQLite（Demo）。

| 路徑 | 說明 |
| --- | --- |
| [`read-watch-tracker/`](read-watch-tracker/) | 後端、前端、測試、schema |
| [`網站搜尋.html`](網站搜尋.html) | 紀錄搜尋頁（API 啟動後開 `/search` 或本檔） |

## 快速開始

```powershell
cd read-watch-tracker
pip install -r requirements.txt
$env:TRACKER_DB = "sqlite"
python -m uvicorn app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

瀏覽器：

- 主畫面：`http://127.0.0.1:8000/`
- 搜尋頁：`http://127.0.0.1:8000/search`
- API 文件：`http://127.0.0.1:8000/docs`

詳細規格與 PostgreSQL 設定見 [`read-watch-tracker/README.md`](read-watch-tracker/README.md)。

## 驗證

```powershell
cd read-watch-tracker
pytest -q
```
