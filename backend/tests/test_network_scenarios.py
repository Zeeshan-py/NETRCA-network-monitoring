from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.network.models import DeviceView, LinkView, TopologyView
from app.core.config import Settings
from app.main import create_app
from app.network.scenario import (
    DEFAULT_SCENARIO,
    NetworkScenario,
    load_scenario,
    stable_link_id,
)
from app.topology.graph import from_mininet


def payload() -> dict:
    return deepcopy(DEFAULT_SCENARIO.model_dump(mode="json"))


def test_canonical_scenario_has_expected_connected_mininet_contract():
    scenario = load_scenario("netrca_lab_v1")
    assert scenario is DEFAULT_SCENARIO
    assert [node.key for node in scenario.nodes] == ["s1", "s2", "h1", "h2", "server1"]
    assert scenario.host_names == ("h1", "h2", "server1")
    assert [link.key for link in scenario.links] == ["h1--s1", "s1--s2", "s2--h2", "s2--server1"]
    assert scenario.components() == [["h1", "h2", "s1", "s2", "server1"]]


@pytest.mark.parametrize("mutation", [
    "duplicate_node", "duplicate_address", "unknown_endpoint", "self_link",
    "duplicate_link", "wrong_interface_owner",
])
def test_scenario_rejects_invalid_nodes_and_links(mutation):
    value = payload()
    if mutation == "duplicate_node":
        value["nodes"].append(deepcopy(value["nodes"][0]))
    elif mutation == "duplicate_address":
        value["nodes"][3]["ip_address"] = "10.77.0.11/25"
    elif mutation == "unknown_endpoint":
        value["links"][0]["destination"] = "missing"
    elif mutation == "self_link":
        value["links"][0]["destination"] = value["links"][0]["source"]
    elif mutation == "duplicate_link":
        value["links"].append({
            "id": str(stable_link_id(value["name"], "s1--h1")),
            "key": "s1--h1",
            "source": "s1",
            "destination": "h1",
            "interface_source": "s1-eth9",
            "interface_destination": "h1-eth9",
        })
    else:
        value["links"][0]["interface_source"] = "s1-eth9"
    with pytest.raises(ValidationError):
        NetworkScenario.model_validate(value)


def test_scenario_rejects_path_traversal_and_unknown_names():
    with pytest.raises(ValueError, match="Invalid scenario name"):
        load_scenario("../netrca_lab_v1")
    with pytest.raises(ValueError, match="Unknown network scenario"):
        load_scenario("unknown_lab")


def test_live_graph_projection_uses_the_scenario_stable_ids():
    view = TopologyView(
        topology_name=DEFAULT_SCENARIO.name,
        nodes=[
            DeviceView(
                id=node.key,
                name=node.name,
                device_type=node.device_type,
                ip_address=node.ip_address,
            )
            for node in DEFAULT_SCENARIO.nodes
        ],
        links=[
            LinkView(
                id=link.key,
                source=link.source,
                destination=link.destination,
                status="UP",
                interface_source=link.interface_source,
                interface_destination=link.interface_destination,
            )
            for link in DEFAULT_SCENARIO.links
        ],
    )
    graph = from_mininet(view)
    assert [device.id for device in graph.devices] == [node.id for node in DEFAULT_SCENARIO.nodes]
    assert [link.id for link in graph.links] == [link.id for link in DEFAULT_SCENARIO.links]
    assert graph.validate().valid


def test_canonical_scenario_api_is_read_only_local_and_does_not_start_mininet():
    app = create_app(Settings(_env_file=None, simulation_enabled=False))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get("/api/v1/network/scenario")
        assert response.status_code == 200
        assert response.json()["data"]["name"] == DEFAULT_SCENARIO.name
        assert response.json()["data"]["nodes"][0]["id"] == str(DEFAULT_SCENARIO.nodes[0].id)
        assert client.get("/api/v1/network/status").json()["data"]["state"] == "DISABLED"
    with TestClient(app, client=("203.0.113.10", 50000)) as client:
        assert client.get("/api/v1/network/scenario").status_code == 403
