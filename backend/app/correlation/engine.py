"""Pure, conservative direct-relationship rules; never infer causation or paths."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID


SEVERITY = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@dataclass(frozen=True)
class Evidence:
    kind: str
    id: UUID
    observed_at: datetime | None
    severity: str | None
    device_id: UUID | None = None
    link_id: UUID | None = None
    service_id: UUID | None = None
    metric_id: UUID | None = None
    event_id: UUID | None = None


def valid_time(item: Evidence, *, now: datetime, max_age: timedelta) -> bool:
    value = item.observed_at
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() is not None and now - max_age <= value <= now)


def severity_of(items: list[Evidence]) -> str:
    """Unknown optional severity is LOW; the database-backed loaders reject invalid rows."""
    return max((item.severity if item.severity in SEVERITY else "LOW" for item in items),
               key=SEVERITY.__getitem__, default="LOW")


def relationship(a: Evidence, b: Evidence, links: dict[UUID, frozenset[UUID]],
                 *, window: timedelta) -> str | None:
    if a.id == b.id and a.kind == b.kind:
        return "SAME_EVIDENCE"
    if not a.observed_at or not b.observed_at or a.observed_at.tzinfo is None or b.observed_at.tzinfo is None:
        return None
    if abs(a.observed_at - b.observed_at) > window:
        return None
    if a.service_id and b.service_id and a.service_id != b.service_id:
        return None
    if a.kind == "ANOMALY" and a.event_id and b.kind == "EVENT" and a.event_id == b.id:
        return "SOURCE_EVENT"
    if b.kind == "ANOMALY" and b.event_id and a.kind == "EVENT" and b.event_id == a.id:
        return "SOURCE_EVENT"
    if a.kind == b.kind == "ANOMALY" and a.metric_id and a.metric_id == b.metric_id:
        return "SOURCE_METRIC"
    if a.link_id and a.link_id == b.link_id:
        return "SAME_LINK"
    if a.service_id and a.service_id == b.service_id:
        return "SAME_SERVICE"
    if a.device_id and a.device_id == b.device_id:
        return "SAME_DEVICE"
    if a.link_id and b.device_id and b.device_id in links.get(a.link_id, frozenset()):
        return "LINK_ENDPOINT"
    if b.link_id and a.device_id and a.device_id in links.get(b.link_id, frozenset()):
        return "LINK_ENDPOINT"
    return None


def group(items: list[Evidence], links: dict[UUID, frozenset[UUID]], *, now: datetime,
          window: timedelta, max_age: timedelta) -> tuple[list[list[tuple[Evidence, str]]], list[UUID]]:
    """Greedy ordered groups. Each member directly relates to another; span stays bounded."""
    seen: set[tuple[str, UUID]] = set()
    accepted: list[Evidence] = []
    skipped: list[UUID] = []
    for item in items:
        key = (item.kind, item.id)
        if key in seen or not valid_time(item, now=now, max_age=max_age):
            skipped.append(item.id)
            continue
        seen.add(key)
        accepted.append(item)
    accepted.sort(key=lambda item: (item.observed_at.astimezone(timezone.utc), item.kind, str(item.id)))
    groups: list[list[tuple[Evidence, str]]] = []
    for item in accepted:
        for members in groups:
            if item.observed_at - members[0][0].observed_at > window:
                continue
            reason = next((reason for prior, _ in members
                           if (reason := relationship(item, prior, links, window=window))), None)
            if reason:
                members.append((item, reason))
                break
        else:
            groups.append([(item, "SEED")])
    return groups, skipped
