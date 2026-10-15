from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.connection import DatabaseUnavailable
from app.impact.engine import analyze
from app.impact.models import ImpactRun
from app.impact.store import RcaNotFound, StaleRca
from app.main import create_app
from app.rca.engine import analyze as rca_analyze
from app.rca.models import Observation, RcaRun
from app.topology.graph import TopologyGraph
from app.topology.models import Device, Link


NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
IDS = [UUID(int=n) for n in range(1, 12)]


def topology():
    return TopologyGraph(
        [Device(id=IDS[n], name=f"node-{n}", device_type="SWITCH", status="HEALTHY")
         for n in (0, 1, 2, 3)],
        [Link(id=IDS[4], source_device_id=IDS[0], destination_device_id=IDS[1], status="DOWN"),
         Link(id=IDS[5], source_device_id=IDS[1], destination_device_id=IDS[2], status="UP")],
    )


def make_run(observations, graph=None):
    graph = graph or topology()
    incident_id = uuid4()
    result = rca_analyze(incident_id, observations, graph)
    return RcaRun(id=uuid4(), incident_id=incident_id, analysis_version="RULES_V1",
                  input_fingerprint="a" * 64, status=result.status, result=result,
                  created_at=NOW, last_analyzed_at=NOW)


def link_failure():
    return Observation(kind="EVENT", id=uuid4(), observed_at=NOW, link_id=IDS[4],
                       event_type="LINK_FAILURE", event_status="DETECTED")


def device_failure(device_id=IDS[1]):
    return Observation(kind="EVENT", id=uuid4(), observed_at=NOW, device_id=device_id,
                       event_type="DEVICE_UNAVAILABLE", event_status="DETECTED")


def bindings():
    return [{"device_id": IDS[1], "service_id": IDS[8], "status": "UP", "service_status": "UP"},
            {"device_id": IDS[3], "service_id": IDS[9], "status": "UP", "service_status": "UP"}]


def test_direct_link_has_only_potential_endpoints_and_no_unsupported_claim():
    evidence = link_failure()
    result = analyze(make_run([evidence]), [evidence], topology(), bindings())
    assert result.status == "ASSESSED" and result.affected_links == 1
    assert {(e.kind, e.id, e.classification) for e in result.entities} >= {
        ("LINK", IDS[4], "OBSERVED"), ("DEVICE", IDS[0], "POTENTIAL"),
        ("DEVICE", IDS[1], "POTENTIAL")}
    assert not any(e.id == IDS[3] for e in result.entities)
    assert result.user_application_impact == "UNKNOWN_UNVERIFIED"
    assert result.chain[0].step == 1
    assert {(ref.source_type, ref.source_id) for ref in result.entities
            if ref.classification == "OBSERVED" for ref in ref.evidence} == {("EVENT", evidence.id)}


def test_device_failure_branches_one_hop_and_maps_hosted_service():
    evidence = device_failure()
    result = analyze(make_run([evidence]), [evidence], topology(), bindings())
    assert result.status == "ASSESSED"
    assert (result.affected_devices, result.affected_links, result.affected_services) == (3, 2, 1)
    assert len([e for e in result.chain if e.source_id == IDS[1] and e.target_kind == "LINK"]) == 2
    assert any(e.id == IDS[8] and e.classification == "POTENTIAL" for e in result.entities)
    assert not any(e.id in {IDS[3], IDS[9]} for e in result.entities)
    assert all(e.classification == "POTENTIAL" for e in result.chain)


def test_unmapped_stale_ambiguous_or_missing_evidence_is_inconclusive():
    evidence = device_failure()
    run = make_run([evidence])
    assert analyze(run, [], topology(), []).status == "INCONCLUSIVE"
    assert analyze(run, [evidence.model_copy(update={"observed_at": None})], topology(), []).status == "INCONCLUSIVE"
    unknown = device_failure(uuid4())
    assert "RCA_TARGET_NOT_IN_STORED_TOPOLOGY" in analyze(
        make_run([unknown]), [unknown], topology(), []).limitations
    tie = make_run([device_failure(IDS[0]), device_failure(IDS[2])])
    assert "AMBIGUOUS_TOP_RCA_CANDIDATE" in analyze(tie, [evidence], topology(), []).limitations
    empty = make_run([])
    assert analyze(empty, [], topology(), []).status == "INCONCLUSIVE"


