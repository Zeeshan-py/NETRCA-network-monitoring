"""Offline fault safety tests; real Mininet coverage is opt-in separately."""
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.faults.adapter import FaultApplyFailure, FaultOperationError, InvalidFaultTarget, UnsafeFaultTarget, apply, restore
from app.faults.controller import FaultBusy, FaultController
from app.faults.models import FaultRecord, FaultRequest
from app.faults.store import FaultStore
from app.main import create_app
from app.network.errors import ShutdownFailure
from app.network.manager import NetworkManager
from app.network.models import EnvironmentReport
from app.network.topology import LINKS


class Process:
    def __init__(self, output=b""):
        self.output = output
        self.returncode = 0

    def communicate(self, timeout):
        return self.output, b""


class Node:
    def __init__(self, name):
        self.name = name
        self.interfaces = []
        self.up = {}
        self.qdisc = {}
        self.calls = []

    def intfList(self):
        return self.interfaces

    def popen(self, args, **_kwargs):
        self.calls.append(args)
        name = args[args.index("dev") + 1]
        if args[:3] == ["ip", "-j", "link"]:
            return Process(json.dumps([{"ifname": name, "flags": ["UP"] if self.up[name] else []}]).encode())
        if args[:3] == ["tc", "-j", "qdisc"]:
            return Process(json.dumps([{"kind": self.qdisc[name], "root": True}]).encode())
        if args[:3] == ["ip", "link", "set"]:
            self.up[name] = args[-1] == "up"
        elif args[:3] == ["tc", "qdisc", "replace"]:
            self.qdisc[name] = "netem"
        elif args[:3] == ["tc", "qdisc", "del"]:
            self.qdisc[name] = "noqueue"
        else:
            raise AssertionError(args)
        return Process()


def net():
    nodes = {name: Node(name) for name in ("s1", "s2", "h1", "h2", "server1")}
    links = []
    for edge in LINKS:
        ends = []
        for name in (edge.source, edge.destination):
            node = nodes[name]
            interface = SimpleNamespace(node=node, name=f"{name}-eth{len(node.interfaces)}")
            node.interfaces.append(interface)
            node.up[interface.name] = True
            node.qdisc[interface.name] = "noqueue"
            ends.append(interface)
        links.append(SimpleNamespace(intf1=ends[0], intf2=ends[1]))
    lab = SimpleNamespace(hosts=[nodes[name] for name in ("h1", "h2", "server1")],
                          switches=[nodes[name] for name in ("s1", "s2")], links=links)
    return lab, nodes


def test_request_rejects_invalid_targets_and_parameters():
    for body in (
        {"fault_type": "LINK_FAILURE", "source": "s1", "destination": "s1"},
        {"fault_type": "PACKET_LOSS", "device": "h1", "interface": "h1-eth0", "packet_loss_percent": 101},
        {"fault_type": "HIGH_LATENCY", "device": "h1", "interface": "h1-eth0", "latency_ms": -1},
        {"fault_type": "INTERFACE_FAILURE", "device": "h1", "interface": "h1-eth0", "source": "h2"},
        {"fault_type": "INTERFACE_FAILURE", "device": "h1", "interface": "h1-eth0", "extra": "unsafe"},
    ):
        with pytest.raises(ValidationError):
            FaultRequest(**body)


def test_interface_and_link_restoration_preserve_initial_state():
    lab, nodes = net()
    request = FaultRequest(fault_type="INTERFACE_FAILURE", device="h1", interface="h1-eth0")
    state = apply(lab, request)
    assert nodes["h1"].up["h1-eth0"] is False
    restore(lab, state)
    assert nodes["h1"].up["h1-eth0"] is True
    link = FaultRequest(fault_type="LINK_FAILURE", source="h1", destination="s1")
    state = apply(lab, link)
    assert all(nodes[item["device"]].up[item["interface"]] is False for item in state["targets"])
    restore(lab, state)
    assert all(nodes[item["device"]].up[item["interface"]] is True for item in state["targets"])


def test_shaping_restores_qdisc_and_rejects_existing_shaping():
    lab, nodes = net()
    for kind, value in (("PACKET_LOSS", {"packet_loss_percent": 100}),
                        ("HIGH_LATENCY", {"latency_ms": 50})):
        request = FaultRequest(fault_type=kind, device="h1", interface="h1-eth0", **value)
        state = apply(lab, request)
        assert nodes["h1"].qdisc["h1-eth0"] == "netem"
        restore(lab, state)
        assert nodes["h1"].qdisc["h1-eth0"] == "noqueue"
    nodes["h1"].qdisc["h1-eth0"] = "fq_codel"
    with pytest.raises(UnsafeFaultTarget):
        apply(lab, FaultRequest(fault_type="PACKET_LOSS", device="h1", interface="h1-eth0",
                                packet_loss_percent=10))


