"""Opt-in end-to-end Mininet-to-explanation test with PostgreSQL rollback."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import sys
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.explanation.models import ModelSelection
from app.main import create_app
from app.network.topology import LINKS, NODES


pytestmark = pytest.mark.skipif(
    os.environ.get("NETRCA_RUN_E2E_DB_TESTS") != "1",
    reason="Requires explicit opt-in to isolated Mininet and PostgreSQL rollback test",
)


def test_mininet_evidence_to_mocked_explanation_and_rollback(monkeypatch):
    if sys.platform != "linux" or not hasattr(os, "geteuid") or os.geteuid() != 0:
        pytest.skip("End-to-end Mininet test requires root in the isolated Ubuntu lab")

    settings = Settings(
        simulation_enabled=True,
        topology_writes_enabled=True,
        pipeline_writes_enabled=True,
        anomaly_writes_enabled=True,
        correlation_writes_enabled=True,
        rca_writes_enabled=True,
        impact_writes_enabled=True,
        gemini_enabled=True,
        gemini_api_key="phase15-test-only-key",
        anomaly_ml_enabled=False,
    )
    assert settings.database_url, "Configured PostgreSQL endpoint is required"
    connection = psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10)
    connection.execute("SET LOCAL ROLE service_role")

    @contextmanager
    def shared_transaction(_settings, **_kwargs):
        yield connection

    # Keep every real store operation in one rollback-only PostgreSQL transaction.
    for module in (
        "app.topology.store", "app.pipeline.store", "app.anomaly.store",
        "app.correlation.store", "app.rca.store", "app.impact.store",
        "app.explanation.store",
    ):
        monkeypatch.setattr(f"{module}.transaction", shared_transaction)

    app = create_app(settings)
    client = TestClient(app, client=("127.0.0.1", 50000))
    control = {"X-NetRCA-Local-Control": "1"}
    fixture_suffix = uuid4().hex[:12]
    device_ids: dict[str, str] = {}
    link_ids: dict[frozenset[str], str] = {}

    try:
        with client:
            for node in NODES:
                response = client.post("/api/v1/devices", headers=control, json={
                    "name": node.name,
                    "device_type": node.device_type,
                    "status": "HEALTHY",
                    "ip_address": node.ip,
                    "metadata": {"fixture": "phase15-e2e", "run": fixture_suffix},
                })
                assert response.status_code == 201, response.text
                device_ids[node.name] = response.json()["data"]["id"]

            for link in LINKS:
                response = client.post("/api/v1/links", headers=control, json={
                    "source_device_id": device_ids[link.source],
                    "destination_device_id": device_ids[link.destination],
                    "status": "UP",
                    "metadata": {"fixture": "phase15-e2e", "run": fixture_suffix},
                })
                assert response.status_code == 201, response.text
                link_ids[frozenset((link.source, link.destination))] = response.json()["data"]["id"]

            started = client.post("/api/v1/network/start", headers=control)
            assert started.status_code == 200, started.text
            collection = client.post("/api/v1/pipeline/collect", headers=control)
            assert collection.status_code == 200, collection.text
            assert collection.json()["data"]["metrics"] > 0
            probe = client.post("/api/v1/pipeline/probe", headers=control, json={
                "source": "h1", "destination": "h2", "count": 1, "timeout_seconds": 2,
            })
            assert probe.status_code == 200 and probe.json()["data"]["probe_status"] == "REACHABLE", probe.text

            link_id = link_ids[frozenset(("h1", "s1"))]
            timestamp = datetime.now(timezone.utc).isoformat()
            observation_key = f"phase15:{fixture_suffix}:link-state"
            metric_response = client.post("/api/v1/metrics", headers=control, json={"items": [{
                "link_id": link_id, "metric_type": "LINK_STATE", "value": 0, "unit": "state",
                "timestamp": timestamp, "source": "manual", "observation_key": observation_key,
            }]})
            assert metric_response.status_code == 200, metric_response.text
            metrics = client.get(f"/api/v1/metrics?link_id={link_id}&metric_type=LINK_STATE&limit=100")
            metric_rows = [row for row in metrics.json()["data"]
                           if row["metadata"].get("observation_key") == observation_key]
            assert len(metric_rows) == 1

            detection = client.post("/api/v1/anomalies/detect", headers=control, json={
                "metric_ids": [metric_rows[0]["id"]], "persist": True,
            })
            assert detection.status_code == 200, detection.text
            finding = detection.json()["data"]["items"][0]
            assert finding["status"] == "ANOMALY" and finding["anomaly_id"]

            event_key = f"phase15:{fixture_suffix}:link-failure"
            event = client.post("/api/v1/events", headers=control, json={
                "link_id": link_id, "event_type": "LINK_FAILURE", "severity": "HIGH",
                "source": "operator", "timestamp": timestamp, "dedup_key": event_key,
                "message": "Controlled Phase 15 test link failure",
            })
            assert event.status_code == 200, event.text
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM public.events WHERE metadata->>'dedup_key'=%s", (event_key,))
                event_id = str(cursor.fetchone()[0])

            correlated = client.post("/api/v1/events/correlate", headers=control, json={
                "event_ids": [event_id], "anomaly_ids": [finding["anomaly_id"]],
            })
            assert correlated.status_code == 200, correlated.text
            incident_id = correlated.json()["data"]["incidents"][0]["incident_id"]
            assert correlated.json()["data"]["attached"] == 2

            context = client.get(f"/api/v1/incidents/{incident_id}/topology-context")
            assert context.status_code == 200, context.text
            assert link_id in context.json()["data"]["referenced_link_ids"]
            before_rca = client.post(f"/api/v1/incidents/{incident_id}/root-cause/analyze", headers=control)
            assert before_rca.status_code == 200, before_rca.text
            rca_run = before_rca.json()["data"]
            assert rca_run["status"] == "CANDIDATES"
            assert rca_run["result"]["candidates"][0]["target_id"] == link_id

            impact = client.post(f"/api/v1/incidents/{incident_id}/impact/analyze", headers=control)
            assert impact.status_code == 200, impact.text
            assert impact.json()["data"]["status"] == "ASSESSED"

            # Exercise the real explanation service and endpoint with a deterministic provider stub.
            monkeypatch.setattr(
                app.state.explanation_service.provider,
                "select",
                lambda context: ModelSelection(ordered_claim_ids=[claim.claim_id for claim in context.claims]),
            )
            explanation = client.post(f"/api/v1/ai/incidents/{incident_id}/explain", headers=control)
            assert explanation.status_code == 200, explanation.text
            payload = explanation.json()["data"]
            assert payload["rca_run_id"] == rca_run["id"]
            assert payload["impact_run_id"] == impact.json()["data"]["id"]
            claim_ids = {claim["claim_id"] for section in (
                "summary", "observed_facts", "candidate_explanations", "failure_chain_explanation",
                "impact_explanation", "uncertainties", "missing_evidence", "limitations",
            ) for claim in payload[section]}
            assert claim_ids and {ref["source_id"] for ref in payload["evidence_references"]}

            after_rca = client.get(f"/api/v1/incidents/{incident_id}/root-causes")
            assert after_rca.status_code == 200 and after_rca.json()["data"] == rca_run
            final_incident = client.get(f"/api/v1/incidents/{incident_id}")
            assert final_incident.status_code == 200
            assert final_incident.json()["data"]["id"] == incident_id
            assert len(final_incident.json()["data"]["events"]) == 1
            assert len(final_incident.json()["data"]["anomalies"]) == 1
    finally:
        # The TestClient context has already shut down the isolated Mininet manager.
        connection.rollback()
        remaining = connection.execute(
            "SELECT count(*) FROM public.devices WHERE metadata->>'fixture'='phase15-e2e' AND metadata->>'run'=%s",
            (fixture_suffix,),
        ).fetchone()[0]
        assert remaining == 0
        connection.close()
