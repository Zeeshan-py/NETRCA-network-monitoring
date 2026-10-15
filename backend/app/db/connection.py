from contextlib import contextmanager
from collections.abc import Iterator

import psycopg

from app.core.config import Settings


class DatabaseUnavailable(RuntimeError):
    """Safe public error; never includes a DSN or database server details."""


@contextmanager
def transaction(settings: Settings, *, read_only: bool = False) -> Iterator[psycopg.Connection]:
    """One bounded transaction; commit on success, rollback on failure, always close.

    SQL callers must use parameters for values and psycopg.sql for identifiers.
    The configured database role determines privileges; no end-user JWT is applied.
    """
    if not settings.database_url or not settings.database_url.get_secret_value().strip():
        raise DatabaseUnavailable("Database is not configured")
    try:
        with psycopg.connect(
            settings.database_url.get_secret_value(),
            connect_timeout=10,
            sslmode="require",
            application_name="netrca_backend",
            options="-c statement_timeout=10000 -c lock_timeout=5000",
            prepare_threshold=None,
        ) as connection:
            if read_only:
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            # The configured Supabase login is an administrative role. Restrict
            # application SQL to the existing table-scoped service role.
            connection.execute("SET LOCAL ROLE service_role")
            yield connection
    except psycopg.Error:
        raise DatabaseUnavailable("Database operation failed") from None


def check_connection(settings: Settings) -> bool:
    with transaction(settings) as connection:
        return connection.execute("SELECT 1").fetchone() == (1,)
