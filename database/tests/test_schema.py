"""Opt-in integration suite. DDL/fixtures/test writes ALWAYS roll back.

Run from the repository root using backend/.venv/Scripts/python.exe -m pytest
database/tests -q. Set NETRCA_RUN_DATABASE_TESTS=1 first; see database/README.md.
"""
import os
from pathlib import Path
import re
import sys
from uuid import uuid5, NAMESPACE_URL, uuid4

import psycopg
from psycopg import sql
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import Settings

TABLES = "devices links services device_services metrics logs events anomalies incidents incident_events root_causes root_cause_evidence impact_records recommendations ai_analyses fault_injections topology_snapshots".split()
pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_DATABASE_TESTS") != "1", reason="Explicit database test opt-in required")


def demo_id(name):
    return uuid5(NAMESPACE_URL, "netrca:phase2:demo:" + name)


@pytest.fixture(scope="session")
def database():
    settings = Settings()
    if not settings.database_url:
        pytest.fail("DATABASE_URL is required", pytrace=False)
    try:
        connection = psycopg.connect(settings.database_url.get_secret_value(), connect_timeout=15, sslmode="require", prepare_threshold=None, options="-c statement_timeout=15000 -c lock_timeout=5000")
    except psycopg.Error:
        pytest.fail("Database connection failed (details suppressed)", pytrace=False)
    try:
        if os.environ.get("NETRCA_TEST_INITIAL_MIGRATION") == "1":
            for migration in sorted((ROOT / "supabase/migrations").glob("*.sql")):
                connection.execute(migration.read_text())
        connection.execute((ROOT / "database/seeds/development_seed.sql").read_text())
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def db(database):
    with database.transaction(force_rollback=True):
        yield database


