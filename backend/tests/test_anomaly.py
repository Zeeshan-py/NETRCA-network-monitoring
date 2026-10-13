"""Deterministic synthetic fixtures; none are presented as live network data."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from contextlib import contextmanager
from types import ModuleType
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.anomaly.engine import _isolation, detect
from app.anomaly.models import DetectionRequest
from app.anomaly.service import AnomalyService, DuplicateObservation
from app.anomaly.store import AnomalyStore, model_version
from app.core.config import Settings
from app.db.connection import DatabaseUnavailable
from app.main import create_app
from app.pipeline.models import MetricIn


DEVICE = uuid4()
LINK = uuid4()
NOW = datetime.now(timezone.utc).replace(microsecond=0)
SETTINGS = Settings(_env_file=None)
UNITS = {"LATENCY": "ms", "PACKET_LOSS": "%", "AVAILABILITY": "%", "INTERFACE_STATE": "state",
         "LINK_STATE": "state", "RX_ERRORS": "packets", "TX_ERRORS": "packets"}


def metric(kind="LATENCY", value=20, *, minutes=0, key=None, interface=None, target=None):
    return MetricIn(device_id=None if kind == "LINK_STATE" else DEVICE,
                    link_id=LINK if kind == "LINK_STATE" else None,
                    metric_type=kind, value=Decimal(str(value)), unit=UNITS[kind],
                    timestamp=NOW - timedelta(minutes=minutes), source="manual",
                    observation_key=key or f"test:{uuid4().hex}", interface=interface, target=target)


def test_thresholds_and_normal_values():
    for kind, value in (("LATENCY", 20), ("PACKET_LOSS", 0), ("AVAILABILITY", 100),
                        ("INTERFACE_STATE", 1), ("LINK_STATE", 1)):
        observation = metric(kind, value, interface="h1-eth0" if kind == "INTERFACE_STATE" else None)
        result = detect(observation, [], SETTINGS, now=NOW)
        assert result.status == "NORMAL" and result.score == 0
    for kind, value in (("LATENCY", 300), ("PACKET_LOSS", 25), ("AVAILABILITY", 0),
                        ("INTERFACE_STATE", 0), ("LINK_STATE", 0)):
        observation = metric(kind, value, interface="h1-eth0" if kind == "INTERFACE_STATE" else None)
        result = detect(observation, [], SETTINGS, now=NOW)
        assert result.status == "ANOMALY" and result.method == "THRESHOLD"
        assert result.score is not None and 0 < result.score <= 1
        assert result.severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_baseline_requires_distinct_prior_same_scope_samples():
    observation = metric(value=50, target="h2")
    history = [metric(value=10 + index % 3, minutes=index + 1, target="h2") for index in range(20)]
    duplicate = history[0].model_copy(deep=True)
    other_target = metric(value=10, minutes=2, target="server1")
    future = metric(value=10, minutes=0, target="h2")
    result = detect(observation, history + [duplicate, other_target, future], SETTINGS, now=NOW)
    assert result.status == "ANOMALY" and result.method == "BASELINE"
    assert result.baseline_samples == 20
    assert result.support["median"] == 11
    assert detect(observation, history[:19], SETTINGS, now=NOW).reason == "WITHIN_LIMIT_BASELINE_INSUFFICIENT"
    assert detect(metric(value=11, target="h2"), history, SETTINGS, now=NOW).status == "NORMAL"
    copied = history[0].model_copy(update={"observation_key": "test:copied-different-key"})
    assert detect(observation, history + [copied], SETTINGS, now=NOW).baseline_samples == 20


def test_isolation_margin_scoring_with_deterministic_model_stub(monkeypatch):
    """Exercises the optional adapter; actual sklearn fit needs the installed dependency."""
    parent = ModuleType("sklearn")
    parent.__path__ = []
    ensemble = ModuleType("sklearn.ensemble")

    class IsolationForest:
        def __init__(self, **kwargs):
            assert kwargs["random_state"] == 41 and kwargs["n_jobs"] == 1

        def fit(self, rows):
            assert len(rows) == 50
            return self

        def decision_function(self, rows):
            return [-0.2] if len(rows) == 1 else [0.1] * len(rows)

    ensemble.IsolationForest = IsolationForest
    monkeypatch.setitem(sys.modules, "sklearn", parent)
    monkeypatch.setitem(sys.modules, "sklearn.ensemble", ensemble)
    history = [metric(value=20 + index % 10, minutes=index + 1) for index in range(50)]
    result = detect(metric(value=30), history, SETTINGS, now=NOW)
    assert result.method == "ISOLATION_FOREST" and result.score == 1
    assert result.support["decision_margin"] == -0.2


def test_real_isolation_forest_on_synthetic_fixture_when_installed():
    pytest.importorskip("sklearn", reason="scikit-learn is not installed in this environment")
    history = [metric(value=20 + index % 10, minutes=index + 1) for index in range(50)]
    result = _isolation(80, history, SETTINGS)
    assert result is not None
    percentile, margin = result
    assert margin < 0 and 0 <= percentile <= 1


def test_counters_missing_reset_and_increase():
    item = metric("RX_ERRORS", 12, interface="h1-eth0")
    assert detect(item, [], SETTINGS, now=NOW).reason == "COUNTER_PREDECESSOR_MISSING"
    previous = metric("RX_ERRORS", 10, minutes=1, interface="h1-eth0")
    result = detect(item, [previous], SETTINGS, now=NOW)
    assert result.status == "ANOMALY" and result.support["delta"] == "2"
    reset = metric("RX_ERRORS", 5, interface="h1-eth0")
    assert detect(reset, [previous], SETTINGS, now=NOW).reason == "COUNTER_RESET"
    stable = metric("RX_ERRORS", 10, interface="h1-eth0")
    assert detect(stable, [previous], SETTINGS, now=NOW).status == "NORMAL"


def test_stale_invalid_and_configured_thresholds():
    stale = metric(value=400, minutes=120)
    assert detect(stale, [], SETTINGS, now=NOW).status == "INSUFFICIENT_DATA"
    with pytest.raises(ValidationError):
        metric("PACKET_LOSS", 101)
    with pytest.raises(ValidationError):
        DetectionRequest(observations=[metric()], metric_ids=[uuid4()])
    default = detect(metric(value=150), [], SETTINGS, now=NOW)
    raised = Settings(_env_file=None, anomaly_latency_ms=200)
    assert default.status == "ANOMALY"
    assert detect(metric(value=150), [], raised, now=NOW).status == "NORMAL"


class Store:
    def __init__(self, item=None, unavailable=False):
        self.item = item or metric(value=200)
        self.unavailable = unavailable
        self.saved = []

    def load(self, identifiers):
        if self.unavailable:
            raise DatabaseUnavailable("Unavailable")
        return [(identifier, self.item, []) for identifier in dict.fromkeys(identifiers)]

    def save(self, finding):
        if self.unavailable:
            raise DatabaseUnavailable("Unavailable")
        self.saved.append(finding)
        return uuid4(), True


def test_batch_dedup_persistence_and_database_unavailable():
    item = metric(value=150)
    store = Store(item)
    service = AnomalyService(SETTINGS, store)
    local = service.run(DetectionRequest(observations=[item, item]))
    assert len(local["items"]) == 1 and local["items"][0].persistence == "NOT_REQUESTED"
    copied = item.model_copy(update={"observation_key": "test:same-measurement-new-key"})
    assert len(service.run(DetectionRequest(observations=[item, copied]))["items"]) == 1
    with pytest.raises(DuplicateObservation):
        service.run(DetectionRequest(observations=[item, item.model_copy(update={"value": Decimal(30)})]))
    result = service.run(DetectionRequest(metric_ids=[uuid4(), uuid4()], persist=True))
    assert len(result["items"]) == 2 and result["persisted"] == 2
    store.unavailable = True
    with pytest.raises(DatabaseUnavailable):
        service.run(DetectionRequest(metric_ids=[uuid4()]))
    store.unavailable = False
    store.save = lambda finding: (_ for _ in ()).throw(DatabaseUnavailable("Unavailable"))
    result = service.run(DetectionRequest(metric_ids=[uuid4()], persist=True))
    assert result["items"][0].persistence == "UNAVAILABLE" and result["persisted"] == 0


def test_store_idempotence_and_configuration_version(monkeypatch):
    identifier, existing_id = uuid4(), uuid4()
    state = {"saved": False, "insertions": 0}

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def execute(self, sql, params):
            self.sql = sql
            if sql.startswith("INSERT INTO public.anomalies"):
                state["saved"] = True
                state["insertions"] += 1

        def fetchone(self):
            if "FROM public.metrics" in self.sql:
                return {"id": identifier}
            if "FROM public.anomalies" in self.sql:
                return {"id": existing_id} if state["saved"] else None
            return {"id": existing_id}

    class Connection:
        def cursor(self, **_kwargs):
            return Cursor()

    @contextmanager
    def transaction(_settings):
        yield Connection()

    monkeypatch.setattr("app.anomaly.store.transaction", transaction)
    store = AnomalyStore(SETTINGS)
    finding = detect(metric(value=300), [], SETTINGS, metric_id=identifier, now=NOW)
    assert store.save(finding) == (existing_id, True)
    assert store.save(finding) == (existing_id, False)
    assert state["insertions"] == 1
    assert model_version(SETTINGS) != model_version(Settings(_env_file=None, anomaly_latency_ms=200))


def test_api_local_controls_validation_and_result_envelope():
    settings = Settings(_env_file=None, anomaly_writes_enabled=False)
    app = create_app(settings)
    body = {"observations": [metric(value=300).model_dump(mode="json")]}
    with TestClient(app, client=("192.0.2.1", 5555)) as client:
        assert client.post("/api/v1/anomalies/detect", json=body,
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
    with TestClient(app, client=("127.0.0.1", 5555)) as client:
        assert client.post("/api/v1/anomalies/detect", json=body).json()["error"]["code"] == "LOCAL_CONTROL_REQUIRED"
        response = client.post("/api/v1/anomalies/detect", json=body,
                               headers={"X-NetRCA-Local-Control": "1"})
        assert response.status_code == 200
        assert response.json()["data"]["anomalies_detected"] == 1
        assert client.post("/api/v1/anomalies/detect", json={"observations": []},
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 422
        assert client.post("/api/v1/anomalies/detect", json={"metric_ids": [str(uuid4())], "persist": True},
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
        assert client.get("/api/v1/anomalies").status_code == 503
