"""Opt-in real PostgreSQL Phase 12 tests; all fixtures are explicitly rolled back."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from app.core.config import Settings
from app.impact.store import ImpactStore, StaleRca
from app.rca.store import RcaStore


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_IMPACT_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to real PostgreSQL rollback test")


def _connection():
    settings = Settings()
    assert settings.database_url, "A configured database is required"
    try:
        return psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10,
                               options="-c statement_timeout=10000 -c lock_timeout=5000", prepare_threshold=None)
    except psycopg.Error:
        pytest.fail("Configured PostgreSQL endpoint is unavailable", pytrace=False)


def _fixture(conn, *, with_event=True):
    name = f"phase12-{uuid4().hex[:12]}"
    observed = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=2)
    device_ids = [row[0] for row in conn.execute(
        "INSERT INTO public.devices (name,device_type,status) "
        "VALUES (%s,'SWITCH','HEALTHY'),(%s,'HOST','HEALTHY') RETURNING id", (name, name + "-host")).fetchall()]
    link_id = conn.execute("INSERT INTO public.links (source_device_id,destination_device_id,status) "
                           "VALUES (%s,%s,'DOWN') RETURNING id", device_ids).fetchone()[0]
    service_id = conn.execute("INSERT INTO public.services (name,service_type,status) "
                              "VALUES (%s,'HTTP','UP') RETURNING id", (name + "-http",)).fetchone()[0]
    conn.execute("INSERT INTO public.device_services (device_id,service_id,status) VALUES (%s,%s,'UP')",
                 (device_ids[1], service_id))
    incident_id = conn.execute("INSERT INTO public.incidents (title,severity,status,start_time) "
                               "VALUES (%s,'HIGH','DETECTED',%s) RETURNING id",
                               (name, observed)).fetchone()[0]
    event_id = None
    if with_event:
        event_id = conn.execute("INSERT INTO public.events "
                                "(link_id,event_type,severity,status,timestamp,message,metadata) "
                                "VALUES (%s,'LINK_FAILURE','HIGH','DETECTED',%s,'Simulated link failure',%s) RETURNING id",
                                (link_id, observed, Jsonb({"source": "operator", "dedup_key": name + "-event"}))).fetchone()[0]
        conn.execute("INSERT INTO public.incident_events "
                     "(incident_id,event_id,sequence_number,relationship_type) VALUES (%s,%s,1,'SEED')",
                     (incident_id, event_id))
    return incident_id, link_id, service_id, event_id


def _stores(monkeypatch, conn):
    @contextmanager
    def same_transaction(_settings):
        yield conn

    monkeypatch.setattr("app.rca.store.transaction", same_transaction)
    monkeypatch.setattr("app.impact.store.transaction", same_transaction)
    settings = Settings(rca_writes_enabled=True, impact_writes_enabled=True)
    return RcaStore(settings), ImpactStore(settings)


def test_real_assessed_idempotency_stale_input_and_rollback(monkeypatch):
    with _connection() as conn:
        incident_id, link_id, service_id, event_id = _fixture(conn)
        rca_store, impact_store = _stores(monkeypatch, conn)
        rca = rca_store.analyze(incident_id)
        first = impact_store.analyze(incident_id)
        assert first.rca_run_id == rca.id and first.status == "ASSESSED"
        assert first.result.candidate_target_id == link_id
        assert any(e.id == service_id and e.classification == "POTENTIAL" for e in first.result.entities)
        assert any(ref.source_id == event_id for e in first.result.entities for ref in e.evidence)
        assert impact_store.analyze(incident_id).id == first.id
        assert impact_store.latest(incident_id).id == first.id
        assert conn.execute("SELECT count(*) FROM public.impact_runs WHERE rca_run_id=%s",
                            (rca.id,)).fetchone()[0] == 1
        conn.execute("UPDATE public.links SET status='UP' WHERE id=%s", (link_id,))
        with pytest.raises(StaleRca):
            impact_store.analyze(incident_id)
        assert conn.execute("SELECT count(*) FROM public.impact_runs WHERE rca_run_id=%s",
                            (rca.id,)).fetchone()[0] == 1
        conn.rollback()
        assert conn.execute("SELECT 1 FROM public.impact_runs WHERE id=%s", (first.id,)).fetchone() is None
        assert conn.execute("SELECT 1 FROM public.incidents WHERE id=%s", (incident_id,)).fetchone() is None


def test_real_inconclusive_run_is_persisted_without_fabricated_impact(monkeypatch):
    with _connection() as conn:
        incident_id, _, _, _ = _fixture(conn, with_event=False)
        rca_store, impact_store = _stores(monkeypatch, conn)
        assert rca_store.analyze(incident_id).status == "INCONCLUSIVE"
        run = impact_store.analyze(incident_id)
        assert run.status == "INCONCLUSIVE" and run.result.entities == []
        assert run.result.chain == [] and run.result.affected_devices == 0
        assert run.result.user_application_impact == "UNKNOWN_UNVERIFIED"
        conn.rollback()
        assert conn.execute("SELECT 1 FROM public.impact_runs WHERE id=%s", (run.id,)).fetchone() is None


def test_real_constraint_failure_and_transaction_rollback():
    with _connection() as conn:
        incident_id, _, _, _ = _fixture(conn, with_event=False)
        with pytest.raises(psycopg.Error):
            conn.execute("INSERT INTO public.impact_runs "
                         "(rca_run_id,analysis_version,input_fingerprint,topology_fingerprint,status,result) "
                         "VALUES (%s,'IMPACT_RULES_V1',%s,%s,'INVALID',%s)",
                         (uuid4(), "f" * 64, "e" * 64, Jsonb({})))
        conn.rollback()
        assert conn.execute("SELECT 1 FROM public.incidents WHERE id=%s", (incident_id,)).fetchone() is None
