"""Offline tests use a fake adapter; they do not prove Mininet is installed."""
from threading import Event
from types import ModuleType
import sys

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app
from app.network.environment import check_environment
from app.network.errors import NetworkAlreadyRunning, NetworkNotRunning, OperationBusy, ShutdownFailure, StartupFailure
from app.network.manager import NetworkManager
from app.network.mininet_adapter import MininetAdapter
from app.network.models import ConnectivityView, DeviceView, EnvironmentReport, LinkView, TopologyView
from app.network.topology import HOST_NAMES, LINKS, NODES, TOPOLOGY_NAME, build_mininet_topology, validate_topology


TOPOLOGY = TopologyView(
    topology_name=TOPOLOGY_NAME,
    nodes=[DeviceView(id=n.name, name=n.name, device_type=n.device_type, ip_address=n.ip) for n in NODES],
    links=[LinkView(id=f"{edge.source}--{edge.destination}", source=edge.source, destination=edge.destination, status="UP", interface_source="mock0", interface_destination="mock1") for edge in LINKS],
)


class FakeAdapter:
    def __init__(self, *, start_gate=None, fail_start=False, fail_stop=False, connected=True):
        self.calls = []
        self.start_gate = start_gate
        self.fail_start = fail_start
        self.fail_stop = fail_stop
        self.connected = connected

    def start(self):
        self.calls.append("start")
        if self.start_gate:
            self.start_gate.wait(3)
        if self.fail_start:
            raise StartupFailure("Test startup failure")
        return TOPOLOGY

    def stop(self):
        self.calls.append("stop")
        if self.fail_stop:
            raise ShutdownFailure("Test shutdown failure")

    def topology(self):
        self.calls.append("topology")
        return TOPOLOGY

    def test_connectivity(self, timeout):
        self.calls.append("ping")
        return ConnectivityView(hosts=list(HOST_NAMES), packet_loss_percent=0 if self.connected else 50, connected=self.connected)


def ready():
    return EnvironmentReport(available=True, code="READY")


def manager(adapter):
    return NetworkManager(enabled=True, adapter_factory=lambda: adapter, environment_probe=ready)


def test_topology_is_small_connected_tree_without_false_router_claim():
    validate_topology()
    assert len(NODES) == 5
    assert len(LINKS) == 4
    assert {n.device_type for n in NODES} == {"HOST", "SERVER", "SWITCH"}
    adjacency = {n.name: set() for n in NODES}
    for link in LINKS:
        adjacency[link.source].add(link.destination)
        adjacency[link.destination].add(link.source)
    seen = {"h1"}
    frontier = ["h1"]
    while frontier:
        frontier.extend(adjacency[frontier.pop()] - seen)
        seen.update(frontier)
    assert seen == set(adjacency)


def test_host_environment_reports_unavailable_without_installing():
    report = check_environment()
    if not report.available:
        assert report.code != "READY"


def test_mininet_topology_builder_and_partial_start_cleanup(monkeypatch):
    """Fake Mininet package checks exact API calls and cleanup, never host interfaces."""
    parent = ModuleType("mininet")
    parent.__path__ = []
    topo_module = ModuleType("mininet.topo")
    net_module = ModuleType("mininet.net")
    node_module = ModuleType("mininet.node")

    class FakeTopo:
        def __init__(self):
            self.nodes = []
            self.links = []
            self.build()

        def addSwitch(self, name):
            self.nodes.append((name, "SWITCH", None))

        def addHost(self, name, ip):
            self.nodes.append((name, "HOST", ip))

        def addLink(self, source, destination):
            self.links.append((source, destination))

    class FakeNet:
        def __init__(self, **options):
            self.options = options
            self.stopped = False

        def build(self):
            pass

        def start(self):
            raise RuntimeError("mock startup error")

        def stop(self):
            self.stopped = True

    created = []
    def make_net(**options):
        result = FakeNet(**options)
        created.append(result)
        return result
    topo_module.Topo = FakeTopo
    net_module.Mininet = make_net
    node_module.OVSBridge = type("OVSBridge", (), {})
    for name, module in [("mininet", parent), ("mininet.topo", topo_module), ("mininet.net", net_module), ("mininet.node", node_module)]:
        monkeypatch.setitem(sys.modules, name, module)
    topo = build_mininet_topology()
    assert len(topo.nodes) == 5 and len(topo.links) == 4
    assert topo.nodes[2] == ("h1", "HOST", "10.77.0.11/24")

    adapter = MininetAdapter()
    calls = []
    monkeypatch.setattr(adapter, "_acquire_process_lock", lambda: calls.append("lock"))
    monkeypatch.setattr(adapter, "_release_process_lock", lambda: calls.append("unlock"))
    with pytest.raises(StartupFailure):
        adapter.start()
    assert created[0].stopped
    assert adapter._net is None
    assert calls == ["lock", "unlock"]
    assert created[0].options["controller"] is None
    assert created[0].options["switch"] is node_module.OVSBridge


