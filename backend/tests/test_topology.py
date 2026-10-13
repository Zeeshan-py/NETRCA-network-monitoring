from uuid import UUID, uuid4
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.network.models import DeviceView, LinkView, TopologyView
from app.topology.graph import TopologyGraph, from_mininet
from app.topology.models import Device, DeviceCreate, Link, LinkCreate, Snapshot
from app.topology.store import TopologyConflict, TopologyNotFound


def sample_graph():
    a, b, c = uuid4(), uuid4(), uuid4()
    devices = [Device(id=a, name="s1", device_type="SWITCH", status="HEALTHY"),
               Device(id=b, name="h1", device_type="HOST", status="HEALTHY"),
               Device(id=c, name="h2", device_type="HOST", status="DOWN")]
    links = [Link(id=uuid4(), source_device_id=a, destination_device_id=b, status="UP")]
    return TopologyGraph(devices, links), (a, b, c)


def test_graph_creation_retrieval_components_and_neighbors():
    graph, (a, b, c) = sample_graph()
    result = graph.validate()
    assert result.valid
    assert {frozenset(group) for group in result.components} == {frozenset((a, b)), frozenset((c,))}
    assert graph.neighbors(a) == [b]
    assert graph.neighbors(c) == []
    assert graph.path(a, b) == [a, b]
    assert graph.path(a, c) is None
    with pytest.raises(KeyError):
        graph.neighbors(uuid4())


def test_graph_rejects_unknown_self_and_duplicate_links_and_devices():
    graph, (a, b, _) = sample_graph()
    graph.devices.append(Device(id=a, name="s1", device_type="SWITCH", status="DOWN"))
    graph.links.extend([
        Link(id=uuid4(), source_device_id=b, destination_device_id=a, status="UP"),
        Link(id=uuid4(), source_device_id=a, destination_device_id=a, status="UP"),
        Link(id=uuid4(), source_device_id=a, destination_device_id=uuid4(), status="UP"),
    ])
    assert set(graph.validate().errors) == {
        "DUPLICATE_DEVICE_ID", "DUPLICATE_OR_EMPTY_DEVICE_NAME", "DUPLICATE_LINK",
        "SELF_LINK", "INVALID_LINK_ENDPOINT",
    }
    with pytest.raises(ValueError):
        graph.neighbors(a)


def test_create_models_reject_bad_address_and_link_measurements():
    with pytest.raises(ValidationError):
        DeviceCreate(name="host", device_type="HOST", status="HEALTHY", ip_address="not-an-ip")
    with pytest.raises(ValidationError):
        LinkCreate(source_device_id=uuid4(), destination_device_id=uuid4(),
                   status="UP", packet_loss_percent=101)


def test_phase3_projection_has_stable_ids_without_claiming_health_or_storage():
    view = TopologyView(topology_name="lab", nodes=[
        DeviceView(id="s1", name="s1", device_type="SWITCH"),
        DeviceView(id="h1", name="h1", device_type="HOST", ip_address="10.0.0.1/24"),
    ], links=[LinkView(id="h1--s1", source="h1", destination="s1", status="UP",
                      interface_source="h1-eth0", interface_destination="s1-eth1")])
    first, second = from_mininet(view), from_mininet(view)
    assert first.validate().valid
    assert [device.id for device in first.devices] == [device.id for device in second.devices]
    assert all(device.status == "PRESENT" for device in first.devices)
    assert first.links[0].source_device_id == first.devices[1].id
    view.links[0].destination = "missing"
    assert from_mininet(view).validate().errors == ["INVALID_LINK_ENDPOINT"]


