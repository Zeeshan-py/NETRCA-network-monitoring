from unittest.mock import MagicMock, patch

import psycopg
import pytest

from app.core.config import Settings
from app.db.connection import DatabaseUnavailable, check_connection, transaction


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_configuration_does_not_connect(value):
    with patch("app.db.connection.psycopg.connect") as connect:
        with pytest.raises(DatabaseUnavailable, match="not configured"):
            check_connection(Settings(_env_file=None, DATABASE_URL=value))
        connect.assert_not_called()


def test_connection_failure_is_sanitized():
    with patch("app.db.connection.psycopg.connect", side_effect=psycopg.OperationalError("secret-password")):
        with pytest.raises(DatabaseUnavailable) as error:
            check_connection(Settings(_env_file=None, DATABASE_URL="postgresql://secret-password"))
        assert "secret-password" not in str(error.value)


def test_query_failure_is_sanitized_and_context_is_closed():
    context = MagicMock()
    context.__exit__.return_value = False
    context.__enter__.return_value.execute.side_effect = psycopg.ProgrammingError("sensitive SQL")
    with patch("app.db.connection.psycopg.connect", return_value=context):
        with pytest.raises(DatabaseUnavailable, match="operation failed"):
            with transaction(Settings(_env_file=None, DATABASE_URL="postgresql://localhost/test")) as connection:
                connection.execute("SELECT 1")
    assert context.__exit__.call_args.args[0] is psycopg.ProgrammingError


def test_connection_check_uses_real_query_and_masks_settings():
    settings = Settings(_env_file=None, DATABASE_URL="postgresql://user:secret-password@localhost/test")
    assert "secret-password" not in repr(settings)
    context = MagicMock()
    context.__enter__.return_value.execute.return_value.fetchone.return_value = (1,)
    with patch("app.db.connection.psycopg.connect", return_value=context):
        assert check_connection(settings)
    context.__enter__.return_value.execute.assert_called_once_with("SELECT 1")
