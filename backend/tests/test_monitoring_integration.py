"""Opt-in real Mininet monitoring validation on the isolated Ubuntu lab."""
import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.network.environment import check_environment
from app.network.errors import NetworkNotRunning
from app.network.manager import NetworkManager


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_MININET_TESTS") != "1",
                                reason="Real Mininet test requires explicit opt-in")


def test_real_monitoring_snapshot_and_bounded_probe():
    report = check_environment()
    if not report.available:
        pytest.skip(f"Mininet prerequisite missing: {report.code}")
    manager = NetworkManager(enabled=True)
    try:
        manager.start_network().result(timeout=60)
        snapshot = manager.monitor_snapshot().result(timeout=30)
        assert snapshot.network_state == "RUNNING"
        assert snapshot.collection_status == "COMPLETE", snapshot.errors
        assert {device.name for device in snapshot.devices} == {"s1", "s2", "h1", "h2", "server1"}
        assert len(snapshot.links) == 4
        assert all(link.status == "UP" for link in snapshot.links)
        assert any(interface.rx_bytes is not None for device in snapshot.devices for interface in device.interfaces)
        result = manager.probe_hosts("h1", "h2", count=2, timeout_seconds=2).result(timeout=15)
        assert result.status == "REACHABLE"
        assert result.packets_sent == 2 and result.packets_received == 2
        assert result.packet_loss_percent == 0
        assert result.latency_ms is not None
        manager.stop_network().result(timeout=30)
        with pytest.raises(NetworkNotRunning):
            manager.monitor_snapshot()
    finally:
        manager.close(timeout=30)


def test_real_monitoring_api_preserves_timestamp_source_and_uncertainty_fields():
    report = check_environment()
    if not report.available:
        pytest.skip(f"Mininet prerequisite missing: {report.code}")
    app = create_app(Settings(
        _env_file=None,
        simulation_enabled=True,
        simulation_operation_timeout_seconds=30,
        cors_origins="http://localhost:3000",
    ))
    controls = {"X-NetRCA-Local-Control": "1", "Origin": "http://localhost:3000"}
    reads = {"Origin": "http://localhost:3000"}
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post("/api/v1/network/start", headers=controls).status_code == 200
        snapshot = client.get("/api/v1/network/monitoring", headers=reads)
        assert snapshot.status_code == 200
        data = snapshot.json()["data"]
        assert data["topology_name"] == "netrca_lab_v1"
        assert data["network_state"] == "RUNNING"
        assert data["collection_status"] in {"COMPLETE", "PARTIAL"}
        assert data["counter_unit"] == "bytes_and_packets"
        assert data["observed_at"].endswith("Z")
        assert len(data["devices"]) == 5 and len(data["links"]) == 4
        assert all("error_code" in interface for device in data["devices"] for interface in device["interfaces"])

        probe = client.post("/api/v1/network/monitoring/probe", headers=controls, json={
            "source": "h1", "destination": "server1", "count": 2, "timeout_seconds": 2,
        })
        assert probe.status_code == 200
        reading = probe.json()["data"]
        assert reading["source"] == "h1" and reading["destination"] == "server1"
        assert reading["status"] == "REACHABLE"
        assert reading["packets_sent"] == reading["packets_received"] == 2
        assert reading["packet_loss_percent"] == 0
        assert reading["latency_ms"] is not None
        assert reading["observed_at"].endswith("Z")
        assert client.post("/api/v1/network/stop", headers=controls).status_code == 200
