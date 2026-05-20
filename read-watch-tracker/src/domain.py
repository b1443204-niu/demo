from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, unquote_plus


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

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "movie": (
        "record_id",
        "title",
        "rating",
        "genre",
        "status",
        "remark",
        "tags",
        "created_at",
        "updated_at",
    ),
    "book": (
        "record_id",
        "title",
        "isbn",
        "rating",
        "genre",
        "status",
        "remark",
        "tags",
        "created_at",
        "updated_at",
    ),
    "course": (
        "record_id",
        "title",
        "platform",
        "instructor",
        "url",
        "rating",
        "genre",
        "status",
        "remark",
        "tags",
        "created_at",
        "updated_at",
    ),
    "paper": (
        "record_id",
        "title",
        "year",
        "doi_or_url",
        "key_takeaways",
        "implementation_value",
        "rating",
        "genre",
        "status",
        "remark",
        "tags",
        "created_at",
        "updated_at",
    ),
}

DEMO_SEED_RECORDS: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "movie",
        {
            "record_id": "M001",
            "title": "奧本海默",
            "genre": "傳記/歷史",
            "status": "完成",
            "remark": "諾蘭式的敘事風格，配樂震撼。",
            "tags": ["諾蘭", "歷史"],
        },
    ),
    (
        "movie",
        {
            "record_id": "M002",
            "title": "葬送的芙莉蓮",
            "genre": "奇幻/冒險",
            "status": "進行中",
            "remark": "節奏舒服，關於時間的思考很深。",
            "tags": ["動畫", "奇幻"],
        },
    ),
    (
        "book",
        {
            "record_id": "B001",
            "title": "蛤蟆先生去看心理師",
            "isbn": "97895713854",
            "rating": 5,
            "genre": "心理學",
            "status": "完成",
            "remark": "非常療癒，適合低潮期閱讀。",
            "tags": ["心理", "療癒"],
        },
    ),
    (
        "book",
        {
            "record_id": "B002",
            "title": "原子習慣",
            "isbn": "978957137731",
            "genre": "自我成長",
            "status": "進行中",
            "remark": "觀點紮實，實作性很高。",
            "tags": ["習慣", "成長"],
        },
    ),
    (
        "course",
        {
            "record_id": "C001",
            "title": "物聯網應用：RFID 系統與技術",
            "platform": "磨課師",
            "instructor": "黃朝曦",
            "rating": 3,
            "genre": "資訊工程/物聯網",
            "status": "完成",
            "url": "https://example.test/rfid",
            "remark": "",
            "tags": ["IoT"],
        },
    ),
    (
        "course",
        {
            "record_id": "C002",
            "title": "Deep Learning Specialization（深度學習專業課程）",
            "platform": "Coursera",
            "instructor": "Andrew Ng（吳恩達）",
            "genre": "人工智慧/神經網路",
            "status": "進行中",
            "url": "https://example.test/dl",
            "remark": "",
            "tags": ["AI", "深度學習"],
        },
    ),
    (
        "paper",
        {
            "record_id": "P001",
            "title": "YOLOv8: Real-Time Object Detection",
            "year": 2023,
            "doi_or_url": "10.48550/arXiv.2304.00501",
            "key_takeaways": "引入新的 C2f 模組，在精度與速度平衡上優於前代，適合移動端部署。",
            "implementation_value": "極高。適用於 BlindHelper 的物件偵測模組。",
            "genre": "Object Detection",
            "status": "完成",
            "remark": "",
            "tags": ["YOLO", "CV"],
        },
    ),
    (
        "paper",
        {
            "record_id": "P002",
            "title": "RandLA-Net: Deep Learning for Large-Scale Point Clouds",
            "year": 2020,
            "doi_or_url": "10.1109/CVPR42600.2020.01112",
            "key_takeaways": "提出輕量級點雲語義分割架構，能有效處理大規模 3D 數據，減少運算開銷。",
            "implementation_value": "中。可用於 LiDAR 數據的環境特徵提取。",
            "genre": "Point Cloud",
            "status": "想讀/想看",
            "remark": "",
            "tags": ["LiDAR", "3D"],
        },
    ),
)


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


class RecordRepository(Protocol):
    backend: str

    def initialize(self) -> None: ...

    def close(self) -> None: ...

    def table_names(self) -> set[str]: ...

    def create(self, record_type: str, payload: dict[str, Any]) -> MediaRecord: ...

    def get(self, record_type: str, record_id: str) -> MediaRecord | None: ...

    def update(
        self,
        record_type: str,
        record_id: str,
        updates: dict[str, Any],
    ) -> MediaRecord: ...

    def delete(self, record_type: str, record_id: str) -> bool: ...

    def list_records(
        self,
        *,
        record_type: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
        genre: str | None = None,
        status: str | None = None,
    ) -> list[MediaRecord]: ...

    def dashboard(self) -> dict[str, Any]: ...


def health() -> dict[str, str]:
    return {"status": "ok", "service": "read-watch-tracker"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_timestamp(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat(timespec="seconds")
    return str(value)


def postgresql_schema() -> str:
    return (Path(__file__).resolve().parents[1] / "schema.sql").read_text(encoding="utf-8")


def parse_query_string(query_string: str) -> dict[str, str]:
    if not query_string:
        return {}
    parsed = parse_qs(query_string, keep_blank_values=False)
    return {key: unquote_plus(values[0]) for key, values in parsed.items() if values}


def resolve_table(record_type: str) -> str:
    try:
        return TYPE_TO_TABLE[record_type]
    except KeyError as exc:
        raise ValidationError(f"record_type must be one of {RECORD_TYPES}") from exc


def record_from_payload(
    record_type: str,
    payload: dict[str, Any],
    *,
    preserve_time: bool = False,
) -> MediaRecord:
    resolve_table(record_type)
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


def row_to_record(record_type: str, row: dict[str, Any]) -> MediaRecord:
    data = dict(row)
    tags = data.get("tags")
    if isinstance(tags, str):
        import json

        data["tags"] = json.loads(tags or "[]")
    elif tags is None:
        data["tags"] = []
    else:
        data["tags"] = list(tags)
    data["created_at"] = format_timestamp(data.get("created_at"))
    data["updated_at"] = format_timestamp(data.get("updated_at"))
    data["record_type"] = record_type
    return MediaRecord(**data)


def columns_for_record(record: MediaRecord) -> dict[str, Any]:
    full = record.to_dict()
    allowed = set(TABLE_COLUMNS[record.record_type])
    return {key: full[key] for key in allowed if key in full}


def seed_demo_records(store: RecordRepository) -> int:
    inserted = 0
    for record_type, payload in DEMO_SEED_RECORDS:
        if store.get(record_type, payload["record_id"]) is None:
            store.create(record_type, payload)
            inserted += 1
    return inserted
