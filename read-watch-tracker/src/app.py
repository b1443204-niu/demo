from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from domain import (
    DEMO_SEED_RECORDS,
    RECORD_TYPES,
    MediaRecord,
    RecordRepository,
    ValidationError,
    health,
    parse_query_string,
    postgresql_schema,
    seed_demo_records,
)
from factory import create_store, database_backend
from sqlite_store import RecordStore, SqliteRecordStore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = PROJECT_ROOT / "index.html"


def search_page_path() -> Path | None:
    for candidate in (PROJECT_ROOT / "search.html", PROJECT_ROOT.parent / "網站搜尋.html"):
        if candidate.is_file():
            return candidate
    return None


class RecordPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    record_id: str
    title: str
    rating: int | None = None
    genre: str = ""
    status: str = "想讀/想看"
    remark: str = ""
    tags: list[str] = Field(default_factory=list)
    isbn: str | None = None
    platform: str | None = None
    instructor: str | None = None
    url: str | None = None
    year: int | None = None
    doi_or_url: str | None = None
    key_takeaways: str | None = None
    implementation_value: str | None = None


class RecordPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    rating: int | None = None
    genre: str | None = None
    status: str | None = None
    remark: str | None = None
    tags: list[str] | None = None
    isbn: str | None = None
    platform: str | None = None
    instructor: str | None = None
    url: str | None = None
    year: int | None = None
    doi_or_url: str | None = None
    key_takeaways: str | None = None
    implementation_value: str | None = None


def _payload_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(exclude_none=True)


def _register_routes(application: FastAPI, store: RecordRepository) -> None:
    @application.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        return INDEX_PATH.read_text(encoding="utf-8")

    @application.get("/search", response_class=HTMLResponse, include_in_schema=False)
    def search_page() -> str:
        path = search_page_path()
        if path is None:
            raise HTTPException(status_code=404, detail="search page not found")
        return path.read_text(encoding="utf-8")

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        return {**health(), "backend": store.backend, "runtime": "fastapi"}

    @application.get("/api/dashboard")
    def dashboard() -> dict[str, Any]:
        return store.dashboard()

    @application.post("/api/demo/seed")
    def demo_seed() -> dict[str, int]:
        return {"inserted": seed_demo_records(store)}

    @application.get("/api/records")
    def list_records(
        keyword: str | None = Query(default=None),
        tag: str | None = Query(default=None),
        genre: str | None = Query(default=None),
        status: str | None = Query(default=None),
        record_type: str | None = Query(default=None),
    ) -> dict[str, list[dict[str, Any]]]:
        records = store.list_records(
            record_type=record_type,
            keyword=keyword,
            tag=tag,
            genre=genre,
            status=status,
        )
        return {"items": [record.to_dict() for record in records]}

    @application.post("/api/records/{record_type}", status_code=201)
    def create_record(record_type: str, payload: RecordPayload) -> dict[str, Any]:
        record = store.create(record_type, _payload_dict(payload))
        return record.to_dict()

    @application.get("/api/records/{record_type}/{record_id}")
    def get_record(record_type: str, record_id: str) -> dict[str, Any]:
        record = store.get(record_type, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="not found")
        return record.to_dict()

    @application.patch("/api/records/{record_type}/{record_id}")
    def patch_record(
        record_type: str,
        record_id: str,
        payload: RecordPatch,
    ) -> dict[str, Any]:
        try:
            record = store.update(record_type, record_id, _payload_dict(payload))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="not found") from exc
        return record.to_dict()

    @application.delete("/api/records/{record_type}/{record_id}")
    def delete_record(record_type: str, record_id: str) -> dict[str, bool]:
        return {"deleted": store.delete(record_type, record_id)}


def create_app(store: RecordRepository | None = None) -> FastAPI:
    repository = store or create_store()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        repository.initialize()
        yield
        repository.close()

    application = FastAPI(
        title="Read & Watch Tracker",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.store = repository

    @application.exception_handler(ValidationError)
    async def validation_error_handler(_request, exc: ValidationError):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @application.exception_handler(KeyError)
    async def key_error_handler(_request, exc: KeyError):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @application.exception_handler(sqlite3.IntegrityError)
    async def sqlite_integrity_handler(_request, exc: sqlite3.IntegrityError):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @application.exception_handler(psycopg.IntegrityError)
    async def postgres_integrity_handler(_request, exc: psycopg.IntegrityError):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    _register_routes(application, repository)
    return application


app = create_app()


__all__ = [
    "DEMO_SEED_RECORDS",
    "MediaRecord",
    "RecordPayload",
    "RecordPatch",
    "RecordStore",
    "RECORD_TYPES",
    "SqliteRecordStore",
    "ValidationError",
    "app",
    "create_app",
    "create_store",
    "database_backend",
    "health",
    "parse_query_string",
    "postgresql_schema",
    "seed_demo_records",
]
