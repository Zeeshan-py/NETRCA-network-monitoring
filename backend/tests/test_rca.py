from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.connection import DatabaseUnavailable
from app.main import create_app
from app.rca.engine import analyze
from app.rca.models import Observation, RcaRun
from app.rca.store import IncidentNotFound
from app.topology.graph import TopologyGraph
from app.topology.models import Device, Link


IDS = [UUID(int=n) for n in range(1, 8)]
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def graph():
    return TopologyGraph([Device(id=IDS[n], name=f"device{n}", device_type="SWITCH", status="HEALTHY")
                          for n in range(3)],
                         [Link(id=IDS[4], source_device_id=IDS[0], destination_device_id=IDS[1], status="DOWN"),
                          Link(id=IDS[5], source_device_id=IDS[1], destination_device_id=IDS[2], status="UP")])


def failure(**overrides):
    values = dict(kind="EVENT", id=IDS[6], observed_at=NOW, device_id=IDS[1],
                  event_type="DEVICE_UNAVAILABLE", event_status="DETECTED")
    values.update(overrides)
    return Observation(**values)


def symptom(**overrides):
    values = dict(kind="ANOMALY", id=uuid4(), observed_at=NOW + timedelta(seconds=10),
                  device_id=IDS[2], metric_id=uuid4(), metric_type="PACKET_LOSS",
                  metric_value=Decimal("25"))
    values.update(overrides)
    return Observation(**values)


def test_direct_failure_timing_cut_and_provenance():
    direct, later = failure(), symptom()
    result = analyze(uuid4(), [later, direct], graph())
    assert result.status == "CANDIDATES"
    candidate = result.candidates[0]
    assert candidate.target_id == IDS[1] and candidate.score == 6
    assert [rule.rule for rule in candidate.contributions] == [
        "DIRECT_FAILURE", "FOLLOWING_RELATED_SYMPTOM", "TOPOLOGY_CUT_WITH_SYMPTOM"]
    assert {(ref.source_type, ref.source_id) for ref in candidate.supporting_evidence} == {
        ("EVENT", direct.id), ("ANOMALY", later.id), ("TOPOLOGY", IDS[1])}
    assert candidate.score_kind == "UNCALIBRATED_RULE_POINTS"
    assert result.model_dump(mode="json") == analyze(result.incident_id, [direct, later], graph()).model_dump(mode="json")


def test_link_failure_and_metric_state_support_same_candidate_without_double_counting():
    event = failure(event_type="LINK_FAILURE", device_id=None, link_id=IDS[4])
    metric_id = uuid4()
    anomaly = symptom(device_id=None, link_id=IDS[4], metric_id=metric_id,
                      metric_type="LINK_STATE", metric_value=Decimal(0))
    duplicate = anomaly.model_copy(update={"id": uuid4()})
    result = analyze(uuid4(), [event, anomaly, duplicate, anomaly], graph())
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.cause_type == "LINK_FAILURE" and candidate.target_id == IDS[4]
    assert candidate.score == 6  # one additional metric observation, not two anomaly rows
    assert len([ref for ref in candidate.supporting_evidence if ref.source_type == "ANOMALY"]) == 1


def test_earlier_symptom_and_resolved_failure_are_contradictions():
    early = symptom(observed_at=NOW - timedelta(seconds=5))
    result = analyze(uuid4(), [failure(event_status="RESOLVED"), early], graph())
    assert result.status == "INCONCLUSIVE"
    candidate = result.candidates[0]
    assert candidate.score == 0
    assert {rule.rule for rule in candidate.contributions} >= {
        "RESOLVED_FAILURE", "SYMPTOM_PRECEDES_FAILURE"}
    assert {ref.source_id for ref in candidate.contradictory_evidence} == {IDS[6], early.id}


