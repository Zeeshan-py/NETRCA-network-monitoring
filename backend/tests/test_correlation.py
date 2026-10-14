"""Phase 9 deterministic and local API tests; no database or Mininet required."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.correlation.engine import Evidence, group, relationship, severity_of
from app.db.connection import DatabaseUnavailable
from app.main import create_app


NOW = datetime.now(timezone.utc).replace(microsecond=0)
WINDOW = timedelta(minutes=5)
DEVICE = uuid4()
OTHER = uuid4()
LINK = uuid4()
SERVICE = uuid4()


def evidence(kind="EVENT", *, age=0, device=DEVICE, link=None, service=None,
             severity="LOW", observed=True, metric=None, source_event=None):
    return Evidence(kind, uuid4(), NOW - timedelta(seconds=age) if observed else None,
                    severity, device_id=device, link_id=link, service_id=service,
                    metric_id=metric, event_id=source_event)


def grouped(items, links=None):
    return group(items, links or {}, now=NOW, window=WINDOW, max_age=timedelta(hours=1))


def test_related_same_device_inside_window_and_boundary():
    first = evidence(age=300)
    second = evidence(age=0)
    assert relationship(first, second, {}, window=WINDOW) == "SAME_DEVICE"
    assert len(grouped([first, second])[0]) == 1


def test_outside_window_and_stale_evidence_separate_or_skipped():
    first, second = evidence(age=301), evidence()
    assert relationship(first, second, {}, window=WINDOW) is None
    assert len(grouped([first, second])[0]) == 2
    groups, skipped = grouped([evidence(age=3601)])
    assert groups == [] and len(skipped) == 1


def test_known_link_endpoint_and_unknown_topology():
    link_event = evidence(device=None, link=LINK)
    endpoint = evidence(device=DEVICE)
    assert relationship(link_event, endpoint, {LINK: frozenset((DEVICE, OTHER))}, window=WINDOW) == "LINK_ENDPOINT"
    assert relationship(link_event, endpoint, {}, window=WINDOW) is None
    assert len(grouped([link_event, endpoint], {LINK: frozenset((DEVICE, OTHER))})[0]) == 1
    assert relationship(link_event, evidence(device=None, link=LINK), {}, window=WINDOW) == "SAME_LINK"


def test_unrelated_devices_and_different_services_do_not_group():
    assert len(grouped([evidence(device=DEVICE), evidence(device=OTHER)])[0]) == 2
    assert len(grouped([evidence(service=SERVICE), evidence(service=uuid4())])[0]) == 2
    assert len(grouped([evidence(device=None), evidence(device=None)])[0]) == 2


def test_phase8_metric_and_event_references_are_explicit():
    event = evidence()
    anomaly = evidence("ANOMALY", source_event=event.id)
    assert relationship(event, anomaly, {}, window=WINDOW) == "SOURCE_EVENT"
    metric_id = uuid4()
    first = evidence("ANOMALY", device=None, metric=metric_id)
    second = evidence("ANOMALY", device=None, metric=metric_id)
    assert relationship(first, second, {}, window=WINDOW) == "SOURCE_METRIC"


def test_duplicate_missing_timestamp_future_and_empty_input():
    first = evidence()
    groups, skipped = grouped([first, first, evidence(observed=False), evidence(age=-1)])
    assert len(groups) == 1 and len(groups[0]) == 1 and len(skipped) == 3
    assert grouped([]) == ([], [])


def test_severity_selection_and_missing_severity():
    assert severity_of([evidence(severity="MEDIUM"), evidence(severity="CRITICAL")]) == "CRITICAL"
    assert severity_of([evidence(severity=None)]) == "LOW"
    assert severity_of([]) == "LOW"


class FakeStore:
    def __init__(self):
        self.calls = []

    def correlate(self, value):
        self.calls.append(value)
        return {"incidents": [], "skipped_ids": [], "created": 0, "attached": 0}

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return {"data": [{"id": uuid4(), "status": "DETECTED"}],
                "pagination": {"page": kwargs["page"], "limit": kwargs["limit"], "total": 1, "pages": 1}}

    def get(self, incident_id):
        self.calls.append(incident_id)
        return {"id": incident_id, "events": [], "anomalies": []}


def test_api_control_pagination_detail_and_validation():
    app = create_app(Settings(_env_file=None, correlation_writes_enabled=True))
    fake = FakeStore()
    app.state.incident_store = fake
    headers = {"X-NetRCA-Local-Control": "1"}
    with TestClient(app, client=("192.0.2.1", 5555)) as client:
        assert client.post("/api/v1/events/correlate", json={}, headers=headers).status_code == 403
        assert client.get("/api/v1/incidents").status_code == 403
    with TestClient(app, client=("127.0.0.1", 5555)) as client:
        assert client.post("/api/v1/events/correlate", json={}).status_code == 403
        assert client.post("/api/v1/events/correlate", json={}, headers=headers).json()["data"]["created"] == 0
        assert client.post("/api/v1/events/correlate", json={"event_ids": ["bad"]}, headers=headers).status_code == 422
        listing = client.get("/api/v1/incidents?page=2&limit=1&status=DETECTED").json()
        assert listing["pagination"]["page"] == 2
        assert client.get("/api/v1/incidents?limit=101").status_code == 422
        assert client.get("/api/v1/incidents?status=OPEN").status_code == 422
        assert client.get(f"/api/v1/incidents/{uuid4()}").json()["data"]["events"] == []


def test_api_disabled_writes_and_sanitized_database_failure():
    app = create_app(Settings(_env_file=None, correlation_writes_enabled=False))
    with TestClient(app, client=("127.0.0.1", 5555)) as client:
        assert client.post("/api/v1/events/correlate", json={},
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
    app.state.settings = Settings(_env_file=None, correlation_writes_enabled=True)
    class Failed:
        def correlate(self, _value):
            raise DatabaseUnavailable("Database operation failed")
        def list(self, **_kwargs):
            raise DatabaseUnavailable("Database operation failed")
        def get(self, _id):
            raise DatabaseUnavailable("Database operation failed")
    app.state.incident_store = Failed()
    with TestClient(app, client=("127.0.0.1", 5555)) as client:
        assert client.post("/api/v1/events/correlate", json={},
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 503
        assert client.get("/api/v1/incidents").status_code == 503
        assert client.get(f"/api/v1/incidents/{uuid4()}").status_code == 503