def test_adapter_reports_discovered_nodes_links_and_measured_connectivity():
    class Node:
        def __init__(self, name, address=""):
            self.name, self.address = name, address

        def IP(self):
            return self.address

    class Interface:
        def __init__(self, node, name, up=True):
            self.node, self.name, self.up = node, name, up

        def isUp(self):
            return self.up

    class Link:
        def __init__(self, a, b):
            self.intf1 = Interface(a, f"{a.name}-eth1")
            self.intf2 = Interface(b, f"{b.name}-eth1")

    class Net:
        def __init__(self):
            self.switches = [Node("s1"), Node("s2")]
            self.hosts = [Node("h1", "10.77.0.11"), Node("h2", "10.77.0.12"), Node("server1", "10.77.0.20")]
            nodes = {node.name: node for node in self.switches + self.hosts}
            self.links = [Link(nodes[edge.source], nodes[edge.destination]) for edge in LINKS]

        def pingAll(self, timeout):
            assert timeout == 2
            return 0

    adapter = MininetAdapter()
    adapter._net = Net()
    topology = adapter.topology()
    assert len(topology.nodes) == 5
    assert len(topology.links) == 4
    assert next(node for node in topology.nodes if node.name == "h1").ip_address == "10.77.0.11"
    assert all(edge.status == "UP" for edge in topology.links)
    assert adapter.test_connectivity(timeout=2).connected
    adapter._net.links[0].intf1.up = False
    assert adapter.topology().links[0].status == "DOWN"


def test_lifecycle_duplicate_prevention_and_real_adapter_results():
    fake = FakeAdapter()
    lab = manager(fake)
    try:
        assert lab.get_status().state == "STOPPED"
        with pytest.raises(NetworkNotRunning):
            lab.get_topology()
        lab.start_network().result(timeout=2)
        status = lab.get_status()
        assert (status.state, status.device_count, status.link_count) == ("RUNNING", 5, 4)
        assert status.started_at is not None
        assert len(lab.get_topology().nodes) == 5
        assert lab.test_connectivity().result(timeout=2).connected
        with pytest.raises(NetworkAlreadyRunning):
            lab.start_network()
        lab.stop_network().result(timeout=2)
        assert lab.get_status().state == "STOPPED"
        assert fake.calls.count("stop") == 1
    finally:
        lab.close()


def test_reset_and_restart_are_explicit_fresh_cycles():
    instances = []
    def factory():
        instance = FakeAdapter()
        instances.append(instance)
        return instance
    lab = NetworkManager(enabled=True, adapter_factory=factory, environment_probe=ready)
    try:
        with pytest.raises(NetworkNotRunning):
            lab.reset_network(require_running=True)
        lab.reset_network().result(timeout=2)
        lab.reset_network(require_running=True).result(timeout=2)
        assert len(instances) == 2
        assert instances[0].calls == ["start", "stop"]
        assert lab.get_status().last_operation == "RESTART"
    finally:
        lab.close()
    assert instances[1].calls[-1] == "stop"


def test_startup_failure_never_reports_running_and_can_be_cleaned():
    fake = FakeAdapter(fail_start=True)
    lab = manager(fake)
    try:
        with pytest.raises(StartupFailure):
            lab.start_network().result(timeout=2)
        assert lab.get_status().state == "FAILED"
        with pytest.raises(ShutdownFailure):
            lab.start_network()
        lab.stop_network().result(timeout=2)
        assert lab.get_status().state == "STOPPED"
    finally:
        lab.close()


