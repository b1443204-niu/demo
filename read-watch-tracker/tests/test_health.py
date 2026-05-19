from __future__ import annotations

from app import health


def test_health_ok() -> None:
    assert health() == {"status": "ok", "service": "read-watch-tracker"}
