"""Opt-in validation against the owned Mininet instance in Ubuntu WSL2."""
import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.faults.adapter import _qdisc, _up
from app.faults.controller import FaultController
from app.faults.models import FaultRequest
from app.faults.store import FaultUnmapped
from app.network.environment import check_environment
from app.network.manager import NetworkManager
from app.main import create_app


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_FAULT_TESTS") != "1",
                                reason="Real fault test requires explicit opt-in")


class UnmappedStore:
    def save(self, record, state):
        raise FaultUnmapped()


def test_real_faults_apply_restore_expire_and_stop_cleanup():
    report = check_environment()
    if not report.available:
        pytest.skip(f"Mininet prerequisite missing: {report.code}")
    manager = NetworkManager(enabled=True)
    controller = FaultController(manager, UnmappedStore(), enabled=True, timeout=20)
    try:
        manager.start_network().result(timeout=60)
        adapter = manager._adapter
        h1 = adapter._net.get("h1")
        assert _up(h1, "h1-eth0")
        assert _qdisc(h1, "h1-eth0") == "noqueue"

        interface = controller.inject(FaultRequest(fault_type="INTERFACE_FAILURE", device="h1",
                                                   interface="h1-eth0"))
        assert not _up(h1, "h1-eth0")
        snapshot = manager.monitor_snapshot().result(timeout=20)
        h1_reading = next(device for device in snapshot.devices if device.name == "h1")
        assert any(item.name == "h1-eth0" and item.status == "DOWN" for item in h1_reading.interfaces)
        assert any(item.status == "DOWN" and {item.source, item.destination} == {"h1", "s1"}
                   for item in snapshot.links)
        assert controller.recover(interface.id).status == "COMPLETED"
        assert _up(h1, "h1-eth0")

        link = controller.inject(FaultRequest(fault_type="LINK_FAILURE", source="h1", destination="s1"))
        assert all(not _up(adapter._net.get(item["device"]), item["interface"])
                   for item in controller._states[link.id]["targets"])
        controller.recover(link.id)
        assert all(_up(adapter._net.get(item["device"]), item["interface"])
                   for item in controller._states[link.id]["targets"])

        loss = controller.inject(FaultRequest(fault_type="PACKET_LOSS", device="h1",
                                              interface="h1-eth0", packet_loss_percent=100))
        assert _qdisc(h1, "h1-eth0") == "netem"
        probe = manager.probe_hosts("h1", "h2", count=1, timeout_seconds=1).result(timeout=10)
        assert probe.status == "UNREACHABLE" and probe.packet_loss_percent == 100
        assert controller.recover(loss.id).status == "COMPLETED"
        assert _qdisc(h1, "h1-eth0") == "noqueue"

        latency = controller.inject(FaultRequest(fault_type="HIGH_LATENCY", device="h1",
                                                 interface="h1-eth0", latency_ms=50, duration_seconds=1))
        assert _qdisc(h1, "h1-eth0") == "netem"
        controller._expire(latency.id)
        assert controller.get(latency.id).end_reason == "EXPIRED"
        assert _qdisc(h1, "h1-eth0") == "noqueue"

        stopped = controller.inject(FaultRequest(fault_type="INTERFACE_FAILURE", device="h1",
                                                 interface="h1-eth0"))
        manager.stop_network().result(timeout=30)
        assert controller.get(stopped.id).end_reason == "LAB_STOPPED"
    finally:
        manager.close(timeout=30)


def test_real_fault_api_exposes_observed_failure_and_recovery():
    report = check_environment()
    if not report.available:
        pytest.skip(f"Mininet prerequisite missing: {report.code}")
    app = create_app(Settings(
        _env_file=None,
        simulation_enabled=True,
        fault_injection_enabled=True,
        simulation_operation_timeout_seconds=30,
        cors_origins="http://localhost:3000",
    ))
    app.state.fault_controller.store = UnmappedStore()
    controls = {"X-NetRCA-Local-Control": "1", "Origin": "http://localhost:3000"}
    reads = {"Origin": "http://localhost:3000"}
    with TestClient(app, client=("127.0.0.1", 50001)) as client:
        assert client.post("/api/v1/network/start", headers=controls).status_code == 200
        fault_types = client.get("/api/v1/faults/types", headers=reads)
        assert fault_types.status_code == 200
        assert set(fault_types.json()["data"]) == {
            "INTERFACE_FAILURE", "LINK_FAILURE", "PACKET_LOSS", "HIGH_LATENCY",
        }
        injected = client.post("/api/v1/faults/inject", headers=controls, json={
            "fault_type": "INTERFACE_FAILURE", "device": "h1", "interface": "h1-eth0",
            "duration_seconds": 30, "severity": "HIGH",
        })
        assert injected.status_code == 201
        record = injected.json()["data"]
        assert record["status"] == "ACTIVE" and record["storage_status"] == "UNMAPPED"
        history = client.get("/api/v1/faults?page=1&limit=100", headers=reads)
        assert history.status_code == 200 and history.json()["pagination"]["total"] == 1

        failed_snapshot = client.get("/api/v1/network/monitoring", headers=reads).json()["data"]
        h1 = next(device for device in failed_snapshot["devices"] if device["name"] == "h1")
        assert any(interface["name"] == "h1-eth0" and interface["status"] == "DOWN"
                   for interface in h1["interfaces"])
        assert any(link["status"] == "DOWN" and {link["source"], link["destination"]} == {"h1", "s1"}
                   for link in failed_snapshot["links"])

        recovered = client.post(f"/api/v1/faults/{record['id']}/recover", headers=controls)
        assert recovered.status_code == 200
        assert recovered.json()["data"]["restoration_result"] == "SUCCEEDED"
        restored_snapshot = client.get("/api/v1/network/monitoring", headers=reads).json()["data"]
        restored_h1 = next(device for device in restored_snapshot["devices"] if device["name"] == "h1")
        assert any(interface["name"] == "h1-eth0" and interface["status"] == "UP"
                   for interface in restored_h1["interfaces"])
        assert client.post("/api/v1/network/stop", headers=controls).status_code == 200
