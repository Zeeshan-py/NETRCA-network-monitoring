"""Rank plausible component failures; physical adjacency is support, not causation."""
from collections import defaultdict
from uuid import UUID

from app.rca.models import (AnalysisResult, Candidate, EvidenceReference,
                            Observation, RuleContribution)
from app.topology.analysis import GraphAnalysis
from app.topology.graph import TopologyGraph


def _ref(item: Observation, reason: str) -> EvidenceReference:
    return EvidenceReference(source_type=item.kind, source_id=item.id,
                             timestamp=item.observed_at, metric_id=item.metric_id, reason=reason)


def _key(item: Observation) -> tuple[str, UUID] | None:
    if item.kind == "EVENT":
        if item.event_type == "LINK_FAILURE" and item.link_id:
            return "LINK_FAILURE", item.link_id
        if item.event_type == "INTERFACE_FAILURE" and item.device_id:
            return "INTERFACE_FAILURE", item.device_id
        if item.event_type == "DEVICE_UNAVAILABLE" and item.device_id:
            return "DEVICE_UNAVAILABLE", item.device_id
    elif item.metric_value == 0:
        if item.metric_type == "LINK_STATE" and item.link_id:
            return "LINK_FAILURE", item.link_id
        if item.metric_type == "INTERFACE_STATE" and item.device_id:
            return "INTERFACE_FAILURE", item.device_id
    return None


def _source_key(item: Observation) -> tuple[str, UUID]:
    # Multiple anomaly rows for one metric observation are one measurement.
    return ("METRIC", item.metric_id) if item.kind == "ANOMALY" and item.metric_id else (item.kind, item.id)


def _related(candidate_key: tuple[str, UUID], item: Observation, graph: GraphAnalysis | None) -> bool:
    cause_type, target = candidate_key
    if cause_type == "LINK_FAILURE":
        if item.link_id == target:
            return True
        if graph and item.device_id and target in {data["id"] for _, _, data in graph.graph.edges(data=True)}:
            for left, right, data in graph.graph.edges(data=True):
                if data["id"] == target:
                    return item.device_id in {left, right}
        return False
    if item.device_id == target:
        return True
    return bool(graph and target in graph.graph and item.device_id in graph.graph.neighbors(target))


