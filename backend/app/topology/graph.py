"""Topology validation and relationships. Links are physical, undirected edges."""
from collections.abc import Iterable
from uuid import UUID, uuid5

import networkx as nx

from app.network.models import TopologyView
from app.topology.models import Device, Link, TopologyValidation


# Runtime IDs are deterministic graph IDs, not claims of persisted database rows.
RUNTIME_NAMESPACE = UUID("09dfd2df-838b-4dd7-91fb-39b1970aa86f")


class TopologyGraph:
    def __init__(self, devices: Iterable[Device], links: Iterable[Link]):
        self.devices = list(devices)
        self.links = list(links)

    def validate(self) -> TopologyValidation:
        errors: list[str] = []
        graph = nx.Graph()
        seen_ids: set[UUID] = set()
        names: set[str] = set()
        addresses: set[str] = set()
        for device in self.devices:
            if device.id in seen_ids:
                errors.append("DUPLICATE_DEVICE_ID")
            if not device.name.strip() or device.name in names:
                errors.append("DUPLICATE_OR_EMPTY_DEVICE_NAME")
            if device.ip_address and device.ip_address in addresses:
                errors.append("DUPLICATE_DEVICE_ADDRESS")
            seen_ids.add(device.id)
            names.add(device.name)
            if device.ip_address:
                addresses.add(device.ip_address)
            graph.add_node(device.id)

        link_ids: set[UUID] = set()
        endpoint_pairs: set[frozenset[UUID]] = set()
        for link in self.links:
            if link.id in link_ids:
                errors.append("DUPLICATE_LINK_ID")
            link_ids.add(link.id)
            if link.source_device_id == link.destination_device_id:
                errors.append("SELF_LINK")
                continue
            if link.source_device_id not in seen_ids or link.destination_device_id not in seen_ids:
                errors.append("INVALID_LINK_ENDPOINT")
                continue
            pair = frozenset((link.source_device_id, link.destination_device_id))
            if pair in endpoint_pairs:
                errors.append("DUPLICATE_LINK")
            endpoint_pairs.add(pair)
            graph.add_edge(link.source_device_id, link.destination_device_id)

        components = [sorted(group, key=str) for group in nx.connected_components(graph)]
        components.sort(key=lambda group: str(group[0]))
        return TopologyValidation(valid=not errors, errors=sorted(set(errors)), components=components)

    def _validated_graph(self) -> nx.Graph:
        validation = self.validate()
        if not validation.valid:
            raise ValueError("Cannot traverse an invalid topology")
        graph = nx.Graph()
        for device in sorted(self.devices, key=lambda item: str(item.id)):
            graph.add_node(device.id, name=device.name, device_type=device.device_type,
                           status=device.status, is_active=device.is_active)
        for link in sorted(self.links, key=lambda item: str(item.id)):
            graph.add_edge(link.source_device_id, link.destination_device_id, id=link.id,
                           status=link.status, interface_source=link.interface_source,
                           interface_destination=link.interface_destination,
                           bandwidth_mbps=link.bandwidth_mbps, latency_ms=link.latency_ms,
                           packet_loss_percent=link.packet_loss_percent)
        return graph

    def neighbors(self, device_id: UUID) -> list[UUID]:
        graph = self._validated_graph()
        if device_id not in graph:
            raise KeyError(device_id)
        return sorted(graph.neighbors(device_id), key=str)

    def path(self, source: UUID, destination: UUID) -> list[UUID] | None:
        graph = self._validated_graph()
        if source not in graph or destination not in graph:
            raise KeyError("Unknown device")
        try:
            return nx.shortest_path(graph, source, destination)
        except nx.NetworkXNoPath:
            return None


def from_mininet(view: TopologyView) -> TopologyGraph:
    """Project a live Phase 3 view without storing or inventing health status."""
    names = {node.id for node in view.nodes}
    node_ids = {name: uuid5(RUNTIME_NAMESPACE, f"{view.topology_name}:device:{name}")
                for name in names | {name for link in view.links for name in (link.source, link.destination)}}
    devices = [
        Device(id=node_ids[node.id], name=node.name, device_type=node.device_type,
               status="PRESENT", ip_address=node.ip_address)
        for node in view.nodes
    ]
    links = [
        Link(id=uuid5(RUNTIME_NAMESPACE, f"{view.topology_name}:link:{link.id}"),
             source_device_id=node_ids[link.source], destination_device_id=node_ids[link.destination],
             status=link.status, interface_source=link.interface_source,
             interface_destination=link.interface_destination)
        for link in view.links
    ]
    return TopologyGraph(devices, links)
