import json
from datetime import timezone
from subprocess import TimeoutExpired
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.monitoring.service import _command, capture, probe
from app.network.errors import NetworkNotRunning
from app.network.manager import NetworkManager
from app.network.models import DeviceView, EnvironmentReport, LinkView, TopologyView


def _ip_output(name, *, bytes_received=0):
    return json.dumps([{"ifname": name, "flags": ["UP", "LOWER_UP"], "operstate": "UP",
                        "stats64": {"rx": {"bytes": bytes_received, "packets": 0, "errors": 0},
                                    "tx": {"bytes": 0, "packets": 0, "errors": 0}}}]).encode()


class Process:
    def __init__(self, output=b"", returncode=0, *, timeout=False):
        self.output = output
        self.returncode = returncode
        self.timeout = timeout
        self.killed = False

    def communicate(self, timeout):
        if self.timeout and not self.killed:
            raise TimeoutExpired("test", timeout)
        return self.output, b""

    def kill(self):
        self.killed = True


class Node:
    def __init__(self, name, interface, *, missing=False, ping_output=b"", ping_code=0, ping_timeout=False):
        self.name = name
        self.interface = interface
        self.missing = missing
        self.ping_output = ping_output
        self.ping_code = ping_code
        self.ping_timeout = ping_timeout
        self.commands = []

    def intfList(self):
        return [SimpleNamespace(name=self.interface)]

    def IP(self):
        return "10.77.0.12" if self.name == "h2" else "10.77.0.11"

    def popen(self, args, **kwargs):
        self.commands.append(args)
        if args[0] == "ip":
            return Process(returncode=1) if self.missing else Process(_ip_output(self.interface))
        return Process(self.ping_output, self.ping_code, timeout=self.ping_timeout)


def _net(*, missing=False, ping_output=b"", ping_code=0, ping_timeout=False):
    switch = Node("s1", "s1-eth1")
    host1 = Node("h1", "h1-eth0", missing=missing, ping_output=ping_output,
                 ping_code=ping_code, ping_timeout=ping_timeout)
    host2 = Node("h2", "h2-eth0")
    left = SimpleNamespace(node=switch, name="s1-eth1")
    right = SimpleNamespace(node=host1, name="h1-eth0")
    return SimpleNamespace(switches=[switch], hosts=[host1, host2],
                           links=[SimpleNamespace(intf1=left, intf2=right)]), host1


def test_snapshot_reports_real_zero_counters_units_links_and_utc_time():
    net, host = _net()
    snapshot = capture(net)
    assert snapshot.network_state == "RUNNING"
    assert snapshot.collection_status == "COMPLETE"
    assert snapshot.observed_at.tzinfo == timezone.utc
    assert snapshot.counter_unit == "bytes_and_packets"
    assert snapshot.devices[1].interfaces[0].rx_bytes == 0
    assert snapshot.devices[1].interfaces[0].rx_errors == 0
    assert snapshot.links[0].status == "UP"
    assert host.commands[0] == ["ip", "-j", "-s", "link", "show", "dev", "h1-eth0"]


def test_snapshot_keeps_missing_interface_unavailable_and_partial():
    net, _ = _net(missing=True)
    snapshot = capture(net)
    interface = snapshot.devices[1].interfaces[0]
    assert snapshot.collection_status == "PARTIAL"
    assert interface.status == "UNAVAILABLE"
    assert interface.rx_bytes is None
    assert interface.error_code == "INTERFACE_MISSING"
    assert snapshot.links[0].status == "UNKNOWN"


def test_probe_success_loss_timeout_and_invalid_host():
    success = b"2 packets transmitted, 2 received, 0% packet loss\nrtt min/avg/max/mdev = 0.010/0.020/0.030/0.001 ms\n"
    net, host = _net(ping_output=success)
    result = probe(net, "h1", "h2", count=2, timeout_seconds=2)
    assert result.status == "REACHABLE" and result.packet_loss_percent == 0
    assert result.latency_ms == 0.020 and result.observed_at.tzinfo == timezone.utc
    assert host.commands[-1] == ["ping", "-n", "-c", "2", "-W", "2", "10.77.0.12"]
    loss = b"2 packets transmitted, 0 received, 100% packet loss\n"
    net, _ = _net(ping_output=loss, ping_code=1)
    result = probe(net, "h1", "h2", count=2, timeout_seconds=2)
    assert result.status == "UNREACHABLE" and result.packet_loss_percent == 100
    assert result.latency_ms is None
    net, _ = _net(ping_timeout=True)
    result = probe(net, "h1", "h2", count=1, timeout_seconds=1)
    assert result.status == "TIMEOUT" and result.packet_loss_percent is None
    with pytest.raises(ValueError):
        probe(net, "h1", "outside", count=1, timeout_seconds=1)