def test_cross_incident_and_identifier_contamination_rejected():
    evidence = link_failure()
    run = make_run([evidence])
    unrelated = evidence.model_copy(update={"id": uuid4()})
    assert analyze(run, [unrelated], topology(), []).status == "INCONCLUSIVE"
    altered = run.model_copy(deep=True)
    altered.result.incident_id = uuid4()
    assert analyze(altered, [evidence], topology(), []).status == "INCONCLUSIVE"
    result = analyze(run, [evidence], topology(), [])
    assert all(entity.id in {IDS[0], IDS[1], IDS[4]} for entity in result.entities)


def test_other_direct_failure_is_reported_without_inventing_chain():
    main = device_failure(IDS[1])
    independent = device_failure(IDS[3])
    # A following related symptom raises the main candidate above the other.
    symptom = Observation(kind="EVENT", id=uuid4(), observed_at=NOW,
                          device_id=IDS[1], event_type="PROBE_FAILED", event_status="DETECTED")
    run = make_run([main, independent, symptom])
    result = analyze(run, [main, independent, symptom], topology(), [])
    assert result.status == "ASSESSED"
    assert any(e.id == IDS[3] and e.classification == "OBSERVED" for e in result.entities)
    assert not any(e.target_id == IDS[3] for e in result.chain)
    assert "ADDITIONAL_DIRECT_FAILURE_NOT_CAUSALLY_CHAINED" in result.limitations


class FakeStore:
    def __init__(self, run):
        self.run = run
        self.error = None

    def analyze(self, _id):
        if self.error:
            raise self.error
        return self.run

    def latest(self, _id):
        if self.error:
            raise self.error
        return self.run


def test_api_controls_and_sanitized_errors():
    incident = uuid4()
    evidence = link_failure()
    rca = make_run([evidence])
    rca.incident_id = incident
    rca.result.incident_id = incident
    result = analyze(rca, [evidence], topology(), [])
    run = ImpactRun(id=uuid4(), rca_run_id=rca.id, analysis_version="IMPACT_RULES_V1",
                    input_fingerprint="b" * 64, topology_fingerprint="c" * 64,
                    status=result.status, result=result, created_at=NOW, last_analyzed_at=NOW)
    app = create_app(Settings(_env_file=None, impact_writes_enabled=True))
    app.state.impact_store = FakeStore(run)
    route = f"/api/v1/incidents/{incident}/impact/analyze"
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post(route).status_code == 403
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1"}).json()["data"]["status"] == "ASSESSED"
        assert client.get(f"/api/v1/incidents/{incident}/impact").json()["data"]["result"]["entities"]
        assert client.get(f"/api/v1/incidents/{incident}/failure-chain").json()["data"]["result"]["chain"]
        assert client.post("/api/v1/incidents/bad/impact/analyze",
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 422
        app.state.impact_store.run = None
        assert client.get(f"/api/v1/incidents/{incident}/impact").json()["error"]["code"] == "IMPACT_NOT_FOUND"
    with TestClient(app, client=("203.0.113.1", 50000)) as client:
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
        assert client.get(f"/api/v1/incidents/{incident}/impact").status_code == 403
    app.state.settings = Settings(_env_file=None, impact_writes_enabled=False)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1"}).json()["error"]["code"] == "IMPACT_WRITES_DISABLED"
    app.state.settings = Settings(_env_file=None, impact_writes_enabled=True)
    app.state.impact_store.error = DatabaseUnavailable("private connection detail")
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.post(route, headers={"X-NetRCA-Local-Control": "1"})
        assert response.status_code == 503 and "private" not in response.text
        app.state.impact_store.error = RcaNotFound("missing")
        assert client.get(f"/api/v1/incidents/{incident}/impact").json()["error"]["code"] == "RCA_NOT_FOUND"
        app.state.impact_store.error = StaleRca("stale")
        assert client.post(route, headers={"X-NetRCA-Local-Control": "1"}).status_code == 409
