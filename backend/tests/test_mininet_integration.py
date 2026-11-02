"""Real Mininet test. Opt in ONLY on a dedicated Linux/WSL2 lab with root + OVS."""
import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.network.environment import check_environment
from app.network.errors import StartupFailure
from app.network.manager import NetworkManager
from app.network.mininet_adapter import MininetAdapter
from app.network.topology import HOST_NAMES, LINKS, NODES
from app.network.scenario import DEFAULT_SCENARIO

pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_MININET_TESTS") != "1", reason="Real Mininet test requires explicit opt-in")


def test_real_start_connectivity_reset_stop_and_repeated_start():
    report = check_environment()
    if not report.available:
        pytest.skip(f"Mininet prerequisite missing: {report.code}")
    manager = NetworkManager(enabled=True)
    try:
        manager.start_network().result(timeout=60)
        topology = manager.get_topology()
        assert {node.name for node in topology.nodes} == {node.name for node in NODES}
        assert {frozenset((link.source, link.destination)) for link in topology.links} == {frozenset((link.source, link.destination)) for link in LINKS}
        assert all(link.status == "UP" for link in topology.links)
        assert set(manager.test_connectivity().result(timeout=30).hosts) == set(HOST_NAMES)
        assert manager.test_connectivity().result(timeout=30).connected
        manager.reset_network().result(timeout=60)
        assert manager.test_connectivity().result(timeout=30).connected
        manager.stop_network().result(timeout=30)
        manager.start_network().result(timeout=60)
        assert manager.test_connectivity().result(timeout=30).connected
        manager.stop_network().result(timeout=30)
        assert manager.get_status().state == "STOPPED"
    finally:
        manager.close(timeout=30)


def test_real_partial_startup_cleanup_allows_retry(monkeypatch):
    report = check_environment()
    if not report.available:
        pytest.skip(f"Mininet prerequisite missing: {report.code}")

    original = MininetAdapter.test_connectivity

    def fail_after_network_start(self, timeout):
        raise StartupFailure("Injected startup verification failure")

    monkeypatch.setattr(MininetAdapter, "test_connectivity", fail_after_network_start)
    manager = NetworkManager(enabled=True)
    try:
        with pytest.raises(StartupFailure):
            manager.start_network().result(timeout=60)
        monkeypatch.setattr(MininetAdapter, "test_connectivity", original)
        retry = NetworkManager(enabled=True)
        try:
            retry.start_network().result(timeout=60)
            assert retry.test_connectivity().result(timeout=30).connected
            retry.stop_network().result(timeout=30)
        finally:
            retry.close(timeout=30)
    finally:
        manager.close(timeout=30)


def test_real_local_api_start_topology_connectivity_and_stop():
    report = check_environment()
    if not report.available:
        pytest.skip(f"Mininet prerequisite missing: {report.code}")
    settings = Settings(
        _env_file=None,
        simulation_enabled=True,
        simulation_operation_timeout_seconds=30,
        cors_origins="http://localhost:3000",
    )
    app = create_app(settings)
    headers = {"X-NetRCA-Local-Control": "1", "Origin": "http://localhost:3000"}
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        started = client.post("/api/v1/network/start", headers=headers)
        assert started.status_code == 200
        assert started.json()["data"]["state"] == "RUNNING"
        assert started.json()["data"]["topology_name"] == DEFAULT_SCENARIO.name

        graph = client.get("/api/v1/topology/analysis?source=live", headers={"Origin": "http://localhost:3000"})
        assert graph.status_code == 200
        assert graph.json()["data"]["connected"] is True
        assert {item["id"] for item in graph.json()["data"]["devices"]} == {str(item.id) for item in DEFAULT_SCENARIO.nodes}

        connectivity = client.post("/api/v1/network/connectivity-test", headers=headers)
        assert connectivity.status_code == 200
        assert connectivity.json()["data"]["connected"] is True
        assert connectivity.json()["data"]["packet_loss_percent"] == 0

        stopped = client.post("/api/v1/network/stop", headers=headers)
        assert stopped.status_code == 200
        assert stopped.json()["data"]["state"] == "STOPPED"
        assert client.get("/api/v1/topology/analysis?source=live").status_code == 409
