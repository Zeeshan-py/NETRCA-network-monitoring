"""Opt-in, read-only catalog verification of live PostgreSQL access controls."""
import os
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.db.connection import transaction


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_SECURITY_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to live PostgreSQL catalog checks")


TABLES = (
    "devices", "links", "services", "device_services", "metrics", "logs", "events",
    "anomalies", "incidents", "incident_events", "incident_anomalies", "root_causes",
    "root_cause_evidence", "impact_records", "recommendations", "ai_analyses",
    "fault_injections", "topology_snapshots", "rca_runs", "impact_runs",
)


def test_live_client_roles_cannot_access_operational_tables_or_create_public_objects():
    with transaction(Settings()) as connection:
        role_names = {row[0] for row in connection.execute(
            "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)",
            (["anon", "authenticated", "service_role"],))}
        assert role_names == {"anon", "authenticated", "service_role"}
        for table in TABLES:
            row = connection.execute(
                "SELECT c.relrowsecurity, "
                "has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE'), "
                "has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE'), "
                "has_table_privilege('service_role',c.oid,'SELECT,INSERT,UPDATE,DELETE') "
                "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=%s AND c.relkind='r'", (table,)).fetchone()
            assert row is not None, f"Expected public.{table} to exist"
            assert row == (True, False, False, True), f"Unexpected access policy on public.{table}"
        assert connection.execute(
            "SELECT has_schema_privilege('anon','public','CREATE'), "
            "has_schema_privilege('authenticated','public','CREATE')").fetchone() == (False, False)


def test_backend_transaction_downgrades_to_table_scoped_service_role():
    with transaction(Settings()) as connection:
        assert connection.execute("SELECT current_user").fetchone()[0] == "service_role"
        assert connection.execute(
            "SELECT rolsuper,rolcreaterole,rolcreatedb,rolbypassrls "
            "FROM pg_roles WHERE rolname=current_user").fetchone() == (False, False, False, True)
        assert connection.execute(
            "SELECT has_schema_privilege(current_user,'public','CREATE')").fetchone()[0] is False


def test_service_role_write_is_limited_to_existing_tables_and_rolls_back():
    name = f"phase14-role-{uuid4().hex}"

    class RollbackFixture(Exception):
        pass

    with pytest.raises(RollbackFixture):
        with transaction(Settings()) as connection:
            connection.execute(
                "INSERT INTO public.devices (name,device_type,status) VALUES (%s,'HOST','HEALTHY')",
                (name,))
            raise RollbackFixture
    with transaction(Settings()) as connection:
        assert connection.execute(
            "SELECT count(*) FROM public.devices WHERE name=%s", (name,)).fetchone()[0] == 0


def test_security_definer_event_trigger_is_not_a_callable_client_function():
    with transaction(Settings()) as connection:
        row = connection.execute(
            "SELECT p.prorettype::regtype::text, EXISTS (SELECT 1 FROM pg_event_trigger e "
            "WHERE e.evtfoid=p.oid) AS is_event_trigger "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='public' AND p.proname='rls_auto_enable'").fetchone()
        assert row == ("event_trigger", True)
