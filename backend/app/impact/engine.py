"""Conservative one-hop failure chains over validated stored physical topology.

Physical adjacency is exposure, never proof of outage or propagation direction.
"""
from uuid import UUID

from app.impact.models import ChainEdge, ImpactEntity, ImpactResult
from app.rca.models import Observation, RcaRun
from app.topology.graph import TopologyGraph


def _direct_observation(candidate, observations: list[Observation]):
    by_id = {(item.kind, item.id): item for item in observations}
    refs = []
    for ref in candidate.supporting_evidence:
        if ref.reason != "DIRECT_FAILURE" or ref.source_type not in {"EVENT", "ANOMALY"}:
            continue
        item = by_id.get((ref.source_type, ref.source_id))
        if item is None or item.observed_at is None or item.observed_at != ref.timestamp:
            continue
        if item.kind == "EVENT" and item.event_status == "RESOLVED":
            continue
        if candidate.target_kind == "LINK":
            valid = item.link_id == candidate.target_id and (
                (item.kind == "EVENT" and item.event_type == "LINK_FAILURE") or
                (item.kind == "ANOMALY" and item.metric_type == "LINK_STATE" and item.metric_value == 0))
        else:
            valid = item.device_id == candidate.target_id and (
                (item.kind == "EVENT" and item.event_type in {"INTERFACE_FAILURE", "DEVICE_UNAVAILABLE"}) or
                (item.kind == "ANOMALY" and item.metric_type == "INTERFACE_STATE" and item.metric_value == 0))
        if valid:
            refs.append(ref)
    return sorted({(ref.source_type, ref.source_id): ref for ref in refs}.values(),
                  key=lambda ref: (ref.source_type, str(ref.source_id)))


