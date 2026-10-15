"""Phase 13 evidence, security, provider and API contracts without a live Gemini call."""
from datetime import datetime, timezone
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.explanation.context import build_input
from app.explanation.models import ModelSelection
from app.explanation.provider import GeminiProvider, ProviderUnavailable
from app.explanation.service import ExplanationService
from app.explanation.store import ExplanationNotReady, Snapshot
from app.impact.engine import analyze as impact_analyze
from app.impact.models import ImpactRun
from app.main import create_app
from app.rca.engine import analyze as rca_analyze
from app.rca.models import EvidenceReference, Observation, RcaRun
from app.topology.graph import TopologyGraph
from app.topology.models import Device, Link


NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)
INCIDENT, DEVICE_A, DEVICE_B, LINK, EVENT = [UUID(int=n) for n in range(1, 6)]


def snapshot(*, evidence=True, impact=True, second_candidate=False, service=False):
    graph = TopologyGraph(
        [Device(id=DEVICE_A, name="a", device_type="SWITCH", status="HEALTHY"),
         Device(id=DEVICE_B, name="b", device_type="SWITCH", status="HEALTHY")],
        [Link(id=LINK, source_device_id=DEVICE_A, destination_device_id=DEVICE_B, status="DOWN")])
    items = ([Observation(kind="EVENT", id=EVENT, observed_at=NOW, link_id=LINK,
                          event_type="LINK_FAILURE", event_status="DETECTED")] if evidence else [])
    if second_candidate:
        items.append(Observation(kind="EVENT", id=UUID(int=6), observed_at=NOW,
                                 device_id=DEVICE_A, event_type="DEVICE_UNAVAILABLE",
                                 event_status="DETECTED"))
    result = rca_analyze(INCIDENT, items, graph)
    rca = RcaRun(id=UUID(int=7), incident_id=INCIDENT, analysis_version="RULES_V1",
                 input_fingerprint="a" * 64, status=result.status, result=result,
                 created_at=NOW, last_analyzed_at=NOW)
    impact_run = None
    if impact:
        bindings = ([{"device_id": DEVICE_A, "service_id": UUID(int=99),
                     "status": "UP", "service_status": "UP"}] if service else [])
        outcome = impact_analyze(rca, items, graph, bindings)
        impact_run = ImpactRun(id=UUID(int=8), rca_run_id=rca.id,
                               analysis_version="IMPACT_RULES_V1", input_fingerprint="b" * 64,
                               topology_fingerprint="c" * 64, status=outcome.status,
                               result=outcome, created_at=NOW, last_analyzed_at=NOW)
    return Snapshot(INCIDENT, items, graph, rca, impact_run)


class FakeStore:
    def __init__(self, value):
        self.value = value

    def load(self, incident_id):
        assert incident_id == INCIDENT
        return self.value


class FakeProvider:
    def __init__(self, value=None):
        self.value = value
        self.settings = Settings(_env_file=None)

    def select(self, context):
        if self.value is not None:
            raise self.value
        return ModelSelection(ordered_claim_ids=[claim.claim_id for claim in reversed(context.claims)])


def service(value):
    return ExplanationService(FakeStore(value), FakeProvider())


def test_supported_explanation_and_provenance():
    result = service(snapshot()).explain(INCIDENT)
    assert result.rca_run_id == UUID(int=7) and result.impact_run_id == UUID(int=8)
    assert result.summary and result.observed_facts and result.candidate_explanations
    assert result.failure_chain_explanation and result.impact_explanation
    assert any("potentially exposed" in claim.text for claim in result.impact_explanation)
    assert all("confirmed root cause" not in claim.text for claim in result.candidate_explanations)
    assert any(ref.source_id == EVENT for ref in result.evidence_references)
    assert all(claim.evidence_references for claim in result.summary + result.impact_explanation)


def test_inconclusive_and_missing_impact():
    value = snapshot(evidence=False, impact=True)
    assert value.rca.status == "INCONCLUSIVE"
    result = service(value).explain(INCIDENT)
    assert "inconclusive" in result.summary[0].text
    assert result.candidate_explanations == []
    assert result.uncertainties and result.impact_explanation == []
    missing = service(snapshot(evidence=False, impact=False)).explain(INCIDENT)
    assert missing.impact_run_id is None and missing.missing_evidence


def test_multiple_candidates_remain_unconfirmed():
    result = service(snapshot(second_candidate=True)).explain(INCIDENT)
    assert len(result.candidate_explanations) >= 2
    assert all("candidate, not a confirmed cause" in claim.text for claim in result.candidate_explanations)


def test_potential_service_mapping_is_not_an_observed_outage():
    result = service(snapshot(service=True)).explain(INCIDENT)
    assert any("Service" in claim.text and "potentially exposed" in claim.text
               for claim in result.impact_explanation)