@pytest.mark.parametrize("table", TABLES)
def test_erd_columns_primary_keys_and_rls(db, table):
    erd = (ROOT / "Instruction/ERD.md").read_text(encoding="utf-8")
    section = re.search(r"# \d+\. Entity: `" + table + r"`(.*?)(?=\n# \d+\.|\Z)", erd, re.S).group(1)
    expected = set(re.findall(r"^\| `([a-z_]+)` \|", section, re.M))
    columns = dict(db.execute("SELECT column_name, udt_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (table,)).fetchall())
    assert expected <= columns.keys()
    assert columns["id"] == "uuid"
    for name in expected:
        if name.endswith("_at") or name in {"timestamp", "start_time", "end_time", "snapshot_time"}:
            assert columns[name] == "timestamptz"
    assert db.execute("SELECT count(*) FROM pg_constraint WHERE conrelid=%s::regclass AND contype='p'", ("public."+table,)).fetchone()[0] == 1
    assert db.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass", ("public."+table,)).fetchone()[0]
    assert db.execute("SELECT count(*) FROM pg_policy WHERE polrelid=%s::regclass", ("public."+table,)).fetchone()[0] == 0


def test_seed_repeatability_and_evidence_sources(db):
    def counts():
        return [db.execute(sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(t))).fetchone()[0] for t in TABLES]
    before = counts()
    db.execute((ROOT / "database/seeds/development_seed.sql").read_text())
    assert counts() == before
    mapping = {"METRIC":"metrics", "LOG":"logs", "EVENT":"events", "ANOMALY":"anomalies", "TOPOLOGY":"topology_snapshots"}
    for kind, source in db.execute("SELECT source_type, source_id FROM public.root_cause_evidence WHERE root_cause_id=%s", (demo_id("cause"),)).fetchall():
        assert db.execute(sql.SQL("SELECT 1 FROM public.{} WHERE id=%s").format(sql.Identifier(mapping[kind])), (source,)).fetchone()
    timeline = db.execute("SELECT e.event_type FROM public.incident_events ie JOIN public.events e ON e.id=ie.event_id WHERE ie.incident_id=%s ORDER BY ie.sequence_number", (demo_id("incident"),)).fetchall()
    assert timeline == [("INTERFACE_FAILURE",), ("SERVER_TIMEOUT",)]


@pytest.mark.parametrize("query,params,error", [
    ("UPDATE public.devices SET status='INVALID' WHERE id=%s", (demo_id("DEMO-R1"),), psycopg.errors.CheckViolation),
    ("UPDATE public.links SET destination_device_id=source_device_id WHERE id=%s", (demo_id("uplink"),), psycopg.errors.CheckViolation),
    ("UPDATE public.links SET source_device_id=%s WHERE id=%s", (uuid4(),demo_id("uplink")), psycopg.errors.ForeignKeyViolation),
    ("UPDATE public.metrics SET value=101 WHERE id=%s", (demo_id("loss"),), psycopg.errors.CheckViolation),
    ("UPDATE public.metrics SET value='NaN' WHERE id=%s", (demo_id("loss"),), psycopg.errors.CheckViolation),
    ("UPDATE public.metrics SET device_id=NULL,link_id=NULL WHERE id=%s", (demo_id("loss"),), psycopg.errors.CheckViolation),
    ("UPDATE public.logs SET severity='DEBUG' WHERE id=%s", (demo_id("interface-log"),), psycopg.errors.CheckViolation),
    ("UPDATE public.incidents SET status='OPEN' WHERE id=%s", (demo_id("incident"),), psycopg.errors.CheckViolation),
    ("UPDATE public.incidents SET status='CLOSED',end_time=NULL WHERE id=%s", (demo_id("incident"),), psycopg.errors.CheckViolation),
    ("UPDATE public.incidents SET end_time=start_time-interval '1 second' WHERE id=%s", (demo_id("incident"),), psycopg.errors.CheckViolation),
    ("UPDATE public.root_causes SET confidence=1.1 WHERE id=%s", (demo_id("cause"),), psycopg.errors.CheckViolation),
    ("UPDATE public.anomalies SET anomaly_score=-0.1 WHERE id=%s", (demo_id("loss-anomaly"),), psycopg.errors.CheckViolation),
    ("UPDATE public.services SET port=65536 WHERE id=%s", (demo_id("web"),), psycopg.errors.CheckViolation),
    ("UPDATE public.incident_events SET sequence_number=1 WHERE id=%s", (demo_id("timeline-timeout"),), psycopg.errors.UniqueViolation),
    ("DELETE FROM public.devices WHERE id=%s", (demo_id("DEMO-R1"),), psycopg.errors.ForeignKeyViolation),
    ("DELETE FROM public.events WHERE id=%s", (demo_id("failure"),), psycopg.errors.ForeignKeyViolation),
    ("DELETE FROM public.incidents WHERE id=%s", (demo_id("incident"),), psycopg.errors.ForeignKeyViolation),
    ("UPDATE public.fault_injections SET status='COMPLETED',ended_at=NULL WHERE id=%s", (demo_id("fault"),), psycopg.errors.CheckViolation),
])
def test_invalid_data_is_rejected(db, query, params, error):
    with pytest.raises(error):
        with db.transaction():
            db.execute(query, params)


def test_recommendation_cannot_reference_another_incident_cause(db):
    other = db.execute("INSERT INTO public.incidents(title,severity,status,start_time) VALUES ('test','LOW','DETECTED',now()) RETURNING id").fetchone()[0]
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with db.transaction():
            db.execute("UPDATE public.recommendations SET incident_id=%s WHERE id=%s", (other,demo_id("recommendation")))


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_clients_have_no_read_or_write_access(db, role):
    for table in TABLES:
        for privilege in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]:
            assert not db.execute("SELECT has_table_privilege(%s,%s,%s)", (role,"public."+table,privilege)).fetchone()[0]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with db.transaction():
                db.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                db.execute(sql.SQL("SELECT * FROM public.{} LIMIT 1").format(sql.Identifier(table)))


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_rls_still_denies_if_select_is_accidentally_granted(db, role):
    # Transaction-local grant proves RLS itself blocks the populated fixture.
    db.execute(sql.SQL("GRANT SELECT ON public.devices TO {}").format(sql.Identifier(role)))
    db.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
    assert db.execute("SELECT * FROM public.devices").fetchall() == []


def test_updated_at_and_required_query_indexes(db):
    old = db.execute("SELECT updated_at FROM public.devices WHERE id=%s", (demo_id("DEMO-R1"),)).fetchone()[0]
    new = db.execute("UPDATE public.devices SET hostname='demo-router' WHERE id=%s RETURNING updated_at", (demo_id("DEMO-R1"),)).fetchone()[0]
    assert new > old
    definitions = [r[0] for r in db.execute("SELECT indexdef FROM pg_indexes WHERE schemaname='public'").fetchall()]
    for table, columns in [('metrics','(device_id, "timestamp" DESC)'),('metrics','(link_id, "timestamp" DESC)'),('incidents','(status, severity)'),('incident_events','(incident_id, sequence_number)'),('root_cause_evidence','(root_cause_id, source_type, source_id)'),('topology_snapshots','(snapshot_time DESC)')]:
        assert any(' ON public.'+table+' ' in d and columns in d for d in definitions), (table, columns)


def test_all_foreign_keys_restrict_history_deletion(db):
    constraints = db.execute("SELECT conrelid::regclass::text, confdeltype, confupdtype FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace").fetchall()
    for table in set(TABLES) - {'devices','services','topology_snapshots','incidents'}:
        assert any(c[0] == table for c in constraints)
    assert all(c[1:] == ('r','r') for c in constraints if c[0] in TABLES)
