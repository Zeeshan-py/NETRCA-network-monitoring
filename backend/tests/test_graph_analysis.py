"""Phase 10 structural analysis and local API contracts."""
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.connection import DatabaseUnavailable
from app.main import create_app
from app.network.models import DeviceView, LinkView, TopologyView
from app.topology.analysis import GraphAnalysis
from app.topology.graph import TopologyGraph, from_mininet
from app.topology.models import Device, Link


IDS = [UUID(int=n) for n in range(1, 9)]


def make_graph(edges=(), count=4):
    devices = [Device(id=IDS[n], name=f"node{n}", device_type="SWITCH", status="HEALTHY")
               for n in range(count)]
    links = [Link(id=IDS[4 + n], source_device_id=IDS[a], destination_device_id=IDS[b], status="UP")
             for n, (a, b) in enumerate(edges)]
    return TopologyGraph(devices, links)


def test_graph_construction_components_and_immutable_metadata():
    topology = make_graph([(0, 1)], count=3)
    before = [item.model_dump() for item in topology.devices + topology.links]
    analysis = GraphAnalysis(topology)
    assert analysis.graph.nodes[IDS[0]]["name"] == "node0"
    assert analysis.graph.edges[IDS[0], IDS[1]]["id"] == IDS[4]
    summary = analysis.summary()
    assert summary.directed is False and summary.semantics == "PHYSICAL_TOPOLOGY"
    assert summary.connected is False
    assert summary.components == [[IDS[0], IDS[1]], [IDS[2]]]
    assert [item.model_dump() for item in topology.devices + topology.links] == before
    assert GraphAnalysis(TopologyGraph([], [])).summary().components == []


def test_path_neighborhood_and_unknown_ids():
    analysis = GraphAnalysis(make_graph([(0, 1), (1, 2)], count=4))
    route = analysis.path(IDS[0], IDS[2])
    assert route.connected and route.device_ids == [IDS[0], IDS[1], IDS[2]]
    assert route.link_ids == [IDS[4], IDS[5]] and route.hops == 2
    assert analysis.path(IDS[2], IDS[0]).device_ids == [IDS[2], IDS[1], IDS[0]]
    assert analysis.path(IDS[0], IDS[0]).hops == 0
    assert analysis.path(IDS[0], IDS[3]).connected is False
    assert analysis.path(IDS[0], IDS[3]).hops is None
    assert [(item.device_id, item.link_id) for item in analysis.neighbors(IDS[1]).neighbors] == [
        (IDS[0], IDS[4]), (IDS[2], IDS[5])]
    with pytest.raises(KeyError):
        analysis.path(uuid4(), IDS[0])
    with pytest.raises(KeyError):
        analysis.path(IDS[0], uuid4())
    with pytest.raises(KeyError):
        analysis.neighbors(uuid4())


def test_structural_importance_on_chain_cycle_singleton_and_empty():
    chain = GraphAnalysis(make_graph([(0, 1), (1, 2)], count=3)).importance()
    assert chain.articulation_device_ids == [IDS[1]]
    assert chain.bridge_link_ids == [IDS[4], IDS[5]]
    assert {row.device_id: row.betweenness for row in chain.scores}[IDS[1]] == 1.0
    cycle = GraphAnalysis(make_graph([(0, 1), (1, 2), (2, 0)], count=3)).importance()
    assert cycle.articulation_device_ids == [] and cycle.bridge_link_ids == []
    one = GraphAnalysis(make_graph(count=1)).importance()
    assert one.scores[0].degree == 0 and one.scores[0].betweenness == 0
    assert GraphAnalysis(TopologyGraph([], [])).importance().scores == []


def test_invalid_topology_rejected_and_live_projection_is_structural():
    topology = make_graph([(0, 1)], count=2)
    topology.links.append(Link(id=IDS[6], source_device_id=IDS[1], destination_device_id=IDS[0], status="UP"))
    with pytest.raises(ValueError):
        GraphAnalysis(topology)
    for bad in [(IDS[0], IDS[0]), (IDS[0], uuid4())]:
        topology = make_graph(count=2)
        topology.links.append(Link(id=IDS[4], source_device_id=bad[0], destination_device_id=bad[1], status="UP"))
        with pytest.raises(ValueError):
            GraphAnalysis(topology)
    view = TopologyView(topology_name="lab", nodes=[
        DeviceView(id="s1", name="s1", device_type="SWITCH"),
        DeviceView(id="h1", name="h1", device_type="HOST")],
        links=[LinkView(id="h1--s1", source="h1", destination="s1", status="UP",
                        interface_source="h1-eth0", interface_destination="s1-eth1")])
    analysis = GraphAnalysis(from_mininet(view))
    assert analysis.summary().connected
    assert all(item.status == "PRESENT" for item in analysis.summary().devices)
    assert analysis.summary().devices[0].id == GraphAnalysis(from_mininet(view)).summary().devices[0].id


