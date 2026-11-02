"""Build the fixed Mininet lab from the shared validated scenario contract."""
from dataclasses import dataclass

from app.network.scenario import DEFAULT_SCENARIO, NetworkScenario


@dataclass(frozen=True)
class NodeSpec:
    name: str
    device_type: str
    ip: str | None = None


@dataclass(frozen=True)
class LinkSpec:
    source: str
    destination: str


TOPOLOGY_NAME = DEFAULT_SCENARIO.name
NODES = tuple(NodeSpec(node.key, node.device_type, node.ip_address) for node in DEFAULT_SCENARIO.nodes)
LINKS = tuple(LinkSpec(link.source, link.destination) for link in DEFAULT_SCENARIO.links)
HOST_NAMES = DEFAULT_SCENARIO.host_names


def validate_topology() -> None:
    # Loading the canonical scenario performs the full validation. Keep this
    # compatibility function for existing callers and explicit smoke checks.
    if len(DEFAULT_SCENARIO.components()) != 1:
        raise ValueError("The default connectivity lab must be connected")


def build_mininet_topology(scenario: NetworkScenario = DEFAULT_SCENARIO):
    """Import Mininet only when a supported Linux environment starts a network."""
    from mininet.topo import Topo

    if scenario is DEFAULT_SCENARIO:
        validate_topology()

    class NetRCATopo(Topo):
        def build(self):
            for node in scenario.nodes:
                if node.device_type == "SWITCH":
                    self.addSwitch(node.key)
                else:
                    self.addHost(node.key, ip=node.ip_address)
            for link in scenario.links:
                self.addLink(link.source, link.destination)

    return NetRCATopo()
