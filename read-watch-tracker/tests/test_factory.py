from __future__ import annotations

import os

import pytest

from factory import create_store, database_backend
from postgres_store import PostgresRecordStore
from sqlite_store import SqliteRecordStore


def test_database_backend_defaults_to_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRACKER_DB", raising=False)
    assert database_backend() == "sqlite"


def test_create_store_sqlite(tmp_path) -> None:
    store = create_store(backend="sqlite", db_path=tmp_path / "tracker.sqlite3")
    assert isinstance(store, SqliteRecordStore)


def test_create_store_postgres_requires_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_store(backend="postgresql")


def test_create_store_postgres_with_dsn() -> None:
    store = create_store(
        backend="postgresql",
        dsn="postgresql://user:pass@localhost:5432/db",
    )
    assert isinstance(store, PostgresRecordStore)


def test_create_store_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        create_store(backend="mysql")