class FakeStore:
    def __init__(self):
        self.graph, _ = sample_graph()
        self.snapshots = []

    def list_snapshots(self, limit=20):
        return self.snapshots[:limit]

    def create_snapshot(self, reason=None):
        if not self.graph.validate().valid:
            raise TopologyConflict("INVALID_TOPOLOGY")
        now = datetime.now(timezone.utc)
        item = Snapshot(id=uuid4(), snapshot_time=now, created_at=now, reason=reason,
                        topology_data={"nodes": [node.model_dump(mode="json") for node in self.graph.devices],
                                       "links": [link.model_dump(mode="json") for link in self.graph.links]})
        self.snapshots.insert(0, item)
        return item

    def load(self):
        return self.graph

    def get_device(self, device_id):
        for item in self.graph.devices:
            if item.id == device_id:
                return item
        raise TopologyNotFound("DEVICE_NOT_FOUND")

    def get_link(self, link_id):
        for item in self.graph.links:
            if item.id == link_id:
                return item
        raise TopologyNotFound("LINK_NOT_FOUND")

    def create_device(self, value: DeviceCreate):
        if any(item.name == value.name for item in self.graph.devices):
            raise TopologyConflict("DUPLICATE_DEVICE")
        item = Device(id=uuid4(), **value.model_dump())
        self.graph.devices.append(item)
        return item

    def create_link(self, value: LinkCreate):
        if value.source_device_id == value.destination_device_id:
            raise TopologyConflict("SELF_LINK")
        item = Link(id=uuid4(), **value.model_dump())
        self.graph.links.append(item)
        return item


def test_stored_topology_api_read_create_and_errors():
    settings = Settings(_env_file=None, topology_writes_enabled=True)
    app = create_app(settings)
    app.state.topology_store = FakeStore()
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v1/topology").status_code == 503  # Phase 3 default is unchanged.
        stored = client.get("/api/v1/topology?source=stored")
        assert stored.status_code == 200
        assert len(stored.json()["data"]["components"]) == 2
        devices = client.get("/api/v1/devices").json()["data"]
        assert len(devices) == 3
        assert client.get(f"/api/v1/devices/{devices[0]['id']}").status_code == 200
        assert client.get(f"/api/v1/devices/{uuid4()}").status_code == 404
        assert client.get("/api/v1/devices/not-a-uuid").status_code == 422
        assert len(client.get("/api/v1/links").json()["data"]) == 1
        assert client.get(f"/api/v1/links/{uuid4()}").status_code == 404
        assert client.post("/api/v1/devices", json={"name": "server", "device_type": "SERVER", "status": "HEALTHY"}).status_code == 403
        headers = {"X-NetRCA-Local-Control": "1"}
        created = client.post("/api/v1/devices", json={"name": "server", "device_type": "SERVER", "status": "HEALTHY"}, headers=headers)
        assert created.status_code == 201
        assert client.post("/api/v1/devices", json={"name": "server", "device_type": "SERVER", "status": "HEALTHY"}, headers=headers).status_code == 409
        link = client.post("/api/v1/links", json={"source_device_id": devices[0]["id"],
                                                 "destination_device_id": created.json()["data"]["id"], "status": "UP"}, headers=headers)
        assert link.status_code == 201
        assert client.get(f"/api/v1/links/{link.json()['data']['id']}").status_code == 200
        snapshot = client.post("/api/v1/topology/snapshots", json={"reason": "Before changes"}, headers=headers)
        assert snapshot.status_code == 201
        assert snapshot.json()["data"]["reason"] == "Before changes"
        assert len(client.get("/api/v1/topology/snapshots?limit=1").json()["data"]) == 1
        assert client.get("/api/v1/topology/snapshots?limit=0").status_code == 422


def test_stored_topology_api_disabled_nonlocal_and_invalid_graph():
    app = create_app(Settings(_env_file=None))
    fake = FakeStore()
    app.state.topology_store = fake
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post("/api/v1/devices", json={"name": "x", "device_type": "HOST", "status": "HEALTHY"},
                           headers={"X-NetRCA-Local-Control": "1"}).json()["error"]["code"] == "TOPOLOGY_WRITES_DISABLED"
        fake.graph.links.append(Link(id=uuid4(), source_device_id=uuid4(),
                                     destination_device_id=fake.graph.devices[0].id, status="UP"))
        assert client.get("/api/v1/topology?source=stored").status_code == 409
    with TestClient(app, client=("203.0.113.2", 50000)) as client:
        assert client.get("/api/v1/devices").status_code == 403
