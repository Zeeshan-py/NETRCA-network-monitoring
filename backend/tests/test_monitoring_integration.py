"""Opt-in real Mininet monitoring validation on the isolated Ubuntu lab."""
import os

import pytest

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
