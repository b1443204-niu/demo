# 個人閱讀與觀影紀錄系統

Read & Watch Tracker 是一個個人閱讀、觀影、課程與文獻紀錄 Web App。

## 功能

- 書籍、影片、課程、文獻紀錄 CRUD
- 標題搜尋與類型、標籤、題材、狀態篩選
- 1~5 星評分與心得備註
- 卡片式前端介面與統計儀表板

## 啟動

```bat
pip install -r requirements.txt
python -m uvicorn app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

開啟 http://127.0.0.1:8000/

## 測試

```bat
pytest -q
```

## PostgreSQL

PostgreSQL 初始化 schema 見 schema.sql。