def analyze(incident_id: UUID, observations: list[Observation], topology: TopologyGraph | None,
            *, window_seconds: int = 300, limitations: list[str] | None = None) -> AnalysisResult:
    """Only explicit failure events or state-down anomalies seed candidates.

    Score units are uncalibrated integer rule points, never probabilities.
    """
    limits = set(limitations or [])
    unique: dict[tuple[str, UUID], Observation] = {}
    for item in observations:
        unique.setdefault((item.kind, item.id), item)
    items = sorted(unique.values(), key=lambda row: (row.observed_at.isoformat() if row.observed_at else "", row.kind, str(row.id)))
    graph = None
    if topology is not None:
        try:
            graph = GraphAnalysis(topology)
        except ValueError:
            limits.add("INVALID_STORED_TOPOLOGY")
    else:
        limits.add("TOPOLOGY_UNAVAILABLE")
    grouped: dict[tuple[str, UUID], dict[tuple[str, UUID], Observation]] = defaultdict(dict)
    for item in items:
        if item.observed_at is None:
            limits.add("MISSING_EVIDENCE_TIMESTAMP")
        key = _key(item)
        if key:
            grouped[key].setdefault(_source_key(item), item)
    candidates: list[Candidate] = []
    importance = graph.importance() if graph else None
    for key in sorted(grouped, key=lambda row: (row[0], str(row[1]))):
        cause_type, target = key
        direct = sorted(grouped[key].values(), key=lambda row: (row.observed_at.isoformat() if row.observed_at else "", row.kind, str(row.id)))
        score = 4 + min(2 * (len(direct) - 1), 4)
        supporting = [_ref(item, "DIRECT_FAILURE") for item in direct]
        contradictory: list[EvidenceReference] = []
        contributions = [RuleContribution(rule="DIRECT_FAILURE", points=4, evidence=supporting[:1])]
        if len(direct) > 1:
            contributions.append(RuleContribution(rule="INDEPENDENT_DIRECT_OBSERVATIONS",
                                                  points=min(2 * (len(direct) - 1), 4), evidence=supporting[1:]))
        candidate_limits: set[str] = set()
        if graph:
            known = target in (graph.graph if cause_type != "LINK_FAILURE" else
                               {data["id"] for _, _, data in graph.graph.edges(data=True)})
            if not known:
                candidate_limits.add("TARGET_MISSING_FROM_STORED_TOPOLOGY")
        resolved = [item for item in direct if item.event_status == "RESOLVED"]
        if resolved:
            score -= 3
            refs = [_ref(item, "FAILURE_EVENT_RESOLVED") for item in resolved]
            contradictory.extend(refs)
            contributions.append(RuleContribution(rule="RESOLVED_FAILURE", points=-3, evidence=refs))
        first_time = next((item.observed_at for item in direct if item.observed_at is not None), None)
        if first_time is None:
            candidate_limits.add("DIRECT_FAILURE_TIME_MISSING")
        later: list[EvidenceReference] = []
        earlier: list[EvidenceReference] = []
        direct_sources = {_source_key(item) for item in direct}
        seen_symptoms: set[tuple[str, UUID]] = set()
        for item in items:
            source = _source_key(item)
            if source in direct_sources or source in seen_symptoms or _key(item) is not None:
                continue
            if not _related(key, item, graph) or item.observed_at is None or first_time is None:
                continue
            delta = (item.observed_at - first_time).total_seconds()
            if 0 <= delta <= window_seconds:
                later.append(_ref(item, "FOLLOWING_RELATED_SYMPTOM"))
                seen_symptoms.add(source)
            elif -window_seconds <= delta < 0:
                earlier.append(_ref(item, "SYMPTOM_PRECEDES_FAILURE"))
                seen_symptoms.add(source)
        if later:
            points = min(len(later), 2)
            score += points
            supporting.extend(later)
            contributions.append(RuleContribution(rule="FOLLOWING_RELATED_SYMPTOM", points=points, evidence=later))
        if earlier:
            score -= 2
            contradictory.extend(earlier)
            contributions.append(RuleContribution(rule="SYMPTOM_PRECEDES_FAILURE", points=-2, evidence=earlier))
        if importance and later:
            cut = target in (importance.bridge_link_ids if cause_type == "LINK_FAILURE" else
                             importance.articulation_device_ids)
            if cut:
                score += 1
                ref = EvidenceReference(source_type="TOPOLOGY", source_id=target, reason="PHYSICAL_GRAPH_CUT")
                supporting.append(ref)
                contributions.append(RuleContribution(rule="TOPOLOGY_CUT_WITH_SYMPTOM", points=1, evidence=[ref]))
        score = max(0, score)
        candidates.append(Candidate(cause_type=cause_type,
                                    target_kind="LINK" if cause_type == "LINK_FAILURE" else "DEVICE",
                                    target_id=target, score=score,
                                    explanation="Direct failure evidence supports a plausible component cause; timing and physical topology are corroboration, not proof.",
                                    contributions=contributions, supporting_evidence=supporting,
                                    contradictory_evidence=contradictory,
                                    limitations=sorted(candidate_limits)))
    candidates.sort(key=lambda row: (-row.score, row.cause_type, str(row.target_id)))
    if not items:
        limits.add("NO_VALID_INCIDENT_EVIDENCE")
    if not candidates:
        limits.add("NO_DIRECT_FAILURE_EVIDENCE")
    status = "CANDIDATES" if candidates and candidates[0].score >= 4 else "INCONCLUSIVE"
    if status == "INCONCLUSIVE" and candidates:
        limits.add("DIRECT_EVIDENCE_CONTRADICTED_OR_WEAK")
    return AnalysisResult(incident_id=incident_id, status=status, candidates=candidates,
                          limitations=sorted(limits), evidence_count=len(items))
