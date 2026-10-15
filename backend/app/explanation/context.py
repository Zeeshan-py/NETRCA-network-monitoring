"""Build a closed catalog of grounded sentences; no untrusted prose reaches Gemini."""
import json

from app.explanation.models import Claim, ExplanationInput, SourceReference
from app.explanation.store import ExplanationNotReady, Snapshot
from app.rca.models import EvidenceReference


MAX_INPUT_BYTES = 12000


def build_input(snapshot: Snapshot) -> ExplanationInput:
    rca, impact = snapshot.rca, snapshot.impact
    if (rca.incident_id != snapshot.incident_id or rca.result.incident_id != snapshot.incident_id
            or rca.status != rca.result.status or
            impact is not None and (impact.rca_run_id != rca.id or
                                    impact.result.rca_run_id != rca.id or
                                    impact.result.incident_id != snapshot.incident_id or
                                    impact.status != impact.result.status)):
        raise ExplanationNotReady("MISMATCHED_ANALYSIS_RUN")
    observations = {(item.kind, item.id): item for item in snapshot.observations}
    topology_ids = {item.id for item in snapshot.topology.devices} | {
        item.id for item in snapshot.topology.links}
    rca_ref = SourceReference(source_type="RCA_RUN", source_id=rca.id, timestamp=rca.created_at)
    impact_ref = (SourceReference(source_type="IMPACT_RUN", source_id=impact.id,
                                  timestamp=impact.created_at) if impact else None)
    claims: list[Claim] = []

    def add(section, sentence, refs):
        unique = list(dict.fromkeys((ref.source_type, ref.source_id, ref.timestamp) for ref in refs))
        claims.append(Claim(claim_id=f"C{len(claims) + 1:03d}", section=section, text=sentence,
                            evidence_references=[SourceReference(source_type=k, source_id=i,
                                                                 timestamp=t) for k, i, t in unique]))

    def checked_refs(refs: list[EvidenceReference]):
        checked = []
        for ref in refs:
            if ref.source_type == "TOPOLOGY":
                if ref.source_id not in topology_ids:
                    raise ExplanationNotReady("UNKNOWN_TOPOLOGY_REFERENCE")
            else:
                observation = observations.get((ref.source_type, ref.source_id))
                if observation is None or observation.observed_at != ref.timestamp:
                    raise ExplanationNotReady("UNKNOWN_EVIDENCE_REFERENCE")
            checked.append(SourceReference(source_type=ref.source_type, source_id=ref.source_id,
                                           timestamp=ref.timestamp))
        return checked

    if rca.status == "INCONCLUSIVE":
        add("summary", "The deterministic RCA is inconclusive; no root cause is confirmed.", [rca_ref])
    else:
        add("summary", f"The deterministic RCA identified {len(rca.result.candidates)} candidate "
            "cause(s); none is a confirmed root cause.", [rca_ref])
    for item in sorted(snapshot.observations, key=lambda value: (value.kind, str(value.id))):
        if item.observed_at is None:
            continue
        ref = SourceReference(source_type=item.kind, source_id=item.id, timestamp=item.observed_at)
        target = (f"device {item.device_id}" if item.device_id else
                  f"link {item.link_id}" if item.link_id else "an unspecified component")
        add("observed_facts", f"{item.kind.title()} {item.id} was recorded for {target} "
            f"at {item.observed_at.isoformat()}.", [ref])
    for candidate in rca.result.candidates:
        if candidate.target_id not in topology_ids:
            raise ExplanationNotReady("UNKNOWN_CANDIDATE_TARGET")
        refs = checked_refs(candidate.supporting_evidence)
        add("candidate_explanations", f"{candidate.cause_type} on {candidate.target_kind.lower()} "
            f"{candidate.target_id} is an RCA candidate, not a confirmed cause.", refs + [rca_ref])
    if impact is None:
        add("missing_evidence", "No impact analysis exists for this RCA run.", [rca_ref])
    elif impact.status == "INCONCLUSIVE":
        add("uncertainties", "The deterministic impact analysis is inconclusive.", [impact_ref])
    else:
        service_ids = {row["service_id"] for row in impact.result.topology_input.get("service_bindings", [])}
        links = {row.id: row for row in snapshot.topology.links}
        service_bindings = {(row["device_id"], row["service_id"]) for row in
                            impact.result.topology_input.get("service_bindings", [])}
        def known_entity(kind, entity_id):
            return str(entity_id) in service_ids if kind == "SERVICE" else entity_id in topology_ids
        for edge in impact.result.chain:
            if not known_entity(edge.source_kind, edge.source_id) or not known_entity(edge.target_kind, edge.target_id):
                raise ExplanationNotReady("UNKNOWN_CHAIN_ENTITY")
            if edge.relationship == "DEVICE_ADJACENCY":
                link = links.get(edge.target_id)
                connected = (edge.source_kind == "DEVICE" and edge.target_kind == "LINK"
                             and link is not None and edge.source_id in
                             {link.source_device_id, link.destination_device_id})
            elif edge.relationship == "LINK_ENDPOINT":
                link = links.get(edge.source_id)
                connected = (edge.source_kind == "LINK" and edge.target_kind == "DEVICE"
                             and link is not None and edge.target_id in
                             {link.source_device_id, link.destination_device_id})
            else:
                connected = (edge.source_kind == "DEVICE" and edge.target_kind == "SERVICE"
                             and (str(edge.source_id), str(edge.target_id)) in service_bindings)
            if not connected:
                raise ExplanationNotReady("UNSUPPORTED_CHAIN_RELATIONSHIP")
            refs = checked_refs(edge.evidence)
            add("failure_chain_explanation", f"Potential physical exposure: {edge.source_kind.lower()} "
                f"{edge.source_id} to {edge.target_kind.lower()} {edge.target_id} through "
                f"{edge.relationship}; propagation is unverified.", refs + [impact_ref])
        for entity in impact.result.entities:
            if not known_entity(entity.kind, entity.id):
                raise ExplanationNotReady("UNKNOWN_IMPACT_ENTITY")
            refs = checked_refs(entity.evidence)
            qualifier = ("directly evidenced in incident data" if entity.classification == "OBSERVED"
                         else "potentially exposed; its outage is unverified")
            add("impact_explanation", f"{entity.kind.title()} {entity.id} is {qualifier}.",
                refs + [impact_ref])
        add("uncertainties", "User and application impact is unknown and unverified.", [impact_ref])
    add("limitations", "Candidate scores are uncalibrated rule points, not probabilities.", [rca_ref])
    add("limitations", "This explanation does not establish causality or confirmed business impact.",
        [impact_ref or rca_ref])
    result = ExplanationInput(incident_id=snapshot.incident_id, rca_run_id=rca.id,
                              impact_run_id=impact.id if impact else None, claims=claims)
    if len(json.dumps(result.model_dump(mode="json")).encode("utf-8")) > MAX_INPUT_BYTES:
        raise ExplanationNotReady("EXPLANATION_INPUT_TOO_LARGE")
    return result
