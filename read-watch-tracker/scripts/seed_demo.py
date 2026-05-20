from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factory import create_store  # noqa: E402
from domain import seed_demo_records  # noqa: E402


def main() -> int:
    store = create_store()
    store.initialize()
    inserted = seed_demo_records(store)
    store.close()
    target = getattr(store, "db_path", None) or getattr(store, "dsn", "database")
    print(f"Seeded {inserted} demo records into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
