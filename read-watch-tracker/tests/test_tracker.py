from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from app import MediaRecord, RecordStore, ValidationError, create_app, health
from domain import parse_query_string, postgresql_schema, seed_demo_records


def make_store(tmp_path: Path) -> RecordStore:
    store = RecordStore(tmp_path / "tracker.sqlite3")
    store.initialize()
    return store


def test_health_reports_json_api() -> None:
    assert health() == {"status": "ok", "service": "read-watch-tracker"}


def test_postgresql_schema_covers_required_tables() -> None:
    schema = postgresql_schema()
    assert "CREATE TABLE IF NOT EXISTS movie_records" in schema
    assert "CREATE TABLE IF NOT EXISTS book_records" in schema
    assert "CREATE TABLE IF NOT EXISTS course_records" in schema
    assert "CREATE TABLE IF NOT EXISTS paper_records" in schema
    assert "CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)" in schema


def test_repository_initializes_sqlite_tables(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    tables = store.table_names()
    assert {
        "movie_records",
        "book_records",
        "course_records",
        "paper_records",
    }.issubset(tables)


@pytest.mark.parametrize(
    ("record_type", "payload", "expected_id"),
    [
        (
            "movie",
            {
                "record_id": "M001",
                "title": "奧本海默",
                "rating": 5,
                "genre": "傳記/歷史",
                "status": "完成",
                "remark": "配樂震撼",
                "tags": ["諾蘭", "歷史"],
            },
            "M001",
        ),
        (
            "book",
            {
                "record_id": "B001",
                "title": "原子習慣",
                "isbn": "978957137731",
                "rating": 4,
                "genre": "自我成長",
                "status": "進行中",
                "remark": "實作性高",
                "tags": ["習慣"],
            },
            "B001",
        ),
        (
            "course",
            {
                "record_id": "C001",
                "title": "Deep Learning Specialization",
                "platform": "Coursera",
                "instructor": "Andrew Ng",
                "url": "https://example.test/course",
                "rating": None,
                "genre": "人工智慧",
                "status": "進行中",
                "remark": "補神經網路基礎",
                "tags": ["AI", "深度學習"],
            },
            "C001",
        ),
        (
            "paper",
            {
                "record_id": "P001",
                "title": "YOLOv8: Real-Time Object Detection",
                "year": 2023,
                "doi_or_url": "10.48550/arXiv.2304.00501",
                "key_takeaways": "C2f 模組提升速度與精度平衡",
                "implementation_value": "極高",
                "rating": 5,
                "genre": "Object Detection",
                "status": "完成",
                "remark": "適合移動端部署",
                "tags": ["YOLO", "CV"],
            },
            "P001",
        ),
    ],
)
def test_crud_for_all_record_types(
    tmp_path: Path,
    record_type: str,
    payload: dict[str, object],
    expected_id: str,
) -> None:
    store = make_store(tmp_path)

    created = store.create(record_type, payload)
    assert created.record_id == expected_id
    assert created.record_type == record_type
    assert created.title == payload["title"]

    fetched = store.get(record_type, expected_id)
    assert fetched == created

    updated = store.update(record_type, expected_id, {"status": "完成", "rating": 5})
    assert updated.status == "完成"
    assert updated.rating == 5

    deleted = store.delete(record_type, expected_id)
    assert deleted is True
    assert store.get(record_type, expected_id) is None


def test_search_filter_rating_and_note_flow(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create(
        "book",
        {
            "record_id": "B002",
            "title": "蛤蟆先生去看心理師",
            "isbn": "97895713854",
            "rating": 5,
            "genre": "心理學",
            "status": "完成",
            "remark": "非常療癒",
            "tags": ["心理", "療癒"],
        },
    )
    store.create(
        "movie",
        {
            "record_id": "M002",
            "title": "葬送的芙莉蓮",
            "rating": 4,
            "genre": "奇幻/冒險",
            "status": "進行中",
            "remark": "關於時間的思考很深",
            "tags": ["動畫", "奇幻"],
        },
    )

    by_keyword = store.list_records(keyword="芙莉蓮")
    assert [record.record_id for record in by_keyword] == ["M002"]

    by_tag = store.list_records(tag="心理")
    assert [record.record_id for record in by_tag] == ["B002"]

    by_status = store.list_records(status="完成")
    assert [record.record_id for record in by_status] == ["B002"]

    by_type = store.list_records(record_type="movie", genre="奇幻/冒險")
    assert [record.record_id for record in by_type] == ["M002"]


def test_validation_rejects_invalid_rating_status_and_type(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    with pytest.raises(ValidationError, match="rating"):
        MediaRecord(record_id="B003", record_type="book", title="Bad", rating=6)

    with pytest.raises(ValidationError, match="status"):
        MediaRecord(record_id="B003", record_type="book", title="Bad", status="未知")

    with pytest.raises(ValidationError, match="record_type"):
        store.create("unknown", {"record_id": "X001", "title": "Bad"})


def test_dashboard_counts_status_types_high_rated_and_tags(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create(
        "book",
        {
            "record_id": "B004",
            "title": "原子習慣",
            "rating": 5,
            "genre": "自我成長",
            "status": "完成",
            "tags": ["習慣", "成長"],
        },
    )
    store.create(
        "course",
        {
            "record_id": "C004",
            "title": "RFID 系統與技術",
            "rating": 3,
            "genre": "物聯網",
            "status": "進行中",
            "tags": ["IoT"],
        },
    )

    dashboard = store.dashboard()
    assert dashboard["total"] == 2
    assert dashboard["by_status"] == {"完成": 1, "進行中": 1}
    assert dashboard["by_type"] == {"book": 1, "course": 1}
    assert dashboard["completed"] == ["B004"]
    assert dashboard["high_rated"] == ["B004"]
    assert dashboard["by_tag"]["習慣"] == 1


def test_parse_query_string_decodes_percent_encoding() -> None:
    params = parse_query_string("status=%E9%80%B2%E8%A1%8C%E4%B8%AD&tag=AI")
    assert params["status"] == "進行中"
    assert params["tag"] == "AI"


def test_seed_demo_records_is_idempotent(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = seed_demo_records(store)
    second = seed_demo_records(store)
    assert first == 8
    assert second == 0
    assert store.get("book", "B001") is not None
    assert store.get("paper", "P002") is not None


def test_demo_seed_api_route(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    client = TestClient(create_app(store))
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert response.json()["inserted"] == 8
    again = client.post("/api/demo/seed")
    assert again.json()["inserted"] == 0


def test_fastapi_exposes_json_api(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    client = TestClient(create_app(store))

    healthz = client.get("/healthz")
    assert healthz.status_code == 200
    assert healthz.json()["runtime"] == "fastapi"
    assert healthz.json()["backend"] == "sqlite"

    response = client.post(
        "/api/records/book",
        json={
            "record_id": "B005",
            "title": "Clean Architecture",
            "rating": 5,
            "genre": "Software",
            "status": "完成",
            "remark": "邊界清楚",
        },
    )
    assert response.status_code == 201

    listed = client.get("/api/records", params={"keyword": "Clean"})
    assert listed.status_code == 200
    assert listed.json()["items"][0]["record_id"] == "B005"


def test_sqlite_database_persists_between_store_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "tracker.sqlite3"
    first = RecordStore(db_path)
    first.initialize()
    first.create("movie", {"record_id": "M010", "title": "Inception", "status": "完成"})
    first.close()

    second = RecordStore(db_path)
    second.initialize()
    assert second.get("movie", "M010") is not None
    second.close()

    with sqlite3.connect(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM movie_records").fetchone()[0]
    assert count == 1
