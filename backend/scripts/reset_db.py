"""Reset database schema and demo data.

SQLite (local, no Docker): deletes the db file; restart the API to migrate + seed.
PostgreSQL (Docker / production): drops all tables and re-runs Alembic migrations; restart to seed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import DATA_DIR, DATABASE_URL, is_sqlite, reset_schema  # noqa: E402


def main() -> None:
    if is_sqlite():
        db_path = DATA_DIR / "pocp.db"
        if db_path.exists():
            db_path.unlink()
            print(f"Removed SQLite database: {db_path}")
        else:
            print(f"No SQLite database at {db_path}")
        print("Restart the API to apply migrations and seed demo data.")
        return

    print(f"Resetting PostgreSQL schema ({DATABASE_URL.split('@')[-1]})...")
    reset_schema()
    print("Schema reset complete. Restart the API to seed demo data.")


if __name__ == "__main__":
    main()
