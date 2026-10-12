"""Fixed, loop-free Mininet lab topology. No router is implied."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NodeSpec:
    name: str
    device_type: str
    ip: str | None = None


@dataclass(frozen=True)
class LinkSpec:
    source: str
    destination: str


TOPOLOGY_NAME = "netrca_lab_v1"
NODES = (
    NodeSpec("s1", "SWITCH"),
    NodeSpec("s2", "SWITCH"),
    NodeSpec("h1", "HOST", "10.77.0.11/24"),
    NodeSpec("h2", "HOST", "10.77.0.12/24"),
    NodeSpec("server1", "SERVER", "10.77.0.20/24"),
)
LINKS = (
    LinkSpec("h1", "s1"),
    LinkSpec("s1", "s2"),
    LinkSpec("s2", "h2"),
    LinkSpec("s2", "server1"),
)
HOST_NAMES = ("h1", "h2", "server1")


def validate_topology() -> None:
    names = {node.name for node in NODES}
    if len(names) != len(NODES) or len(set(HOST_NAMES)) != len(HOST_NAMES):
        raise ValueError("Topology node names must be unique")
    if any(link.source not in names or link.destination not in names or link.source == link.destination for link in LINKS):
        raise ValueError("Topology links must join distinct known nodes")
    if any(name not in names or next(n for n in NODES if n.name == name).device_type not in {"HOST", "SERVER"} for name in HOST_NAMES):
        raise ValueError("Connectivity hosts must exist and be hosts")


def build_mininet_topology():
    """Import Mininet only when a supported Linux environment starts a network."""
    from mininet.topo import Topo

    validate_topology()

    class NetRCATopo(Topo):
        def build(self):
            for node in NODES:
                if node.device_type == "SWITCH":
                    self.addSwitch(node.name)
                else:
                    self.addHost(node.name, ip=node.ip)
            for link in LINKS:
                self.addLink(link.source, link.destination)

    return NetRCATopo()
