"""Read-only structural evidence over Phase 4's validated physical-link graph."""
from uuid import UUID

import networkx as nx

from app.topology.graph import TopologyGraph
from app.topology.models import (GraphDevice, GraphImportance, GraphLink, GraphNeighbor,
                                 GraphNeighborhood, GraphPath, GraphScore, GraphSummary,
                                 IncidentGraphContext, IncidentGraphReference)


def _ids(values) -> list[UUID]:
    return sorted(values, key=str)


class GraphAnalysis:
    def __init__(self, topology: TopologyGraph):
        self.topology = topology
        self.graph = topology._validated_graph()

    def summary(self) -> GraphSummary:
        components = [_ids(group) for group in nx.connected_components(self.graph)]
        components.sort(key=lambda group: str(group[0]))
        return GraphSummary(
            connected=len(components) == 1,
            components=components,
            devices=[GraphDevice.model_validate(device.model_dump())
                     for device in sorted(self.topology.devices, key=lambda item: str(item.id))],
            links=[GraphLink.model_validate(link.model_dump())
                   for link in sorted(self.topology.links, key=lambda item: str(item.id))],
        )

    def path(self, source: UUID, destination: UUID) -> GraphPath:
        # Reuse Phase 4's shortest-path contract, including unknown-ID and no-path behavior.
        device_ids = self.topology.path(source, destination)
        if device_ids is None:
            return GraphPath(source_id=source, destination_id=destination, connected=False,
                             device_ids=[], link_ids=[], hops=None)
        links = [self.graph[a][b]["id"] for a, b in zip(device_ids, device_ids[1:])]
        return GraphPath(source_id=source, destination_id=destination, connected=True,
                         device_ids=device_ids, link_ids=links, hops=len(links))

    def neighbors(self, device_id: UUID) -> GraphNeighborhood:
        ids = self.topology.neighbors(device_id)
        return GraphNeighborhood(device_id=device_id, neighbors=[
            GraphNeighbor(device_id=neighbor, link_id=self.graph[device_id][neighbor]["id"],
                          link_status=self.graph[device_id][neighbor]["status"])
            for neighbor in ids
        ])

    def importance(self) -> GraphImportance:
        articulation = _ids(nx.articulation_points(self.graph))
        bridges = _ids(self.graph[a][b]["id"] for a, b in nx.bridges(self.graph))
        # Betweenness describes shortest-path position, not failure likelihood or cause.
        compute_betweenness = len(self.graph) <= 128
        betweenness = nx.betweenness_centrality(self.graph, normalized=True) if compute_betweenness else {}
        scores = [GraphScore(device_id=device_id, degree=self.graph.degree[device_id],
                             betweenness=round(betweenness[device_id], 6) if compute_betweenness else None)
                  for device_id in _ids(self.graph.nodes)]
        return GraphImportance(articulation_device_ids=articulation, bridge_link_ids=bridges,
                               scores=scores,
                               betweenness_status="COMPUTED" if compute_betweenness else "SKIPPED_TOO_LARGE")

    def incident_context(self, incident: dict) -> IncidentGraphContext:
        """Map only direct stored IDs and one-hop structural context; no causal inference."""
        links_by_id = {data["id"]: (a, b) for a, b, data in self.graph.edges(data=True)}
        direct_devices: set[UUID] = set()
        direct_links: set[UUID] = set()
        missing_devices: set[UUID] = set()
        missing_links: set[UUID] = set()
        unmapped_services: set[UUID] = set()
        refs: list[IncidentGraphReference] = []
        for kind, rows in (("EVENT", incident["events"]), ("ANOMALY", incident["anomalies"])):
            for row in rows:
                device_id, link_id = row.get("device_id"), row.get("link_id")
                device_found = device_id in self.graph if device_id is not None else None
                link_found = link_id in links_by_id if link_id is not None else None
                if device_id is not None:
                    (direct_devices if device_found else missing_devices).add(device_id)
                if link_id is not None:
                    (direct_links if link_found else missing_links).add(link_id)
                if row.get("service_id") is not None:
                    unmapped_services.add(row["service_id"])
                refs.append(IncidentGraphReference(kind=kind, id=row["id"],
                                                   device_id=device_id, link_id=link_id,
                                                   device_found=device_found, link_found=link_found))
        context_devices = set(direct_devices)
        context_links = set(direct_links)
        for link_id in direct_links:
            context_devices.update(links_by_id[link_id])
        for device_id in direct_devices:
            for neighbor in self.graph.neighbors(device_id):
                context_devices.add(neighbor)
                context_links.add(self.graph[device_id][neighbor]["id"])
        return IncidentGraphContext(
            incident_id=incident["id"], evidence=refs,
            referenced_device_ids=_ids(direct_devices), referenced_link_ids=_ids(direct_links),
            context_device_ids=_ids(context_devices), context_link_ids=_ids(context_links),
            missing_device_ids=_ids(missing_devices), missing_link_ids=_ids(missing_links),
            unmapped_service_ids=_ids(unmapped_services),
        )
