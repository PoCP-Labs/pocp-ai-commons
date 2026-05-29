"""Delete the local SQLite database so the next API start re-seeds demo data."""

from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pocp.db"


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed {DB_PATH}")
    else:
        print(f"No database at {DB_PATH}")


if __name__ == "__main__":
    main()
