from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from domain import (
    TYPE_TO_TABLE,
    MediaRecord,
    record_from_payload,
    resolve_table,
    row_to_record,
    utc_now,
)


SQLITE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table_name} (
    record_id TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    title TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    isbn TEXT,
    platform TEXT,
    instructor TEXT,
    url TEXT,
    year INTEGER,
    doi_or_url TEXT,
    key_takeaways TEXT,
    implementation_value TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class SqliteRecordStore:
    backend = "sqlite"

    def __init__(self, db_path: str | Path = "data/tracker.sqlite3") -> None:
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self.connection
        for table_name in TYPE_TO_TABLE.values():
            connection.execute(SQLITE_TABLE_SQL.format(table_name=table_name))
        connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def table_names(self) -> set[str]:
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row["name"] for row in rows}

    def create(self, record_type: str, payload: dict[str, Any]) -> MediaRecord:
        record = record_from_payload(record_type, payload)
        table_name = resolve_table(record_type)
        data = record.to_dict()
        data["tags"] = json.dumps(record.tags, ensure_ascii=False)
        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        values = [data[column] for column in columns]
        self.connection.execute(
            f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})",
            values,
        )
        self.connection.commit()
        return record

    def get(self, record_type: str, record_id: str) -> MediaRecord | None:
        table_name = resolve_table(record_type)
        row = self.connection.execute(
            f"SELECT * FROM {table_name} WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return row_to_record(record_type, dict(row))

    def update(
        self,
        record_type: str,
        record_id: str,
        updates: dict[str, Any],
    ) -> MediaRecord:
        current = self.get(record_type, record_id)
        if current is None:
            raise KeyError(record_id)

        payload = current.to_dict()
        payload.update(updates)
        payload["record_id"] = record_id
        payload["record_type"] = record_type
        payload["created_at"] = current.created_at
        payload["updated_at"] = utc_now()
        record = record_from_payload(record_type, payload, preserve_time=True)

        data = record.to_dict()
        data["tags"] = json.dumps(record.tags, ensure_ascii=False)
        assignments = ", ".join(
            f"{column} = ?" for column in data if column != "record_id"
        )
        values = [value for column, value in data.items() if column != "record_id"]
        values.append(record_id)
        table_name = resolve_table(record_type)
        self.connection.execute(
            f"UPDATE {table_name} SET {assignments} WHERE record_id = ?",
            values,
        )
        self.connection.commit()
        return record

    def delete(self, record_type: str, record_id: str) -> bool:
        table_name = resolve_table(record_type)
        cursor = self.connection.execute(
            f"DELETE FROM {table_name} WHERE record_id = ?",
            (record_id,),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_records(
        self,
        *,
        record_type: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
        genre: str | None = None,
        status: str | None = None,
    ) -> list[MediaRecord]:
        if record_type is not None:
            record_types = [record_type]
            resolve_table(record_type)
        else:
            record_types = list(TYPE_TO_TABLE)

        records: list[MediaRecord] = []
        for candidate_type in record_types:
            records.extend(
                self._fetch_table_records(
                    candidate_type,
                    keyword=keyword,
                    genre=genre,
                    status=status,
                )
            )

        if tag is not None:
            records = [record for record in records if tag in record.tags]
        return sorted(records, key=lambda record: (record.record_type, record.record_id))

    def _fetch_table_records(
        self,
        record_type: str,
        *,
        keyword: str | None,
        genre: str | None,
        status: str | None,
    ) -> list[MediaRecord]:
        table_name = resolve_table(record_type)
        clauses: list[str] = []
        params: list[Any] = []
        if keyword:
            clauses.append("LOWER(title) LIKE ?")
            params.append(f"%{keyword.lower()}%")
        if genre:
            clauses.append("genre = ?")
            params.append(genre)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"SELECT * FROM {table_name}{where} ORDER BY record_id",
            params,
        ).fetchall()
        return [row_to_record(record_type, dict(row)) for row in rows]

    def dashboard(self) -> dict[str, Any]:
        records = self.list_records()
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_tag: dict[str, int] = {}

        for record in records:
            by_status[record.status] = by_status.get(record.status, 0) + 1
            by_type[record.record_type] = by_type.get(record.record_type, 0) + 1
            for item in record.tags:
                by_tag[item] = by_tag.get(item, 0) + 1

        return {
            "total": len(records),
            "by_status": by_status,
            "by_type": by_type,
            "completed": [record.record_id for record in records if record.status == "完成"],
            "high_rated": [
                record.record_id
                for record in records
                if record.rating is not None and record.rating >= 5
            ],
            "by_tag": by_tag,
        }


RecordStore = SqliteRecordStore