def test_rejects_non_owned_and_switch_shaping_targets():
    lab, _ = net()
    with pytest.raises(InvalidFaultTarget):
        apply(lab, FaultRequest(fault_type="INTERFACE_FAILURE", device="h1", interface="eth0"))
    with pytest.raises(InvalidFaultTarget):
        apply(lab, FaultRequest(fault_type="LINK_FAILURE", source="h1", destination="h2"))
    with pytest.raises(UnsafeFaultTarget):
        apply(lab, FaultRequest(fault_type="HIGH_LATENCY", device="s1", interface="s1-eth0", latency_ms=5))


def test_partial_link_application_rolls_back_first_endpoint():
    lab, nodes = net()
    second = lab.links[0].intf2.node
    original = second.popen

    def fail_down(args, **kwargs):
        if args[:3] == ["ip", "link", "set"] and args[-1] == "down":
            return SimpleNamespace(returncode=1, communicate=lambda timeout: (b"", b""))
        return original(args, **kwargs)

    second.popen = fail_down
    with pytest.raises(FaultApplyFailure) as caught:
        apply(lab, FaultRequest(fault_type="LINK_FAILURE", source="h1", destination="s1"))
    assert not caught.value.needs_restore
    assert all(nodes[item["device"]].up[item["interface"]] for item in caught.value.state["targets"])


class Adapter:
    def __init__(self):
        self.active = False
        self.restores = 0

    def start(self):
        return SimpleNamespace(nodes=[1], links=[1])

    def stop(self):
        self.active = False

    def apply_fault(self, request):
        self.active = True
        return {"mode": "admin", "targets": [{"device": "h1", "interface": "h1-eth0", "was_up": True}]}

    def restore_fault(self, state):
        self.restores += 1
        self.active = False


class FailingRestoreAdapter(Adapter):
    def restore_fault(self, state):
        raise FaultOperationError("Simulated restoration failure")


class UnmappedStore:
    def save(self, record, state):
        from app.faults.store import FaultUnmapped
        raise FaultUnmapped()


def test_controller_serializes_and_restores_on_recovery_expiry_and_stop():
    adapter = Adapter()
    manager = NetworkManager(enabled=True, adapter_factory=lambda: adapter,
                             environment_probe=lambda: EnvironmentReport(available=True, code="READY"))
    controller = FaultController(manager, UnmappedStore(), enabled=True, timeout=1)
    try:
        manager.start_network().result(timeout=5)
        request = FaultRequest(fault_type="INTERFACE_FAILURE", device="h1", interface="h1-eth0",
                               duration_seconds=1)
        first = controller.inject(request)
        assert first.storage_status == "UNMAPPED" and first.status == "ACTIVE"
        with pytest.raises(FaultBusy):
            controller.inject(request)
        assert controller.recover(first.id).status == "COMPLETED"
        second = controller.inject(request)
        controller._expire(second.id)
        assert controller.get(second.id).end_reason == "EXPIRED"
        third = controller.inject(request)
        manager.stop_network().result(timeout=5)
        assert controller.get(third.id).end_reason == "LAB_STOPPED"
        assert adapter.restores == 3 and not adapter.active
    finally:
        manager.close()


def test_failed_restoration_remains_active_and_repeat_recovery_is_safe():
    adapter = FailingRestoreAdapter()
    manager = NetworkManager(enabled=True, adapter_factory=lambda: adapter,
                             environment_probe=lambda: EnvironmentReport(available=True, code="READY"))
    controller = FaultController(manager, UnmappedStore(), enabled=True, timeout=1)
    try:
        manager.start_network().result(timeout=5)
        record = controller.inject(FaultRequest(fault_type="INTERFACE_FAILURE", device="h1",
                                                interface="h1-eth0"))
        failed = controller.recover(record.id)
        assert failed.status == "ACTIVE" and failed.restoration_result == "FAILED"
        adapter.restore_fault = Adapter.restore_fault.__get__(adapter, Adapter)
        assert controller.recover(record.id).status == "COMPLETED"
        assert controller.recover(record.id).status == "COMPLETED"
    finally:
        manager.close()


