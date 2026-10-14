"""Opt-in real PostgreSQL test. Every inserted Phase 6/8/9 row is rolled back."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest

from app.anomaly.engine import detect
from app.anomaly.store import AnomalyStore
from app.core.config import Settings
from app.correlation.models import CorrelationRequest
from app.correlation.store import IncidentStore
from app.pipeline.models import EventIn, MetricIn
from app.pipeline.store import EvidenceStore


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_CORRELATION_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to real PostgreSQL rollback test")


def test_phase6_phase8_incident_grouping_reuse_idempotency_and_rollback(monkeypatch):
    settings = Settings(correlation_writes_enabled=True)
    assert settings.database_url, "A configured database is required"
    try:
        connection = psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10)
    except psycopg.Error:
        pytest.fail("Configured PostgreSQL endpoint is unavailable", pytrace=False)
    with connection:
        @contextmanager
        def same_transaction(_settings):
            yield connection

        monkeypatch.setattr("app.pipeline.store.transaction", same_transaction)
        monkeypatch.setattr("app.anomaly.store.transaction", same_transaction)
        monkeypatch.setattr("app.correlation.store.transaction", same_transaction)
        name = f"phase9-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.devices (name,device_type,status) VALUES (%s,'HOST','HEALTHY') RETURNING id", (name,))
            device_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.devices (name,device_type,status) VALUES (%s,'HOST','HEALTHY') RETURNING id", (name + "-other",))
            other_id = cursor.fetchone()[0]
        pipeline = EvidenceStore(settings)
        first = EventIn(device_id=device_id, event_type="DEVICE_UNAVAILABLE", severity="MEDIUM",
                        source="operator", timestamp=now - timedelta(seconds=60),
                        dedup_key=f"phase9:{name}:first", message="Simulated host failure")
        pipeline.ingest_event(first)
        first_id = connection.execute("SELECT id FROM public.events WHERE metadata->>'dedup_key'=%s",
                                      (first.dedup_key,)).fetchone()[0]
        metric = MetricIn(device_id=device_id, metric_type="LATENCY", value=300, unit="ms",
                          timestamp=now - timedelta(seconds=30), source="manual",
                          observation_key=f"phase9:{name}:metric")
        pipeline.ingest_metrics([metric])
        metric_id = connection.execute("SELECT id FROM public.metrics WHERE metadata->>'observation_key'=%s",
                                       (metric.observation_key,)).fetchone()[0]
        finding = detect(metric, [], settings, metric_id=metric_id)
        assert finding.status == "ANOMALY"
        anomaly_id, created = AnomalyStore(settings).save(finding)
        assert created
        store = IncidentStore(settings)
        request = CorrelationRequest(event_ids=[first_id], anomaly_ids=[anomaly_id])
        result = store.correlate(request)
        assert result["created"] == 1 and result["attached"] == 2
        incident_id = result["incidents"][0]["incident_id"]
        assert store.correlate(request)["created"] == 0
        assert store.correlate(request)["attached"] == 0
        second = EventIn(device_id=device_id, event_type="PROBE_FAILED", severity="HIGH",
                         source="operator", timestamp=now, dedup_key=f"phase9:{name}:second",
                         message="Simulated probe failure")
        pipeline.ingest_event(second)
        second_id = connection.execute("SELECT id FROM public.events WHERE metadata->>'dedup_key'=%s",
                                       (second.dedup_key,)).fetchone()[0]
        reuse = store.correlate(CorrelationRequest(event_ids=[second_id]))
        assert reuse["created"] == 0 and reuse["incidents"][0]["incident_id"] == incident_id
        detail = store.get(incident_id)
        assert detail["severity"] == "HIGH" and detail["status"] == "DETECTED"
        assert {row["id"] for row in detail["events"]} == {first_id, second_id}
        assert detail["anomalies"][0]["id"] == anomaly_id
        assert all(row["relationship_type"] for row in detail["events"] + detail["anomalies"])
        other = EventIn(device_id=other_id, event_type="DEVICE_UNAVAILABLE", severity="LOW",
                        source="operator", timestamp=now, dedup_key=f"phase9:{name}:other",
                        message="Independent simulated host failure")
        pipeline.ingest_event(other)
        other_event_id = connection.execute("SELECT id FROM public.events WHERE metadata->>'dedup_key'=%s",
                                            (other.dedup_key,)).fetchone()[0]
        separate = store.correlate(CorrelationRequest(event_ids=[other_event_id]))
        assert separate["created"] == 1 and separate["incidents"][0]["incident_id"] != incident_id
        assert store.list(page=1, limit=1, status="DETECTED", severity=None)["pagination"]["total"] >= 2
        connection.rollback()
        assert connection.execute("SELECT 1 FROM public.incidents WHERE id=%s", (incident_id,)).fetchone() is None
        assert connection.execute("SELECT 1 FROM public.incident_anomalies WHERE anomaly_id=%s", (anomaly_id,)).fetchone() is None


def test_real_foreign_key_failure_rolls_back_incident_and_membership():
    settings = Settings(correlation_writes_enabled=True)
    assert settings.database_url
    try:
        connection = psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10)
    except psycopg.Error:
        pytest.fail("Configured PostgreSQL endpoint is unavailable", pytrace=False)
    with connection:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.incidents (title,severity,status,start_time) "
                           "VALUES ('Rollback probe','LOW','DETECTED',%s) RETURNING id", (now,))
            incident_id = cursor.fetchone()[0]
        with pytest.raises(psycopg.Error):
            connection.execute("INSERT INTO public.incident_events "
                               "(incident_id,event_id,sequence_number,relationship_type) "
                               "VALUES (%s,%s,1,'SEED')", (incident_id, uuid4()))
        connection.rollback()
        assert connection.execute("SELECT 1 FROM public.incidents WHERE id=%s", (incident_id,)).fetchone() is None


def test_transaction_advisory_lock_blocks_parallel_writer():
    settings = Settings()
    assert settings.database_url
    try:
        first = psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10)
        second = psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10)
    except psycopg.Error:
        pytest.fail("Configured PostgreSQL endpoint is unavailable", pytrace=False)
    with first, second:
        first.execute("SELECT pg_advisory_xact_lock(47301, 9)")
        assert second.execute("SELECT pg_try_advisory_xact_lock(47301, 9)").fetchone()[0] is False
        first.rollback()
        assert second.execute("SELECT pg_try_advisory_xact_lock(47301, 9)").fetchone()[0] is True
        second.rollback()
