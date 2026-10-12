"""Apply demo data only to an explicitly configured loopback development database."""
import os
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict


def main() -> int:
    dsn = os.environ.get("NETRCA_LOCAL_DATABASE_URL", "")
    try:
        info = conninfo_to_dict(dsn)
        # Do not load backend/.env: it may point to the real linked project.
        if not dsn or info.get("host") not in {"localhost", "127.0.0.1", "::1"} or info.get("hostaddr"):
            print("Set NETRCA_LOCAL_DATABASE_URL to a loopback development database. Remote seeds are refused.")
            return 1
        loopback = "::1" if info["host"] == "::1" else "127.0.0.1"
        with psycopg.connect(dsn, hostaddr=loopback, connect_timeout=10) as connection:
            connection.execute(Path(__file__).with_name("seeds").joinpath("development_seed.sql").read_text())
        print("Development fixtures applied to the local database.")
        return 0
    except psycopg.Error:
        print("Seed failed; transaction rolled back. Check local connection and migrations.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
