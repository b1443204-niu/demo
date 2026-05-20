from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain import RecordRepository


def database_backend() -> str:
    return os.environ.get("TRACKER_DB", "sqlite").strip().lower()


def create_store(
    *,
    backend: str | None = None,
    db_path: str | Path | None = None,
    dsn: str | None = None,
) -> RecordRepository:
    selected = (backend or database_backend()).lower()
    if selected in {"postgres", "postgresql", "pg"}:
        from postgres_store import PostgresRecordStore

        return PostgresRecordStore(dsn=dsn)
    if selected == "sqlite":
        from sqlite_store import SqliteRecordStore

        path = db_path or os.environ.get("TRACKER_SQLITE_PATH", "data/tracker.sqlite3")
        return SqliteRecordStore(path)
    raise ValueError(
        f"Unsupported TRACKER_DB={selected!r}; use 'sqlite' or 'postgresql'"
    )
