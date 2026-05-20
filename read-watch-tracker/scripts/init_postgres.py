from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postgres_store import PostgresRecordStore  # noqa: E402


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("Set DATABASE_URL before running init_postgres.py", file=sys.stderr)
        return 1
    store = PostgresRecordStore(dsn=dsn)
    store.initialize()
    store.close()
    print(f"PostgreSQL schema initialized: {dsn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