def test_shutdown_failure_remains_visible_and_retryable():
    fake = FakeAdapter(fail_stop=True)
    lab = manager(fake)
    lab.start_network().result(timeout=2)
    try:
        with pytest.raises(ShutdownFailure):
            lab.stop_network().result(timeout=2)
        assert lab.get_status().state == "FAILED"
        fake.fail_stop = False
        lab.stop_network().result(timeout=2)
        assert lab.get_status().state == "STOPPED"
    finally:
        lab.close()


def test_busy_gate_rejects_conflicting_operations():
    gate = Event()
    fake = FakeAdapter(start_gate=gate)
    lab = manager(fake)
    try:
        pending = lab.start_network()
        assert lab.get_status().state == "STARTING"
        with pytest.raises(OperationBusy):
            lab.stop_network()
        with pytest.raises(OperationBusy):
            lab.reset_network()
        gate.set()
        pending.result(timeout=2)
        assert lab.get_status().state == "RUNNING"
    finally:
        gate.set()
        lab.close()


def test_disconnected_hosts_are_reported_as_failed_measurement():
    lab = manager(FakeAdapter(connected=False))
    try:
        lab.start_network().result(timeout=2)
        result = lab.test_connectivity().result(timeout=2)
        assert not result.connected and result.packet_loss_percent == 50
        assert lab.get_status().last_result == "FAILED"
        assert lab.get_status().state == "RUNNING"
    finally:
        lab.close()


def test_api_disabled_is_explicit_and_health_unchanged():
    app = create_app(Settings(_env_file=None, simulation_enabled=False))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v1/health").json() == {"success": True, "data": {"api": "UP"}}
        status = client.get("/api/v1/network/status")
        assert status.status_code == 200
        assert status.json()["data"]["state"] == "DISABLED"
        assert client.get("/api/v1/topology").status_code == 503
        response = client.post("/api/v1/network/start", headers={"X-NetRCA-Local-Control":"1"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "MININET_UNAVAILABLE"


def test_api_local_gate_and_lifecycle_with_fake_adapter():
    settings = Settings(_env_file=None, cors_origins="http://localhost:3000", simulation_enabled=True)
    app = create_app(settings)
    fake_lab = manager(FakeAdapter())
    app.state.network_manager = fake_lab
    try:
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            assert client.post("/api/v1/network/start").status_code == 403
            assert client.post("/api/v1/network/start", headers={"X-NetRCA-Local-Control":"1", "Origin":"https://evil.example"}).status_code == 403
            headers = {"X-NetRCA-Local-Control":"1"}
            assert client.post("/api/v1/network/start", headers=headers).json()["data"]["state"] == "RUNNING"
            assert client.post("/api/v1/network/start", headers=headers).status_code == 409
            assert len(client.get("/api/v1/topology").json()["data"]["links"]) == 4
            assert client.post("/api/v1/network/connectivity-test", headers=headers).json()["data"]["connected"]
            assert client.post("/api/v1/network/reset", headers=headers).json()["data"]["state"] == "RUNNING"
            assert client.post("/api/v1/network/restart", headers=headers).json()["data"]["state"] == "RUNNING"
            assert client.post("/api/v1/network/stop", headers=headers).json()["data"]["state"] == "STOPPED"
            assert client.get("/api/v1/topology").status_code == 409
    finally:
        fake_lab.close()


def test_api_denies_nonlocal_peer_even_for_read():
    app = create_app(Settings(_env_file=None, simulation_enabled=False))
    with TestClient(app, client=("203.0.113.10", 50000)) as client:
        assert client.get("/api/v1/network/status").status_code == 403
        assert client.post("/api/v1/network/start", headers={"X-NetRCA-Local-Control":"1"}).status_code == 403


def test_api_returns_pending_status_instead_of_waiting_for_stalled_start():
    gate = Event()
    app = create_app(Settings(_env_file=None, simulation_enabled=True, simulation_operation_timeout_seconds=1))
    fake_lab = manager(FakeAdapter(start_gate=gate))
    app.state.network_manager = fake_lab
    try:
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            headers = {"X-NetRCA-Local-Control": "1"}
            pending = client.post("/api/v1/network/start", headers=headers)
            assert pending.status_code == 202
            assert pending.json()["data"]["state"] == "STARTING"
            assert client.post("/api/v1/network/stop", headers=headers).status_code == 409
            gate.set()
            fake_lab._active_future.result(timeout=2)
            assert client.get("/api/v1/network/status").json()["data"]["state"] == "RUNNING"
    finally:
        gate.set()
        fake_lab.close()
