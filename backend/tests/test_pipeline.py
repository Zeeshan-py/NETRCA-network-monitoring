from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.network.errors import MonitoringFailure
from app.pipeline.models import EventIn, LogIn, MetricIn


NOW = datetime.now(timezone.utc) - timedelta(seconds=2)
DEVICE = uuid4()


def metric(**changes):
    return dict(device_id=DEVICE, metric_type="RX_BYTES", value=0, unit="bytes", timestamp=NOW,
                source="mininet_snapshot", observation_key="sample:rx:0001", interface="h1-eth0") | changes


def test_metric_units_zero_missing_and_timestamps():
    assert MetricIn(**metric()).value == 0
    for value in (None, -1, "NaN", "Infinity"):
        with pytest.raises(ValidationError):
            MetricIn(**metric(value=value))
    for change in (dict(unit="Mbps"), dict(value=1.5), dict(interface=None),
                   dict(timestamp=NOW.replace(tzinfo=None)),
                   dict(timestamp=NOW + timedelta(days=1))):
        with pytest.raises(ValidationError):
            MetricIn(**metric(**change))
    with pytest.raises(ValidationError):
        MetricIn(**metric(metric_type="PACKET_LOSS", unit="%", value=101, interface=None))


def test_structured_log_and_event_validation():
    log = dict(device_id=DEVICE, severity="ERROR", message="Interface read failed", source="netrca",
               timestamp=NOW, observation_key="log:00000001")
    assert LogIn(**log).severity == "ERROR"
    for change in (dict(severity="DEBUG"), dict(message="password=example"), dict(message="raw\noutput"),
                   dict(device_id=None)):
        with pytest.raises(ValidationError):
            LogIn(**(log | change))
    event = dict(device_id=DEVICE, event_type="PROBE_TIMEOUT", severity="MEDIUM", source="mininet_probe",
                 timestamp=NOW, dedup_key="probe:00000001", message="Probe timed out")
    assert EventIn(**event).event_type == "PROBE_TIMEOUT"
    with pytest.raises(ValidationError):
        EventIn(**(event | dict(device_id=None)))


def client(*, writes=False):
    settings = Settings(_env_file=None, DATABASE_URL=None, pipeline_writes_enabled=writes)
    app = create_app(settings)
    return TestClient(app, client=("127.0.0.1", 50000)), app


def test_api_local_control_write_gate_and_pagination_validation():
    api, _ = client()
    assert api.post("/api/v1/metrics", json={"items": [MetricIn(**metric()).model_dump(mode="json")]}).status_code == 403
    assert api.post("/api/v1/metrics", headers={"X-NetRCA-Local-Control": "1"},
                    json={"items": [MetricIn(**metric()).model_dump(mode="json")]}).json()["error"]["code"] == "PIPELINE_WRITES_DISABLED"
    assert api.get("/api/v1/metrics?page=0").status_code == 422
    assert api.get("/api/v1/events?limit=101").status_code == 422
    assert api.get("/api/v1/metrics?from=2026-10-13T01:00:00&to=2026-10-13T02:00:00Z").status_code == 422
    assert api.get("/api/v1/logs").status_code == 503


def test_api_ingest_and_history_with_store_stub():
    api, app = client(writes=True)
    class Store:
        def ingest_metrics(self, items):
            assert items[0].value == 0
            return {"inserted": 1, "duplicates": 0}
        def ingest_log(self, value):
            return {"inserted": 1, "duplicates": 0}
        def ingest_event(self, value):
            return {"inserted": 1, "duplicates": 0}
        def list_records(self, table, *, page, limit, device_id, link_id, name, from_time, to_time):
            assert table == "metrics" and page == 2 and limit == 1 and name == "RX_BYTES"
            return {"data": [{"value": 0}], "pagination": {"page": 2, "limit": 1, "total": 2, "pages": 2}}
    app.state.evidence_store = Store()
    headers = {"X-NetRCA-Local-Control": "1"}
    assert api.post("/api/v1/metrics", headers=headers,
                    json={"items": [MetricIn(**metric()).model_dump(mode="json")]}).json()["error"]["code"] == "INVALID_SOURCE"
    assert api.post("/api/v1/metrics", headers=headers,
                    json={"items": [MetricIn(**metric(source="manual")).model_dump(mode="json")]}).json()["data"]["inserted"] == 1
    assert api.get("/api/v1/metrics?page=2&limit=1&metric_type=RX_BYTES").json()["pagination"]["total"] == 2
    log = LogIn(device_id=DEVICE, severity="INFO", message="Collection completed", source="operator",
                timestamp=NOW, observation_key="log:00000002")
    assert api.post("/api/v1/logs", headers=headers, json=log.model_dump(mode="json")).status_code == 200
    event = EventIn(device_id=DEVICE, event_type="PROBE_FAILED", severity="MEDIUM",
                    source="operator", timestamp=NOW, dedup_key="probe:00000002", message="Host unreachable")
    assert api.post("/api/v1/events", headers=headers, json=event.model_dump(mode="json")).status_code == 200


def test_collect_reports_network_unavailable_without_database():
    api, _ = client(writes=True)
    response = api.post("/api/v1/pipeline/collect", headers={"X-NetRCA-Local-Control": "1"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MININET_UNAVAILABLE"


def test_failed_running_collection_stores_one_structured_failure_event():
    api, app = client(writes=True)
    observed = []
    class Manager:
        def monitor_snapshot(self):
            raise MonitoringFailure("Collection command failed")
        def get_status(self):
            return SimpleNamespace(state="RUNNING")
    class Store:
        def ingest_event(self, item):
            observed.append(item)
            return {"inserted": 1, "duplicates": 0}
    app.state.network_manager = Manager()
    app.state.evidence_store = Store()
    response = api.post("/api/v1/pipeline/collect", headers={"X-NetRCA-Local-Control": "1"})
    assert response.status_code == 503
    assert observed[0].event_type == "COLLECTION_FAILURE"
    assert observed[0].dedup_key == "collection:mininet_snapshot"
