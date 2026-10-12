"""Real Mininet test. Opt in ONLY on a dedicated Linux/WSL2 lab with root + OVS."""
import os

import pytest

from app.network.environment import check_environment
from app.network.errors import StartupFailure
from app.network.manager import NetworkManager
from app.network.mininet_adapter import MininetAdapter
from app.network.topology import HOST_NAMES, LINKS, NODES

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
