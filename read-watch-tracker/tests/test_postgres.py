from __future__ import annotations

import os

import pytest

from factory import create_store
from postgres_store import PostgresRecordStore


pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set; skip PostgreSQL integration tests",
)


@pytest.fixture
def pg_store():
    store = create_store(backend="postgresql")
    assert isinstance(store, PostgresRecordStore)
    store.initialize()
    yield store
    store.close()


def test_postgres_crud_and_tag_filter(pg_store) -> None:
    record_id = "PG-B001"
    pg_store.delete("book", record_id)

    created = pg_store.create(
        "book",
        {
            "record_id": record_id,
            "title": "PostgreSQL 實戰",
            "isbn": "9780000000000",
            "rating": 4,
            "genre": "資料庫",
            "status": "進行中",
            "remark": "正式 runtime 驗證",
            "tags": ["PG", "資料庫"],
        },
    )
    assert created.record_id == record_id

    by_tag = pg_store.list_records(tag="PG")
    assert any(record.record_id == record_id for record in by_tag)

    updated = pg_store.update("book", record_id, {"status": "完成"})
    assert updated.status == "完成"

    assert pg_store.delete("book", record_id) is True