def test_incident_context_uses_only_direct_stored_references():
    analysis = GraphAnalysis(make_graph([(0, 1), (1, 2)], count=4))
    unknown_device, unknown_link, service = uuid4(), uuid4(), uuid4()
    event_id, anomaly_id = uuid4(), uuid4()
    result = analysis.incident_context({"id": uuid4(), "events": [
        {"id": event_id, "device_id": IDS[0], "link_id": IDS[5], "service_id": service},
        {"id": uuid4(), "device_id": unknown_device, "link_id": unknown_link}],
        "anomalies": [{"id": anomaly_id, "device_id": None, "link_id": None}]})
    assert result.referenced_device_ids == [IDS[0]]
    assert result.referenced_link_ids == [IDS[5]]
    assert result.context_device_ids == [IDS[0], IDS[1], IDS[2]]
    assert result.context_link_ids == [IDS[4], IDS[5]]
    assert result.missing_device_ids == [unknown_device]
    assert result.missing_link_ids == [unknown_link]
    assert result.unmapped_service_ids == [service]
    assert result.evidence[0].id == event_id and result.evidence[0].device_found
    assert result.evidence[1].link_found is False
    assert result.evidence[2].id == anomaly_id
    assert analysis.incident_context({"id": uuid4(), "events": [], "anomalies": []}).evidence == []


class FakeTopologyStore:
    def __init__(self, graph=None, fail=False):
        self.graph, self.fail = graph or make_graph([(0, 1)], count=3), fail

    def load(self):
        if self.fail:
            raise DatabaseUnavailable("private database detail")
        return self.graph


class FakeIncidentStore:
    def __init__(self, incident=None, fail=False):
        self.incident, self.fail = incident, fail

    def get(self, _id):
        if self.fail:
            raise DatabaseUnavailable("private incident detail")
        return self.incident


def test_graph_api_stored_source_validation_security_and_errors():
    app = create_app(Settings(_env_file=None))
    app.state.topology_store = FakeTopologyStore()
    app.state.incident_store = FakeIncidentStore({"id": IDS[6], "events": [
        {"id": IDS[7], "device_id": IDS[0], "link_id": IDS[4], "service_id": None}], "anomalies": []})
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v1/topology/analysis").status_code == 503  # Default live source.
        summary = client.get("/api/v1/topology/analysis?source=stored")
        assert summary.status_code == 200 and summary.json()["data"]["connected"] is False
        assert client.get("/api/v1/topology/analysis?source=unknown").status_code == 422
        path = client.get(f"/api/v1/topology/path?source=stored&source_id={IDS[0]}&destination_id={IDS[1]}")
        assert path.status_code == 200 and path.json()["data"]["hops"] == 1
        assert client.get(f"/api/v1/topology/path?source=stored&source_id={IDS[0]}&destination_id={uuid4()}").status_code == 404
        assert client.get("/api/v1/topology/path?source_id=bad&destination_id=bad").status_code == 422
        assert client.get(f"/api/v1/topology/devices/{IDS[0]}/neighbors?source=stored").status_code == 200
        assert client.get(f"/api/v1/topology/devices/{uuid4()}/neighbors?source=stored").status_code == 404
        assert client.get("/api/v1/topology/importance?source=stored").json()["data"]["bridge_link_ids"] == [str(IDS[4])]
        incident = client.get(f"/api/v1/incidents/{IDS[6]}/topology-context")
        assert incident.status_code == 200 and incident.json()["data"]["referenced_link_ids"] == [str(IDS[4])]
        app.state.incident_store.incident = None
        assert client.get(f"/api/v1/incidents/{uuid4()}/topology-context").status_code == 404
        app.state.topology_store.fail = True
        failure = client.get("/api/v1/topology/analysis?source=stored")
        assert failure.status_code == 503 and "private" not in failure.text
        app.state.topology_store.fail = False
        app.state.incident_store.fail = True
        failure = client.get(f"/api/v1/incidents/{IDS[6]}/topology-context")
        assert failure.status_code == 503 and "private" not in failure.text
        app.state.topology_store.graph.links.append(Link(id=IDS[5], source_device_id=IDS[0],
                                                          destination_device_id=uuid4(), status="UP"))
        assert client.get("/api/v1/topology/analysis?source=stored").status_code == 409
    with TestClient(app, client=("203.0.113.1", 50000)) as client:
        assert client.get("/api/v1/topology/analysis?source=stored").status_code == 403
        assert client.get(f"/api/v1/incidents/{IDS[6]}/topology-context").status_code == 403


def test_graph_api_live_source_uses_phase3_projection_without_starting_lab():
    view = TopologyView(topology_name="lab", nodes=[
        DeviceView(id="s1", name="s1", device_type="SWITCH"),
        DeviceView(id="h1", name="h1", device_type="HOST")],
        links=[LinkView(id="h1--s1", source="h1", destination="s1", status="DOWN",
                        interface_source="h1-eth0", interface_destination="s1-eth1")])

    class FakeManager:
        def get_topology(self):
            return view

        def close(self, **_kwargs):
            pass

    app = create_app(Settings(_env_file=None))
    app.state.network_manager = FakeManager()
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        summary = client.get("/api/v1/topology/analysis")
        assert summary.status_code == 200
        assert summary.json()["data"]["links"][0]["status"] == "DOWN"
        ids = [row["id"] for row in summary.json()["data"]["devices"]]
        path = client.get(f"/api/v1/topology/path?source_id={ids[0]}&destination_id={ids[1]}")
        assert path.status_code == 200 and path.json()["data"]["hops"] == 1