def test_centrality_and_symptoms_alone_do_not_create_candidate():
    result = analyze(uuid4(), [symptom()], graph())
    assert result.status == "INCONCLUSIVE" and result.candidates == []
    assert "NO_DIRECT_FAILURE_EVIDENCE" in result.limitations
    empty = analyze(uuid4(), [], TopologyGraph([], []))
    assert empty.status == "INCONCLUSIVE" and "NO_VALID_INCIDENT_EVIDENCE" in empty.limitations


def test_missing_time_unknown_topology_and_outside_window():
    direct = failure(observed_at=None, device_id=uuid4())
    result = analyze(uuid4(), [direct, symptom()], graph())
    assert result.status == "CANDIDATES"
    assert "MISSING_EVIDENCE_TIMESTAMP" in result.limitations
    assert "TARGET_MISSING_FROM_STORED_TOPOLOGY" in result.candidates[0].limitations
    unknown_link = failure(event_type="LINK_FAILURE", device_id=None, link_id=uuid4())
    assert "TARGET_MISSING_FROM_STORED_TOPOLOGY" in analyze(
        uuid4(), [unknown_link], graph()).candidates[0].limitations
    far = symptom(observed_at=NOW + timedelta(seconds=301))
    assert analyze(uuid4(), [failure(), far], graph()).candidates[0].score == 4
    assert "TOPOLOGY_UNAVAILABLE" in analyze(uuid4(), [failure()], None).limitations


def test_multiple_candidates_have_stable_order_and_unrelated_evidence_not_used():
    a = failure(id=uuid4(), device_id=IDS[0])
    b = failure(id=uuid4(), device_id=IDS[2])
    result = analyze(uuid4(), [b, a], graph())
    assert [candidate.target_id for candidate in result.candidates] == [IDS[0], IDS[2]]
    assert all(candidate.score == 4 for candidate in result.candidates)


class FakeRcaStore:
    def __init__(self, run):
        self.run = run

    def analyze(self, _id):
        return self.run

    def latest(self, _id):
        return self.run


def test_api_controls_validation_results_and_sanitized_failures():
    incident_id = uuid4()
    result = analyze(incident_id, [failure()], graph())
    run = RcaRun(id=uuid4(), incident_id=incident_id, analysis_version="RULES_V1",
                 input_fingerprint="a" * 64, status=result.status, result=result,
                 created_at=NOW, last_analyzed_at=NOW)
    app = create_app(Settings(_env_file=None, rca_writes_enabled=True))
    app.state.rca_store = FakeRcaStore(run)
    route = f"/api/v1/incidents/{incident_id}/root-cause/analyze"
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post(route).status_code == 403
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1"}).json()["data"]["status"] == "CANDIDATES"
        assert client.get(f"/api/v1/incidents/{incident_id}/root-causes").json()["data"]["result"]["candidates"]
        assert client.post("/api/v1/incidents/not-a-uuid/root-cause/analyze",
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 422
        app.state.rca_store.run = None
        assert client.get(f"/api/v1/incidents/{incident_id}/root-causes").json()["error"]["code"] == "RCA_NOT_FOUND"
    with TestClient(app, client=("203.0.113.4", 50000)) as client:
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
        assert client.get(f"/api/v1/incidents/{incident_id}/root-causes").status_code == 403
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1",
                                           "Origin": "https://example.com"}).status_code == 403
    app.state.settings = Settings(_env_file=None, rca_writes_enabled=False)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1"}).json()["error"]["code"] == "RCA_WRITES_DISABLED"

    class Failed:
        def analyze(self, _id):
            raise DatabaseUnavailable("private database detail")

        def latest(self, _id):
            raise IncidentNotFound("missing")

    app.state.rca_store = Failed()
    app.state.settings = Settings(_env_file=None, rca_writes_enabled=True)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.post(route, headers={"X-NetRCA-Local-Control": "1"})
        assert response.status_code == 503 and "private" not in response.text
        assert client.get(f"/api/v1/incidents/{incident_id}/root-causes").json()["error"]["code"] == "INCIDENT_NOT_FOUND"
