from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from domain import (
    TYPE_TO_TABLE,
    MediaRecord,
    columns_for_record,
    postgresql_schema,
    record_from_payload,
    resolve_table,
    row_to_record,
    utc_now,
)


class PostgresRecordStore:
    backend = "postgresql"

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.environ.get("DATABASE_URL", "")
        if not self.dsn:
            raise ValueError("DATABASE_URL is required for PostgreSQL runtime")
        self._connection: psycopg.Connection[Any] | None = None

    def initialize(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(postgresql_schema())
        self.connection.commit()

    @property
    def connection(self) -> psycopg.Connection[Any]:
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(self.dsn, row_factory=dict_row)
        return self._connection

    def close(self) -> None:
        if self._connection is not None and not self._connection.closed:
            self._connection.close()
        self._connection = None

    def table_names(self) -> set[str]:
        rows = self.connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            """
        ).fetchall()
        return {row["table_name"] for row in rows}

    def create(self, record_type: str, payload: dict[str, Any]) -> MediaRecord:
        record = record_from_payload(record_type, payload)
        table_name = resolve_table(record_type)
        data = columns_for_record(record)
        columns = list(data.keys())
        placeholders = ", ".join(f"%({column})s" for column in columns)
        column_sql = ", ".join(columns)
        query = f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})"
        self.connection.execute(query, data)
        self.connection.commit()
        return record

    def get(self, record_type: str, record_id: str) -> MediaRecord | None:
        table_name = resolve_table(record_type)
        row = self.connection.execute(
            f"SELECT * FROM {table_name} WHERE record_id = %s",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return row_to_record(record_type, row)

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

        data = columns_for_record(record)
        assignments = ", ".join(
            f"{column} = %({column})s" for column in data if column != "record_id"
        )
        data["record_id"] = record_id
        table_name = resolve_table(record_type)
        self.connection.execute(
            f"UPDATE {table_name} SET {assignments} WHERE record_id = %(record_id)s",
            data,
        )
        self.connection.commit()
        return record

    def delete(self, record_type: str, record_id: str) -> bool:
        table_name = resolve_table(record_type)
        cursor = self.connection.execute(
            f"DELETE FROM {table_name} WHERE record_id = %s",
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
                    tag=tag,
                    genre=genre,
                    status=status,
                )
            )
        return sorted(records, key=lambda record: (record.record_type, record.record_id))

    def _fetch_table_records(
        self,
        record_type: str,
        *,
        keyword: str | None,
        tag: str | None,
        genre: str | None,
        status: str | None,
    ) -> list[MediaRecord]:
        table_name = resolve_table(record_type)
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if keyword:
            clauses.append("LOWER(title) LIKE %(keyword)s")
            params["keyword"] = f"%{keyword.lower()}%"
        if genre:
            clauses.append("genre = %(genre)s")
            params["genre"] = genre
        if status:
            clauses.append("status = %(status)s")
            params["status"] = status
        if tag:
            clauses.append("%(tag)s = ANY(tags)")
            params["tag"] = tag
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"SELECT * FROM {table_name}{where} ORDER BY record_id",
            params,
        ).fetchall()
        return [row_to_record(record_type, row) for row in rows]

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