def test_unknown_evidence_and_cross_incident_rejected():
    value = snapshot()
    value.rca.result.candidates[0].supporting_evidence.append(
        EvidenceReference(source_type="EVENT", source_id=UUID(int=99), timestamp=NOW,
                          reason="DIRECT_FAILURE"))
    with pytest.raises(ExplanationNotReady, match="UNKNOWN_EVIDENCE_REFERENCE"):
        build_input(value)
    wrong = snapshot()
    wrong.rca.result.incident_id = UUID(int=100)
    with pytest.raises(ExplanationNotReady):
        build_input(wrong)
    wrong_impact = snapshot()
    wrong_impact.impact.result.rca_run_id = UUID(int=101)
    with pytest.raises(ExplanationNotReady, match="MISMATCHED_ANALYSIS_RUN"):
        build_input(wrong_impact)


def test_untrusted_log_text_is_not_sent_and_input_is_bounded():
    value = snapshot()
    # No raw event message is part of Observation or the provider input.
    context = build_input(value)
    assert "ignore previous instructions" not in context.model_dump_json().lower()
    import app.explanation.context as module
    old = module.MAX_INPUT_BYTES
    module.MAX_INPUT_BYTES = 10
    try:
        with pytest.raises(ExplanationNotReady, match="TOO_LARGE"):
            build_input(value)
    finally:
        module.MAX_INPUT_BYTES = old


def test_provider_missing_key_timeout_rate_limit_bad_output_and_secret_redaction(monkeypatch):
    context = build_input(snapshot())
    settings = Settings(_env_file=None, GEMINI_API_KEY="secret-test-key")
    provider = GeminiProvider(settings)
    # Use a simple fake client to avoid recursive httpx.Client monkeypatching.
    class Client:
        def __init__(self, response=None, error=None):
            self.response, self.error = response, error
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def post(self, *_args, **_kwargs):
            if self.error:
                raise self.error
            return self.response
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: Client(httpx.Response(429)))
    with pytest.raises(ProviderUnavailable, match="rate limit"):
        provider.select(context)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: Client(error=httpx.TimeoutException("timeout")))
    with pytest.raises(ProviderUnavailable, match="timed out"):
        provider.select(context)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: Client(httpx.Response(200, json={"candidates": []})))
    with pytest.raises(ProviderUnavailable, match="invalid response") as error:
        provider.select(context)
    assert "secret-test-key" not in str(error.value)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: Client(httpx.Response(500, text="secret-test-key")))
    with pytest.raises(ProviderUnavailable, match="request failed") as error:
        provider.select(context)
    assert "secret-test-key" not in str(error.value)
    with pytest.raises(ProviderUnavailable, match="credentials"):
        GeminiProvider(Settings(_env_file=None, GEMINI_API_KEY="")).select(context)


def test_provider_rejects_unknown_claim_and_accepts_complete_selection(monkeypatch):
    context = build_input(snapshot())
    settings = Settings(_env_file=None, GEMINI_API_KEY="test-key")
    class Client:
        def __init__(self, ids):
            self.ids = ids
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def post(self, *_args, **_kwargs):
            import json
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [
                {"text": json.dumps({"ordered_claim_ids": self.ids})}]}}]})
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: Client(["C999"]))
    with pytest.raises(ProviderUnavailable):
        GeminiProvider(settings).select(context)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: Client(
        [claim.claim_id for claim in context.claims]))
    assert len(GeminiProvider(settings).select(context).ordered_claim_ids) == len(context.claims)


def test_provider_cannot_add_claims_or_invoke_tools(monkeypatch):
    context = build_input(snapshot())
    settings = Settings(_env_file=None, GEMINI_API_KEY="test-key")
    seen = {}
    class Client:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def post(self, _url, **kwargs):
            seen.update(kwargs["json"])
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [
                {"text": '{"ordered_claim_ids":["C001"],"confirmed_root_cause":"fabricated"}'}]}}]})
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: Client())
    with pytest.raises(ProviderUnavailable):
        GeminiProvider(settings).select(context)
    assert "tools" not in seen and "functionDeclarations" not in str(seen)


def test_api_access_control_errors_and_success():
    app = create_app(Settings(_env_file=None, gemini_enabled=True))
    app.state.explanation_service = service(snapshot())
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        path = f"/api/v1/ai/incidents/{INCIDENT}/explain"
        assert client.post(path).status_code == 403
        result = client.post(path, headers={"X-NetRCA-Local-Control": "1"})
        assert result.status_code == 200
        assert result.json()["data"]["rca_run_id"] == str(UUID(int=7))
        assert client.post("/api/v1/ai/incidents/not-a-uuid/explain",
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 422
        app.state.explanation_service = ExplanationService(FakeStore(snapshot()),
                                                            FakeProvider(ProviderUnavailable("secret")))
        error = client.post(path, headers={"X-NetRCA-Local-Control": "1"})
        assert error.status_code == 503 and "secret" not in error.text
    disabled = create_app(Settings(_env_file=None, gemini_enabled=False))
    with TestClient(disabled, client=("127.0.0.1", 50000)) as client:
        assert client.post(path, headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
