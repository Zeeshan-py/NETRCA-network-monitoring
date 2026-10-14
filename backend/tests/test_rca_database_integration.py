"""Opt-in real PostgreSQL checks; every fixture and RCA run is rolled back."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from app.core.config import Settings
from app.rca.store import RcaStore


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_RCA_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to real PostgreSQL rollback test")


def _connection():
    settings = Settings()
    assert settings.database_url, "A configured database is required"
    try:
        return psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10,
                               options="-c statement_timeout=10000 -c lock_timeout=5000", prepare_threshold=None)
    except psycopg.Error:
        pytest.fail("Configured PostgreSQL endpoint is unavailable", pytrace=False)


def test_real_evidence_idempotency_latest_and_full_rollback(monkeypatch):
    settings = Settings(rca_writes_enabled=True)
    connection = _connection()
    with connection:
        @contextmanager
        def same_transaction(_settings):
            yield connection

        monkeypatch.setattr("app.rca.store.transaction", same_transaction)
        name = f"phase11-{uuid4().hex[:12]}"
        observed = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=2)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.devices (name,device_type,status) "
                           "VALUES (%s,'SWITCH','HEALTHY'),(%s,'HOST','HEALTHY') RETURNING id", (name, name + "-host"))
            device_ids = [row[0] for row in cursor.fetchall()]
            cursor.execute("INSERT INTO public.links (source_device_id,destination_device_id,status) "
                           "VALUES (%s,%s,'DOWN') RETURNING id", device_ids)
            link_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.events "
                           "(link_id,event_type,severity,status,timestamp,message,metadata) "
                           "VALUES (%s,'LINK_FAILURE','HIGH','DETECTED',%s,'Simulated link failure',%s) RETURNING id",
                           (link_id, observed, Jsonb({"source": "operator", "dedup_key": name + "-event"})))
            event_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.metrics (link_id,metric_type,value,unit,timestamp,metadata) "
                           "VALUES (%s,'LINK_STATE',0,'state',%s,%s) RETURNING id",
                           (link_id, observed + timedelta(seconds=1),
                            Jsonb({"source": "manual", "observation_key": name + "-metric"})))
            metric_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.anomalies "
                           "(metric_id,model_name,anomaly_score,is_anomaly,severity,detected_at,metadata) "
                           "VALUES (%s,'NETRCA_THRESHOLD',1,true,'HIGH',%s,%s) RETURNING id",
                           (metric_id, observed + timedelta(seconds=2),
                            Jsonb({"observed_at": (observed + timedelta(seconds=1)).isoformat()})))
            anomaly_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.incidents (title,severity,status,start_time) "
                           "VALUES ('Phase 11 rollback test','HIGH','DETECTED',%s) RETURNING id", (observed,))
            incident_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.incident_events "
                           "(incident_id,event_id,sequence_number,relationship_type) VALUES (%s,%s,1,'SEED')",
                           (incident_id, event_id))
            cursor.execute("INSERT INTO public.incident_anomalies "
                           "(incident_id,anomaly_id,relationship_type) VALUES (%s,%s,'SAME_LINK')",
                           (incident_id, anomaly_id))
        store = RcaStore(settings)
        first = store.analyze(incident_id)
        assert first.status == "CANDIDATES"
        assert first.result.candidates[0].target_id == link_id
        assert {(ref.source_type, ref.source_id) for ref in first.result.candidates[0].supporting_evidence} >= {
            ("EVENT", event_id), ("ANOMALY", anomaly_id)}
        second = store.analyze(incident_id)
        assert second.id == first.id and second.input_fingerprint == first.input_fingerprint
        assert store.latest(incident_id).id == first.id
        assert connection.execute("SELECT count(*) FROM public.rca_runs WHERE incident_id=%s",
                                  (incident_id,)).fetchone()[0] == 1
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.events "
                           "(device_id,event_type,severity,status,timestamp,message,metadata) "
                           "VALUES (%s,'PROBE_FAILED','HIGH','DETECTED',%s,'Simulated probe failure',%s) RETURNING id",
                           (device_ids[1], observed + timedelta(seconds=3),
                            Jsonb({"source": "operator", "dedup_key": name + "-probe"})))
            probe_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.incident_events "
                           "(incident_id,event_id,sequence_number,relationship_type) VALUES (%s,%s,2,'KNOWN_LINK_ENDPOINT')",
                           (incident_id, probe_id))
        changed = store.analyze(incident_id)
        assert changed.id != first.id and changed.result.candidates[0].score > first.result.candidates[0].score
        assert store.latest(incident_id).id == changed.id
        connection.rollback()
        assert connection.execute("SELECT 1 FROM public.rca_runs WHERE id=%s", (first.id,)).fetchone() is None
        assert connection.execute("SELECT 1 FROM public.incidents WHERE id=%s", (incident_id,)).fetchone() is None


def test_real_constraint_failure_rolls_back_incident():
    connection = _connection()
    with connection:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        incident_id = connection.execute(
            "INSERT INTO public.incidents (title,severity,status,start_time) "
            "VALUES ('Phase 11 constraint rollback','LOW','DETECTED',%s) RETURNING id", (now,)).fetchone()[0]
        with pytest.raises(psycopg.Error):
            connection.execute("INSERT INTO public.rca_runs "
                               "(incident_id,analysis_version,input_fingerprint,status,result) "
                               "VALUES (%s,'RULES_V1',%s,'INVALID',%s)",
                               (incident_id, "f" * 64, Jsonb({})))
        connection.rollback()
        assert connection.execute("SELECT 1 FROM public.incidents WHERE id=%s", (incident_id,)).fetchone() is None


def test_real_inconclusive_run_skips_invalid_stored_event_and_rolls_back(monkeypatch):
    connection = _connection()
    with connection:
        @contextmanager
        def same_transaction(_settings):
            yield connection

        monkeypatch.setattr("app.rca.store.transaction", same_transaction)
        now = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=1)
        incident_id = connection.execute(
            "INSERT INTO public.incidents (title,severity,status,start_time) "
            "VALUES ('Phase 11 inconclusive rollback','LOW','DETECTED',%s) RETURNING id", (now,)).fetchone()[0]
        event_id = connection.execute(
            "INSERT INTO public.events (event_type,severity,status,timestamp,message) "
            "VALUES ('PROBE_FAILED','LOW','DETECTED',%s,'Unvalidated fixture') RETURNING id", (now,)).fetchone()[0]
        connection.execute("INSERT INTO public.incident_events "
                           "(incident_id,event_id,sequence_number,relationship_type) VALUES (%s,%s,1,'SEED')",
                           (incident_id, event_id))
        store = RcaStore(Settings())
        first = store.analyze(incident_id)
        assert first.status == "INCONCLUSIVE" and first.result.candidates == []
        assert "INVALID_INCIDENT_EVIDENCE_SKIPPED" in first.result.limitations
        assert store.analyze(incident_id).id == first.id
        assert store.latest(incident_id).id == first.id
        connection.rollback()
        assert connection.execute("SELECT 1 FROM public.rca_runs WHERE id=%s", (first.id,)).fetchone() is None


def test_advisory_lock_serializes_parallel_analysis_transactions():
    first, second = _connection(), _connection()
    with first, second:
        first.execute("SELECT pg_advisory_xact_lock(47301, 11)")
        assert second.execute("SELECT pg_try_advisory_xact_lock(47301, 11)").fetchone()[0] is False
        first.rollback()
        assert second.execute("SELECT pg_try_advisory_xact_lock(47301, 11)").fetchone()[0] is True
        second.rollback()
