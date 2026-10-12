"""Explicit connection diagnostic: python -m app.db.check (from backend/)."""
from app.core.config import get_settings
from app.db.connection import DatabaseUnavailable, check_connection


def main() -> int:
    try:
        if check_connection(get_settings()):
            print("Database connection: UP")
            return 0
    except DatabaseUnavailable as error:
        print(str(error))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
