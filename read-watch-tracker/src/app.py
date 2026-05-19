from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECORD_TYPES = ("book", "movie", "course", "paper")
STATUSES = ("想讀/想看", "進行中", "完成")
TYPE_TO_TABLE = {
    "book": "book_records",
    "movie": "movie_records",
    "course": "course_records",
    "paper": "paper_records",
}

RECORD_FIELDS = {
    "record_id",
    "record_type",
    "title",
    "rating",
    "genre",
    "status",
    "remark",
    "tags",
    "isbn",
    "platform",
    "instructor",
    "url",
    "year",
    "doi_or_url",
    "key_takeaways",
    "implementation_value",
    "created_at",
    "updated_at",
}


class ValidationError(ValueError):
    """Raised when user input violates tracker invariants."""


@dataclass(frozen=True)
class MediaRecord:
    record_id: str
    record_type: str
    title: str
    rating: int | None = None
    genre: str = ""
    status: str = "想讀/想看"
    remark: str = ""
    tags: list[str] = field(default_factory=list)
    isbn: str | None = None
    platform: str | None = None
    instructor: str | None = None
    url: str | None = None
    year: int | None = None
    doi_or_url: str | None = None
    key_takeaways: str | None = None
    implementation_value: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if self.record_type not in RECORD_TYPES:
            raise ValidationError(f"record_type must be one of {RECORD_TYPES}")
        if not self.record_id.strip():
            raise ValidationError("record_id is required")
        if not self.title.strip():
            raise ValidationError("title is required")
        if self.rating is not None and not 1 <= self.rating <= 5:
            raise ValidationError("rating must be between 1 and 5")
        if self.status not in STATUSES:
            raise ValidationError(f"status must be one of {STATUSES}")
        if self.year is not None and self.year < 0:
            raise ValidationError("year must be positive")

        normalized_tags = [str(tag).strip() for tag in self.tags if str(tag).strip()]
        object.__setattr__(self, "tags", normalized_tags)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value is not None}