def test_failed_lab_stop_keeps_unrestored_fault_recoverable():
    adapter = FailingRestoreAdapter()
    adapter.stop = lambda: (_ for _ in ()).throw(ShutdownFailure("Simulated stop failure"))
    manager = NetworkManager(enabled=True, adapter_factory=lambda: adapter,
                             environment_probe=lambda: EnvironmentReport(available=True, code="READY"))
    controller = FaultController(manager, UnmappedStore(), enabled=True, timeout=1)
    try:
        manager.start_network().result(timeout=5)
        record = controller.inject(FaultRequest(fault_type="INTERFACE_FAILURE", device="h1",
                                                interface="h1-eth0"))
        with pytest.raises(ShutdownFailure):
            manager.stop_network().result(timeout=5)
        assert controller.get(record.id).status == "ACTIVE"
        adapter.restore_fault = Adapter.restore_fault.__get__(adapter, Adapter)
        assert controller.recover(record.id).status == "COMPLETED"
    finally:
        adapter.stop = Adapter.stop.__get__(adapter, Adapter)
        manager.close()


def test_store_uses_existing_table_and_records_lifecycle(monkeypatch):
    calls = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def execute(self, sql, params):
            calls.append((sql, params))

        def fetchone(self):
            return {"id": uuid4()}

    class Connection:
        def cursor(self, **_kwargs):
            return Cursor()

    @contextmanager
    def fake_transaction(_settings):
        yield Connection()

    monkeypatch.setattr("app.faults.store.transaction", fake_transaction)
    from datetime import datetime, timedelta, timezone
    started = datetime.now(timezone.utc)
    record = FaultRecord(id=uuid4(), fault_type="INTERFACE_FAILURE", status="ACTIVE",
                         target={"device": "h1", "interface": "h1-eth0"},
                         parameters={"duration_seconds": 30}, severity="MEDIUM", started_at=started,
                         expires_at=started + timedelta(seconds=30))
    store = FaultStore(Settings(_env_file=None))
    state = {"mode": "admin", "targets": [{"device": "h1", "interface": "h1-eth0", "was_up": True}]}
    store.save(record, state)
    assert "public.fault_injections" in calls[-1][0]
    assert calls[-1][1][-1] == "ACTIVE"
    record.status = "COMPLETED"
    record.ended_at = datetime.now(timezone.utc)
    record.end_reason = "RECOVERED"
    record.restoration_result = "SUCCEEDED"
    store.save(record, state)
    assert calls[-1][1][-1] == "COMPLETED"
    assert calls[-1][1][-2] == record.ended_at


def test_api_blocks_remote_and_unconfigured_controls():
    settings = Settings(_env_file=None, simulation_enabled=False, fault_injection_enabled=False)
    app = create_app(settings)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v1/faults/types").status_code == 200
        body = {"fault_type": "INTERFACE_FAILURE", "device": "h1", "interface": "h1-eth0"}
        assert client.post("/api/v1/faults/inject", json=body).status_code == 403
        assert client.post("/api/v1/faults/inject", json=body,
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
    settings = Settings(_env_file=None, simulation_enabled=True, fault_injection_enabled=True)
    app = create_app(settings)
    with TestClient(app, client=("192.0.2.10", 50000)) as client:
        assert client.get("/api/v1/faults/types").json()["error"]["code"] == "LOCAL_ONLY"
        assert client.post("/api/v1/faults/inject", json=body,
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 403
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post("/api/v1/faults/inject", json=body).json()["error"]["code"] == "LOCAL_CONTROL_REQUIRED"
        assert client.post("/api/v1/faults/inject", json=body,
                           headers={"X-NetRCA-Local-Control": "1"}).status_code == 503


def test_api_fault_lifecycle_with_owned_fake_lab():
    settings = Settings(_env_file=None, simulation_enabled=True, fault_injection_enabled=True)
    app = create_app(settings)
    adapter = Adapter()
    manager = NetworkManager(enabled=True, adapter_factory=lambda: adapter,
                             environment_probe=lambda: EnvironmentReport(available=True, code="READY"))
    controller = FaultController(manager, UnmappedStore(), enabled=True, timeout=1)
    app.state.fault_controller = controller
    headers = {"X-NetRCA-Local-Control": "1"}
    try:
        manager.start_network().result(timeout=5)
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            body = {"fault_type": "INTERFACE_FAILURE", "device": "h1", "interface": "h1-eth0"}
            created = client.post("/api/v1/faults/inject", json=body, headers=headers)
            assert created.status_code == 201
            identifier = created.json()["data"]["id"]
            assert client.get(f"/api/v1/faults/{identifier}").json()["data"]["status"] == "ACTIVE"
            assert client.get("/api/v1/faults").json()["pagination"]["total"] == 1
            assert client.post("/api/v1/faults/inject", json=body, headers=headers).status_code == 409
            assert client.post(f"/api/v1/faults/{identifier}/recover", headers=headers).json()["data"]["status"] == "COMPLETED"
            assert client.post(f"/api/v1/faults/{identifier}/recover", headers=headers).status_code == 200
            assert client.post("/api/v1/faults/reset", headers=headers).json()["data"] == []
    finally:
        manager.close()