def test_command_kills_timed_out_process():
    net, host = _net(ping_timeout=True)
    process = host.popen(["ping"])
    host.popen = lambda *args, **kwargs: process
    output, code, error = _command(host, ["ping"], timeout=0.1)
    assert (output, code, error) == (None, None, "COMMAND_TIMEOUT")
    assert process.killed


class Adapter:
    def start(self):
        return TopologyView(topology_name="netrca_lab_v1", nodes=[
            DeviceView(id="s1", name="s1", device_type="SWITCH"),
            DeviceView(id="h1", name="h1", device_type="HOST"),
            DeviceView(id="h2", name="h2", device_type="HOST"),
        ], links=[LinkView(id="h1--s1", source="h1", destination="s1", status="UP",
                          interface_source="h1-eth0", interface_destination="s1-eth1")])

    def stop(self):
        pass

    def monitor_snapshot(self):
        net, _ = _net()
        return capture(net)

    def probe_hosts(self, source, destination, count, timeout_seconds):
        output = b"2 packets transmitted, 2 received, 0% packet loss\nrtt min/avg/max/mdev = 0.010/0.020/0.030/0.001 ms\n"
        net, _ = _net(ping_output=output)
        return probe(net, source, destination, count=count, timeout_seconds=timeout_seconds)


def test_api_running_stopped_validation_and_local_access():
    app = create_app(Settings(_env_file=None, simulation_enabled=True))
    manager = NetworkManager(enabled=True, adapter_factory=Adapter,
                             environment_probe=lambda: EnvironmentReport(available=True, code="READY"))
    app.state.network_manager = manager
    try:
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            stopped = client.get("/api/v1/network/monitoring")
            assert stopped.status_code == 200
            assert stopped.json()["data"]["collection_status"] == "UNAVAILABLE"
            assert stopped.json()["data"]["devices"] == []
            assert client.post("/api/v1/network/monitoring/probe", json={"source": "h1", "destination": "h2"},
                               headers={"X-NetRCA-Local-Control": "1"}).status_code == 409
            manager.start_network().result(timeout=2)
            snapshot = client.get("/api/v1/network/monitoring")
            assert snapshot.status_code == 200
            assert len(snapshot.json()["data"]["devices"]) == 3
            url = "/api/v1/network/monitoring/probe"
            payload = {"source": "h1", "destination": "h2"}
            assert client.post(url, json=payload).status_code == 403
            assert client.post(url, json={**payload, "count": 99},
                               headers={"X-NetRCA-Local-Control": "1"}).status_code == 422
            assert client.post(url, json={"source": "h1", "destination": "outside"},
                               headers={"X-NetRCA-Local-Control": "1"}).status_code == 400
            response = client.post(url, json=payload, headers={"X-NetRCA-Local-Control": "1"})
            assert response.status_code == 200
            assert response.json()["data"]["latency_ms"] == 0.020
            assert manager.get_status().state == "RUNNING"
    finally:
        manager.close(timeout=2)
    remote = create_app(Settings(_env_file=None))
    with TestClient(remote, client=("203.0.113.9", 50000)) as client:
        assert client.get("/api/v1/network/monitoring").status_code == 403


def test_monitoring_error_is_reported_without_marking_running_lab_failed():
    class FailingAdapter(Adapter):
        def monitor_snapshot(self):
            raise RuntimeError("internal observation failure")

    app = create_app(Settings(_env_file=None, simulation_enabled=True))
    manager = NetworkManager(enabled=True, adapter_factory=FailingAdapter,
                             environment_probe=lambda: EnvironmentReport(available=True, code="READY"))
    app.state.network_manager = manager
    try:
        manager.start_network().result(timeout=2)
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            result = client.get("/api/v1/network/monitoring")
            assert result.status_code == 503
            assert result.json()["error"]["code"] == "MONITORING_FAILED"
            assert "internal observation failure" not in result.text
            assert manager.get_status().state == "RUNNING"
    finally:
        manager.close(timeout=2)