def analyze(rca: RcaRun, observations: list[Observation], topology: TopologyGraph,
            service_bindings: list[dict]) -> ImpactResult:
    """Map one uniquely leading, directly supported RCA candidate; never invent impact."""
    limits = {"NO_DIRECT_APPLICATION_OR_USER_EVIDENCE", "NO_DIRECTED_DEPENDENCY_GRAPH",
              "STORED_TOPOLOGY_IS_POINT_IN_TIME", "SERVICE_STATUS_NOT_INCIDENT_SCOPED"}
    empty = dict(incident_id=rca.incident_id, rca_run_id=rca.id, status="INCONCLUSIVE")
    if rca.result.incident_id != rca.incident_id or rca.status != "CANDIDATES" or not rca.result.candidates:
        return ImpactResult(**empty, limitations=sorted(limits | {"RCA_INCONCLUSIVE_OR_INVALID"}))
    candidates = rca.result.candidates
    if len(candidates) > 1 and candidates[0].score == candidates[1].score:
        return ImpactResult(**empty, limitations=sorted(limits | {"AMBIGUOUS_TOP_RCA_CANDIDATE"}))
    candidate = candidates[0]
    refs = _direct_observation(candidate, observations)
    if not refs:
        return ImpactResult(**empty, limitations=sorted(limits | {"DIRECT_EVIDENCE_MISSING_OR_STALE"}))
    if not topology.validate().valid:
        return ImpactResult(**empty, limitations=sorted(limits | {"INVALID_STORED_TOPOLOGY"}))
    devices = {item.id: item for item in topology.devices}
    links = {item.id: item for item in topology.links}
    if candidate.target_id not in (links if candidate.target_kind == "LINK" else devices):
        return ImpactResult(**empty, limitations=sorted(limits | {"RCA_TARGET_NOT_IN_STORED_TOPOLOGY"}))

    entities: dict[tuple[str, UUID], ImpactEntity] = {}
    edges: dict[tuple[str, UUID, str, UUID], ChainEdge] = {}

    def add_entity(kind, entity_id, classification, explanation, evidence=None):
        key = (kind, entity_id)
        if key not in entities or classification == "OBSERVED":
            entities[key] = ImpactEntity(kind=kind, id=entity_id, classification=classification,
                                         evidence=evidence or [], explanation=explanation)

    def add_edge(source_kind, source_id, target_kind, target_id, relationship, explanation, step):
        key = (source_kind, source_id, target_kind, target_id)
        edges[key] = ChainEdge(step=step, source_kind=source_kind, source_id=source_id,
                               target_kind=target_kind, target_id=target_id,
                               relationship=relationship, evidence=refs, explanation=explanation)

    add_entity(candidate.target_kind, candidate.target_id, "OBSERVED",
               "Validated incident evidence directly reports this component failure; RCA remains a candidate.", refs)
    if candidate.target_kind == "LINK":
        link = links[candidate.target_id]
        for endpoint in sorted((link.source_device_id, link.destination_device_id), key=str):
            add_entity("DEVICE", endpoint, "POTENTIAL",
                       "Endpoint of the evidenced link; device health and reachability are unverified.")
            add_edge("LINK", link.id, "DEVICE", endpoint, "LINK_ENDPOINT",
                     "Physical endpoint exposure only; no direction or outage is established.", 1)
        exposed_devices = {link.source_device_id, link.destination_device_id}
    else:
        exposed_devices = {candidate.target_id}
        for link in sorted(topology.links, key=lambda item: str(item.id)):
            if candidate.target_id not in {link.source_device_id, link.destination_device_id}:
                continue
            other = (link.destination_device_id if link.source_device_id == candidate.target_id
                     else link.source_device_id)
            add_entity("LINK", link.id, "POTENTIAL",
                       "Incident to the evidenced device; operational link impact is unverified.")
            add_edge("DEVICE", candidate.target_id, "LINK", link.id, "DEVICE_ADJACENCY",
                     "Physical adjacency to the failed device; propagation is unverified.", 1)
            add_entity("DEVICE", other, "POTENTIAL",
                       "One-hop neighbor on an exposed path; its failure is unobserved.")
            add_edge("LINK", link.id, "DEVICE", other, "LINK_ENDPOINT",
                     "The link reaches this endpoint; reachability is unverified.", 2)
            exposed_devices.add(other)

    # Preserve other direct failure observations without inventing a causal
    # connection to the leading candidate or expanding their topology paths.
    for other_candidate in candidates[1:]:
        known = other_candidate.target_id in (links if other_candidate.target_kind == "LINK" else devices)
        other_refs = _direct_observation(other_candidate, observations)
        if not known or not other_refs:
            continue
        add_entity(other_candidate.target_kind, other_candidate.target_id, "OBSERVED",
                   "Independent direct incident evidence; relationship to the leading candidate is unknown.",
                   other_refs)
        limits.add("ADDITIONAL_DIRECT_FAILURE_NOT_CAUSALLY_CHAINED")

    for binding in sorted(service_bindings, key=lambda row: (str(row["device_id"]), str(row["service_id"]))):
        if binding["device_id"] not in exposed_devices or binding["status"] == "DOWN":
            # A DOWN binding has no verified active hosting relationship.
            continue
        service_id = binding["service_id"]
        add_entity("SERVICE", service_id, "POTENTIAL",
                   "Service is mapped to an exposed device; service failure is not directly observed.")
        add_edge("DEVICE", binding["device_id"], "SERVICE", service_id, "HOSTS_SERVICE",
                 "Verified device-service mapping; service availability is unverified.",
                 1 if binding["device_id"] == candidate.target_id else
                 (2 if candidate.target_kind == "LINK" else 3))

    ordered_entities = [entities[key] for key in sorted(entities, key=lambda key: (key[0], str(key[1])))]
    ordered_edges = sorted(edges.values(), key=lambda edge: (edge.step, edge.source_kind,
                           str(edge.source_id), edge.target_kind, str(edge.target_id)))
    topology_input = {
        "devices": [{"id": str(item.id), "status": item.status, "is_active": item.is_active}
                    for item in sorted(topology.devices, key=lambda item: str(item.id))],
        "links": [{"id": str(item.id), "source_device_id": str(item.source_device_id),
                   "destination_device_id": str(item.destination_device_id), "status": item.status}
                  for item in sorted(topology.links, key=lambda item: str(item.id))],
        "service_bindings": [{"device_id": str(row["device_id"]), "service_id": str(row["service_id"]),
                              "status": row["status"]} for row in sorted(service_bindings,
                              key=lambda row: (str(row["device_id"]), str(row["service_id"])))],
    }
    return ImpactResult(incident_id=rca.incident_id, rca_run_id=rca.id, status="ASSESSED",
                        candidate_target_kind=candidate.target_kind, candidate_target_id=candidate.target_id,
                        entities=ordered_entities, chain=ordered_edges,
                        affected_devices=sum(item.kind == "DEVICE" for item in ordered_entities),
                        affected_links=sum(item.kind == "LINK" for item in ordered_entities),
                        affected_services=sum(item.kind == "SERVICE" for item in ordered_entities),
                        topology_input=topology_input, limitations=sorted(limits))
