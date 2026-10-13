"""Opt-in real PostgreSQL evidence checks; writes are rolled back."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.monitoring.models import DeviceReading, InterfaceReading, LinkReading, MonitoringSnapshot, ProbeReading
from app.pipeline.models import EventIn, LogIn, MetricIn
from app.pipeline.store import EvidenceConflict, EvidenceStore


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_PIPELINE_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to real database rollback test")


def test_real_database_metrics_logs_events_dedup_pagination_and_rollback(monkeypatch):
    settings = Settings()
    assert settings.database_url, "Database URL required for opt-in test"
    store = EvidenceStore(settings)
    name1, name2 = f"phase6-{uuid4().hex[:12]}", f"phase6-{uuid4().hex[:12]}"
    first = datetime.now(timezone.utc) - timedelta(minutes=2)
    with psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10) as connection:
        @contextmanager
        def same_transaction(_settings):
            yield connection

        monkeypatch.setattr("app.pipeline.store.transaction", same_transaction)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.devices (name, device_type, status) VALUES (%s,'HOST','HEALTHY') RETURNING id", (name1,))
            device1 = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.devices (name, device_type, status) VALUES (%s,'HOST','HEALTHY') RETURNING id", (name2,))
            device2 = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.links (source_device_id, destination_device_id, status, "
                           "interface_source, interface_destination) VALUES (%s,%s,'UP','eth0','eth0') RETURNING id",
                           (device1, device2))
            link_id = cursor.fetchone()[0]

        metric = MetricIn(device_id=device1, metric_type="RX_BYTES", value=0, unit="bytes",
                          timestamp=first, source="manual", observation_key=f"unit:{uuid4().hex}", interface="eth0")
        assert store.ingest_metrics([metric]) == {"inserted": 1, "duplicates": 0}
        assert store.ingest_metrics([metric]) == {"inserted": 0, "duplicates": 1}
        with pytest.raises(EvidenceConflict, match="OBSERVATION_KEY_CONFLICT"):
            store.ingest_metrics([metric.model_copy(update={"value": 9})])
        with pytest.raises(EvidenceConflict, match="DEVICE_NOT_FOUND"):
            store.ingest_metrics([metric.model_copy(update={"device_id": uuid4()})])
        assert store.list_records("metrics", page=1, limit=1, device_id=device1)["pagination"]["total"] == 1

        log = LogIn(device_id=device1, severity="ERROR", source="netrca", message="Read operation failed",
                    timestamp=first, observation_key=f"log:{uuid4().hex}")
        assert store.ingest_log(log)["inserted"] == 1
        assert store.ingest_log(log)["duplicates"] == 1
        with pytest.raises(EvidenceConflict, match="OBSERVATION_KEY_CONFLICT"):
            store.ingest_log(log.model_copy(update={"message": "Different message"}))
        event = EventIn(device_id=device1, event_type="PROBE_FAILED", severity="MEDIUM",
                        source="netrca", timestamp=first, dedup_key=f"probe:{uuid4().hex}",
                        message="Host unreachable")
        assert store.ingest_event(event)["inserted"] == 1
        assert store.ingest_event(event)["duplicates"] == 1
        with pytest.raises(EvidenceConflict, match="EVENT_KEY_CONFLICT"):
            store.ingest_event(event.model_copy(update={"message": "Different event"}))
        assert store.list_records("logs", page=1, limit=1, device_id=device1)["pagination"]["total"] == 1
        assert store.list_records("events", page=1, limit=1, device_id=device1)["pagination"]["total"] == 1

        def snapshot(when, status, rx):
            return MonitoringSnapshot(observed_at=when, topology_name="phase6-test", network_state="RUNNING",
                collection_status="COMPLETE", errors=[], links=[], devices=[DeviceReading(name=name1,
                    device_type="HOST", interfaces=[InterfaceReading(name="eth0", status=status,
                        rx_bytes=rx, tx_bytes=None, rx_packets=0, tx_packets=None, rx_errors=None, tx_errors=None)])])

        with pytest.raises(EvidenceConflict, match="INVALID_OBSERVATION"):
            store.ingest_snapshot(MonitoringSnapshot(observed_at=first, topology_name="phase6-test",
                network_state="RUNNING", collection_status="COMPLETE", errors=[], links=[], devices=[]))
        up = store.ingest_snapshot(snapshot(first + timedelta(seconds=1), "UP", 0))
        assert up == {"metrics": 3, "events": 0, "duplicates": 0, "unmapped_links": 0}
        assert store.ingest_snapshot(snapshot(first + timedelta(seconds=1), "UP", 0))["duplicates"] == 3
        down = store.ingest_snapshot(snapshot(first + timedelta(seconds=2), "DOWN", 2))
        assert down["events"] == 1
        assert store.ingest_snapshot(snapshot(first + timedelta(seconds=3), "DOWN", 3))["events"] == 0
        store.ingest_snapshot(snapshot(first + timedelta(seconds=4), "UP", 4))
        partial = MonitoringSnapshot(observed_at=first + timedelta(seconds=5), topology_name="phase6-test",
            network_state="RUNNING", collection_status="PARTIAL", errors=["eth0:INTERFACE_MISSING"],
            links=[], devices=[DeviceReading(name=name1, device_type="HOST", interfaces=[
                InterfaceReading(name="eth0", status="UNAVAILABLE", error_code="INTERFACE_MISSING")])])
        assert store.ingest_snapshot(partial) == {"metrics": 0, "events": 1, "duplicates": 0, "unmapped_links": 0}
        assert store.ingest_snapshot(partial)["events"] == 0
        store.ingest_snapshot(snapshot(first + timedelta(seconds=6), "UP", 4))
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM public.events WHERE event_type='INTERFACE_FAILURE' AND device_id=%s", (device1,))
            assert cursor.fetchone()[0] == "RESOLVED"
            cursor.execute("SELECT status FROM public.events WHERE event_type='COLLECTION_FAILURE'")
            assert cursor.fetchone()[0] == "RESOLVED"

        probe = ProbeReading(observed_at=first + timedelta(seconds=7), source=name1, destination=name2,
                             packets_sent=2, packets_received=0, packet_loss_percent=100,
                             status="UNREACHABLE")
        result = store.ingest_probe(probe)
        assert result["metrics"] == 2 and result["events"] == 1
        assert store.ingest_probe(probe)["events"] == 0
        timeout = ProbeReading(observed_at=first + timedelta(seconds=8), source=name1, destination=name2,
                               status="TIMEOUT", error_code="COMMAND_TIMEOUT")
        assert store.ingest_probe(timeout) == {"metrics": 0, "events": 1, "duplicates": 0}
        assert store.ingest_probe(timeout)["events"] == 0
        assert store.ingest_probe(ProbeReading(observed_at=first + timedelta(seconds=9), source=name1,
            destination=name2, packets_sent=2, packets_received=2, packet_loss_percent=0,
            latency_ms=1.25, status="REACHABLE"))["metrics"] == 3

        def link_snapshot(when, status):
            return MonitoringSnapshot(observed_at=when, topology_name="phase6-test", network_state="RUNNING",
                collection_status="COMPLETE", errors=[], devices=[
                    DeviceReading(name=name1, device_type="HOST", interfaces=[
                        InterfaceReading(name="eth0", status="UP")]),
                    DeviceReading(name=name2, device_type="HOST", interfaces=[
                        InterfaceReading(name="eth0", status=status)])],
                links=[LinkReading(source=name1, destination=name2, interface_source="eth0",
                                   interface_destination="eth0", status=status)])
        assert store.ingest_snapshot(link_snapshot(first + timedelta(seconds=10), "UP"))["unmapped_links"] == 0
        assert store.ingest_snapshot(link_snapshot(first + timedelta(seconds=11), "DOWN"))["events"] == 2
        assert store.ingest_snapshot(link_snapshot(first + timedelta(seconds=12), "DOWN"))["events"] == 0
        store.ingest_snapshot(link_snapshot(first + timedelta(seconds=13), "UP"))
        assert store.list_records("metrics", page=1, limit=5, link_id=link_id, name="LINK_STATE")["pagination"]["total"] == 4
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM public.events WHERE event_type='LINK_FAILURE' AND link_id=%s", (link_id,))
            assert cursor.fetchone()[0] == "RESOLVED"
        page = store.list_records("metrics", page=2, limit=2, device_id=device1)
        assert page["pagination"]["total"] >= 5 and len(page["data"]) == 2
        window = store.list_records("metrics", page=1, limit=10, link_id=link_id,
                                    from_time=first + timedelta(seconds=11),
                                    to_time=first + timedelta(seconds=12))
        assert window["pagination"]["total"] == 2
        connection.rollback()

    with psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10) as connection:
        assert connection.execute("SELECT count(*) FROM public.devices WHERE name IN (%s,%s)",
                                  (name1, name2)).fetchone()[0] == 0