def health() -> dict[str, str]:
    return {"status": "ok", "service": "read-watch-tracker"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def postgresql_schema() -> str:
    return """CREATE TABLE IF NOT EXISTS movie_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS book_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    isbn TEXT,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    platform TEXT,
    instructor TEXT,
    url TEXT,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER,
    doi_or_url TEXT,
    key_takeaways TEXT,
    implementation_value TEXT,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


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


class RecordStore:
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
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __del__(self) -> None:
        self.close()

    def table_names(self) -> set[str]:
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row["name"] for row in rows}

    def create(self, record_type: str, payload: dict[str, Any]) -> MediaRecord:
        record = self._record_from_payload(record_type, payload)
        table_name = self._table(record_type)
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
        table_name = self._table(record_type)
        row = self.connection.execute(
            f"SELECT * FROM {table_name} WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

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
        record = self._record_from_payload(record_type, payload, preserve_time=True)

        data = record.to_dict()
        data["tags"] = json.dumps(record.tags, ensure_ascii=False)
        assignments = ", ".join(
            f"{column} = ?" for column in data if column != "record_id"
        )
        values = [value for column, value in data.items() if column != "record_id"]
        values.append(record_id)
        table_name = self._table(record_type)
        self.connection.execute(
            f"UPDATE {table_name} SET {assignments} WHERE record_id = ?",
            values,
        )
        self.connection.commit()
        return record

    def delete(self, record_type: str, record_id: str) -> bool:
        table_name = self._table(record_type)
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
            self._table(record_type)
        else:
            record_types = list(RECORD_TYPES)

        records: list[MediaRecord] = []
        for candidate_type in record_types:
            table_name = self._table(candidate_type)
            rows = self.connection.execute(f"SELECT * FROM {table_name}").fetchall()
            records.extend(self._row_to_record(row) for row in rows)

        keyword_lower = keyword.lower() if keyword else None
        filtered = [
            record
            for record in records
            if (keyword_lower is None or keyword_lower in record.title.lower())
            and (tag is None or tag in record.tags)
            and (genre is None or genre == record.genre)
            and (status is None or status == record.status)
        ]
        return sorted(filtered, key=lambda record: (record.record_type, record.record_id))

    def dashboard(self) -> dict[str, Any]:
        records = self.list_records()
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_tag: dict[str, int] = {}

        for record in records:
            by_status[record.status] = by_status.get(record.status, 0) + 1
            by_type[record.record_type] = by_type.get(record.record_type, 0) + 1
            for tag in record.tags:
                by_tag[tag] = by_tag.get(tag, 0) + 1

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

    def _record_from_payload(
        self,
        record_type: str,
        payload: dict[str, Any],
        *,
        preserve_time: bool = False,
    ) -> MediaRecord:
        self._table(record_type)
        now = utc_now()
        data = {
            key: value
            for key, value in payload.items()
            if key in RECORD_FIELDS and key != "record_type"
        }
        data["record_type"] = record_type
        if not preserve_time:
            data.setdefault("created_at", now)
            data.setdefault("updated_at", now)
        else:
            data.setdefault("updated_at", now)
        data.setdefault("status", "想讀/想看")
        data.setdefault("genre", "")
        data.setdefault("remark", "")
        data.setdefault("tags", [])
        return MediaRecord(**data)

    def _row_to_record(self, row: sqlite3.Row) -> MediaRecord:
        data = dict(row)
        data["tags"] = json.loads(data.get("tags") or "[]")
        return MediaRecord(**data)

    def _table(self, record_type: str) -> str:
        try:
            return TYPE_TO_TABLE[record_type]
        except KeyError as exc:
            raise ValidationError(f"record_type must be one of {RECORD_TYPES}") from exc


@dataclass(frozen=True)
class JsonResponse:
    status: int
    body: str
    headers: dict[str, str] = field(
        default_factory=lambda: {"content-type": "application/json; charset=utf-8"}
    )

    @classmethod
    def from_data(cls, status: int, data: Any) -> JsonResponse:
        return cls(status=status, body=json.dumps(data, ensure_ascii=False))


class TrackerApi:
    def __init__(self, store: RecordStore | None = None) -> None:
        self.store = store or RecordStore()
        self._initialized = False
        if store is not None:
            self.store.initialize()
            self._initialized = True

    def routes(self) -> list[str]:
        return [
            "GET /",
            "GET /healthz",
            "GET /api/records",
            "POST /api/records/{record_type}",
            "GET /api/records/{record_type}/{record_id}",
            "PATCH /api/records/{record_type}/{record_id}",
            "DELETE /api/records/{record_type}/{record_id}",
            "GET /api/dashboard",
        ]

    def handle_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
    ) -> JsonResponse:
        clean_path, _, query_string = path.partition("?")
        query = parse_query_string(query_string)

        try:
            if method == "GET" and clean_path == "/":
                index_path = Path(__file__).resolve().parents[1] / "index.html"
                return JsonResponse(
                    status=200,
                    body=index_path.read_text(encoding="utf-8"),
                    headers={"content-type": "text/html; charset=utf-8"},
                )
            if method == "GET" and clean_path == "/healthz":
                return JsonResponse.from_data(200, health())
            self._ensure_initialized()
            if method == "GET" and clean_path == "/api/dashboard":
                return JsonResponse.from_data(200, self.store.dashboard())
            if method == "GET" and clean_path == "/api/records":
                records = self.store.list_records(**query)
                return JsonResponse.from_data(
                    200,
                    {"items": [record.to_dict() for record in records]},
                )
            if clean_path.startswith("/api/records/"):
                parts = clean_path.strip("/").split("/")
                if len(parts) == 3 and method == "POST":
                    record = self.store.create(parts[2], body or {})
                    return JsonResponse.from_data(201, record.to_dict())
                if len(parts) == 4:
                    _, _, record_type, record_id = parts
                    if method == "GET":
                        record = self.store.get(record_type, record_id)
                        if record is None:
                            return JsonResponse.from_data(404, {"error": "not found"})
                        return JsonResponse.from_data(200, record.to_dict())
                    if method == "PATCH":
                        record = self.store.update(record_type, record_id, body or {})
                        return JsonResponse.from_data(200, record.to_dict())
                    if method == "DELETE":
                        deleted = self.store.delete(record_type, record_id)
                        return JsonResponse.from_data(200, {"deleted": deleted})
        except (KeyError, ValidationError, sqlite3.IntegrityError) as exc:
            return JsonResponse.from_data(400, {"error": str(exc)})

        return JsonResponse.from_data(404, {"error": "not found"})

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.store.initialize()
            self._initialized = True

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            raise RuntimeError("Only HTTP scope is supported")

        raw_body = b""
        more_body = True
        while more_body:
            message = await receive()
            raw_body += message.get("body", b"")
            more_body = message.get("more_body", False)

        body = json.loads(raw_body.decode("utf-8")) if raw_body else None
        path = scope["path"]
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            path = f"{path}?{query_string}"
        response = self.handle_json(scope["method"], path, body)
        await send(
            {
                "type": "http.response.start",
                "status": response.status,
                "headers": [
                    (key.encode("utf-8"), value.encode("utf-8"))
                    for key, value in response.headers.items()
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": response.body.encode("utf-8"),
            }
        )


def parse_query_string(query_string: str) -> dict[str, str]:
    if not query_string:
        return {}
    params: dict[str, str] = {}
    for pair in query_string.split("&"):
        key, _, value = pair.partition("=")
        if key:
            params[key] = value.replace("+", " ")
    return params


def create_app(store: RecordStore | None = None) -> TrackerApi:
    return TrackerApi(store)


app = create_app()


def run_asgi_once(
    api: TrackerApi,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> JsonResponse:
    async def call() -> JsonResponse:
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return {
                "type": "http.request",
                "body": json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
                if body is not None
                else b"",
                "more_body": False,
            }

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await api(
            {
                "type": "http",
                "method": method,
                "path": path,
                "query_string": b"",
            },
            receive,
            send,
        )
        status = int(sent[0]["status"])
        response_body = sent[1]["body"].decode("utf-8")
        return JsonResponse(status=status, body=response_body)

    return asyncio.run(call())
