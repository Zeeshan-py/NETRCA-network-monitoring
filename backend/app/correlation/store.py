"""Transactional grouping of validated stored evidence only."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from psycopg.rows import dict_row
from pydantic import ValidationError

from app.anomaly.store import StoredMetricInvalid, _metric
from app.core.config import Settings
from app.correlation.engine import Evidence, group, relationship, severity_of, valid_time, SEVERITY
from app.correlation.models import CorrelationRequest
from app.db.connection import transaction
from app.pipeline.models import EventIn


class EvidenceNotFound(LookupError):
    pass


class AmbiguousMembership(ValueError):
    pass


def _event(row: dict) -> Evidence | None:
    metadata = row["metadata"]
    if not isinstance(metadata, dict) or row["severity"] not in SEVERITY:
        return None
    try:
        parsed = EventIn(device_id=row["device_id"], link_id=row["link_id"],
                         event_type=row["event_type"], severity=row["severity"],
                         source=metadata.get("source"), dedup_key=metadata.get("dedup_key"),
                         timestamp=row["timestamp"], message=row["message"])
    except (ValidationError, TypeError, ValueError):
        return None
    return Evidence("EVENT", row["id"], parsed.timestamp, row["severity"],
                    device_id=row["device_id"], link_id=row["link_id"],
                    service_id=row["service_id"])


def _anomaly(row: dict) -> Evidence | None:
    if (not row["is_anomaly"] or row["severity"] not in SEVERITY
            or not row["model_name"].startswith("NETRCA_") or row["metric_id"] is None
            or row["metric_timestamp"] is None):
        return None
    try:
        metric = _metric({"device_id": row["metric_device_id"],
                          "link_id": row["metric_link_id"],
                          "metric_type": row["metric_type"], "value": row["value"],
                          "unit": row["unit"], "timestamp": row["metric_timestamp"],
                          "metadata": row["metric_metadata"]})
        metadata = row["metadata"]
        if not isinstance(metadata, dict) or datetime.fromisoformat(metadata["observed_at"]) != metric.timestamp:
            return None
        if row["device_id"] is not None and row["device_id"] != metric.device_id:
            return None
    except (StoredMetricInvalid, TypeError, ValueError, KeyError):
        return None
    return Evidence("ANOMALY", row["id"], metric.timestamp, row["severity"],
                    device_id=metric.device_id, link_id=metric.link_id,
                    metric_id=row["metric_id"], event_id=row["event_id"])


def _events(cursor, ids: list[UUID]) -> dict[UUID, Evidence]:
    if not ids:
        return {}
    cursor.execute("SELECT id,device_id,link_id,service_id,event_type,severity,status,timestamp,message,metadata "
                   "FROM public.events WHERE id=ANY(%s)", (ids,))
    return {item.id: item for row in cursor.fetchall() if (item := _event(row)) is not None}


def _anomalies(cursor, ids: list[UUID]) -> dict[UUID, Evidence]:
    if not ids:
        return {}
    cursor.execute("SELECT a.id,a.device_id,a.metric_id,a.event_id,a.model_name,a.is_anomaly,"
                   "a.severity,a.metadata,m.device_id AS metric_device_id,m.link_id AS metric_link_id,"
                   "m.metric_type,m.value,m.unit,m.timestamp AS metric_timestamp,m.metadata AS metric_metadata "
                   "FROM public.anomalies a LEFT JOIN public.metrics m ON m.id=a.metric_id WHERE a.id=ANY(%s)",
                   (ids,))
    return {item.id: item for row in cursor.fetchall() if (item := _anomaly(row)) is not None}


def _links(cursor, items: list[Evidence]) -> dict[UUID, frozenset[UUID]]:
    ids = list({item.link_id for item in items if item.link_id})
    if not ids:
        return {}
    cursor.execute("SELECT id,source_device_id,destination_device_id FROM public.links WHERE id=ANY(%s)", (ids,))
    return {row["id"]: frozenset((row["source_device_id"], row["destination_device_id"]))
            for row in cursor.fetchall()}


class IncidentStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def correlate(self, request: CorrelationRequest) -> dict:
        event_ids = list(dict.fromkeys(request.event_ids))
        anomaly_ids = list(dict.fromkeys(request.anomaly_ids))
        if not event_ids and not anomaly_ids:
            return {"incidents": [], "skipped_ids": [], "created": 0, "attached": 0}
        now = datetime.now(timezone.utc)
        window = timedelta(seconds=self.settings.correlation_window_seconds)
        max_age = timedelta(minutes=self.settings.correlation_max_age_minutes)
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                # One transaction-scoped lock serializes all Phase 9 writers across API workers.
                cursor.execute("SELECT pg_advisory_xact_lock(47301, 9)")
                events = _events(cursor, event_ids)
                anomalies = _anomalies(cursor, anomaly_ids)
                requested = [*events.values(), *anomalies.values()]
                missing = (set(event_ids) - events.keys()) | (set(anomaly_ids) - anomalies.keys())
                if missing:
                    raise EvidenceNotFound("Stored Phase 6/8 evidence was not found or failed validation")
                cursor.execute("SELECT ie.event_id AS evidence_id,ie.incident_id,i.status FROM public.incident_events ie "
                               "JOIN public.incidents i ON i.id=ie.incident_id WHERE ie.event_id=ANY(%s)", (event_ids,))
                memberships = {}
                for row in cursor.fetchall():
                    key = ("EVENT", row["evidence_id"])
                    if key in memberships and memberships[key][0] != row["incident_id"]:
                        raise AmbiguousMembership("Event belongs to multiple incidents")
                    memberships[key] = (row["incident_id"], row["status"])
                cursor.execute("SELECT ia.anomaly_id AS evidence_id,ia.incident_id,i.status "
                               "FROM public.incident_anomalies ia JOIN public.incidents i ON i.id=ia.incident_id "
                               "WHERE ia.anomaly_id=ANY(%s)", (anomaly_ids,))
                for row in cursor.fetchall():
                    memberships[("ANOMALY", row["evidence_id"])] = (row["incident_id"], row["status"])
                closed = {(item.kind, item.id) for item in requested if (member := memberships.get((item.kind, item.id)))
                          and member[1] not in {"DETECTED", "INVESTIGATING"}}
                requested = [item for item in requested if (item.kind, item.id) not in closed]
                groups, stale = group(requested, _links(cursor, requested), now=now, window=window, max_age=max_age)
                skipped = [*(item_id for _, item_id in closed), *stale]
                if not groups:
                    return {"incidents": [], "skipped_ids": sorted(skipped, key=str), "created": 0, "attached": 0}
                earliest = min(members[0][0].observed_at for members in groups) - window
                latest = max(members[-1][0].observed_at for members in groups) + window
                cursor.execute("SELECT ie.incident_id,ie.event_id AS evidence_id FROM public.incident_events ie "
                               "JOIN public.incidents i ON i.id=ie.incident_id JOIN public.events e ON e.id=ie.event_id "
                               "WHERE i.status IN ('DETECTED','INVESTIGATING') AND e.timestamp BETWEEN %s AND %s "
                               "LIMIT 1001", (earliest, latest))
                anchor_rows = [(row["incident_id"], "EVENT", row["evidence_id"]) for row in cursor.fetchall()]
                cursor.execute("SELECT ia.incident_id,ia.anomaly_id AS evidence_id FROM public.incident_anomalies ia "
                               "JOIN public.incidents i ON i.id=ia.incident_id "
                               "JOIN public.anomalies a ON a.id=ia.anomaly_id "
                               "JOIN public.metrics m ON m.id=a.metric_id "
                               "WHERE i.status IN ('DETECTED','INVESTIGATING') AND m.timestamp BETWEEN %s AND %s "
                               "LIMIT 1001", (earliest, latest))
                anchor_rows += [(row["incident_id"], "ANOMALY", row["evidence_id"]) for row in cursor.fetchall()]
                if len(anchor_rows) > 1000:
                    raise ValueError("Too many open incident anchors in the time window")
                all_events = _events(cursor, [item_id for _, kind, item_id in anchor_rows if kind == "EVENT"])
                all_anomalies = _anomalies(cursor, [item_id for _, kind, item_id in anchor_rows if kind == "ANOMALY"])
                anchors: dict[UUID, list[Evidence]] = {}
                for incident_id, kind, item_id in anchor_rows:
                    item = (all_events if kind == "EVENT" else all_anomalies).get(item_id)
                    if item and valid_time(item, now=now, max_age=max_age):
                        anchors.setdefault(incident_id, []).append(item)
                links = _links(cursor, [*requested, *(item for values in anchors.values() for item in values)])
                results = []
                created = attached = 0
                for members in groups:
                    items = [item for item, _ in members]
                    assigned = {memberships[(item.kind, item.id)][0] for item in items
                                if (item.kind, item.id) in memberships}
                    candidates = set(assigned)
                    for incident_id, evidence in anchors.items():
                        if any(relationship(item, prior, links, window=window)
                               for item in items for prior in evidence):
                            candidates.add(incident_id)
                    if len(candidates) > 1:
                        skipped.extend(item.id for item in items)
                        continue
                    if candidates:
                        incident_id = next(iter(candidates))
                    else:
                        cursor.execute("INSERT INTO public.incidents (title,severity,status,start_time) "
                                       "VALUES ('Correlated network evidence',%s,'DETECTED',%s) RETURNING id",
                                       (severity_of(items), members[0][0].observed_at))
                        incident_id = cursor.fetchone()["id"]
                        created += 1
                    cursor.execute("SELECT severity,start_time FROM public.incidents WHERE id=%s FOR UPDATE", (incident_id,))
                    incident = cursor.fetchone()
                    cursor.execute("SELECT COALESCE(MAX(sequence_number),0) AS n FROM public.incident_events "
                                   "WHERE incident_id=%s", (incident_id,))
                    sequence = cursor.fetchone()["n"]
                    reasons = []
                    for item, group_reason in members:
                        key = (item.kind, item.id)
                        if key in memberships:
                            reasons.append({"kind": item.kind, "id": item.id, "reason": "EXISTING"})
                            continue
                        matched = next((reason for prior in anchors.get(incident_id, [])
                                        if (reason := relationship(item, prior, links, window=window))), None)
                        reason = matched or group_reason
                        if item.kind == "EVENT":
                            sequence += 1
                            cursor.execute("INSERT INTO public.incident_events "
                                           "(incident_id,event_id,sequence_number,relationship_type) VALUES (%s,%s,%s,%s)",
                                           (incident_id, item.id, sequence, reason))
                        else:
                            cursor.execute("INSERT INTO public.incident_anomalies "
                                           "(incident_id,anomaly_id,relationship_type) VALUES (%s,%s,%s)",
                                           (incident_id, item.id, reason))
                        memberships[key] = (incident_id, "DETECTED")
                        anchors.setdefault(incident_id, []).append(item)
                        attached += 1
                        reasons.append({"kind": item.kind, "id": item.id, "reason": reason})
                    best = max((incident["severity"], severity_of(items)), key=SEVERITY.__getitem__)
                    start = min(incident["start_time"], *(item.observed_at for item in items))
                    if best != incident["severity"] or start != incident["start_time"]:
                        cursor.execute("UPDATE public.incidents SET severity=%s,start_time=%s WHERE id=%s",
                                       (best, start, incident_id))
                    results.append({"incident_id": incident_id, "created": not candidates,
                                    "evidence": reasons})
                return {"incidents": results, "skipped_ids": sorted(set(skipped), key=str),
                        "created": created, "attached": attached}

    def list(self, *, page: int, limit: int, status: str | None, severity: str | None) -> dict:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                where = "WHERE (%s::text IS NULL OR status=%s) AND (%s::text IS NULL OR severity=%s)"
                params = (status, status, severity, severity)
                cursor.execute("SELECT count(*) AS total FROM public.incidents " + where, params)
                total = cursor.fetchone()["total"]
                cursor.execute("SELECT id,title,description,severity,status,start_time,end_time,created_at,updated_at "
                               "FROM public.incidents " + where + " ORDER BY start_time DESC,id DESC LIMIT %s OFFSET %s",
                               (*params, limit, (page - 1) * limit))
                rows = cursor.fetchall()
        return {"data": rows, "pagination": {"page": page, "limit": limit, "total": total,
                                               "pages": (total + limit - 1) // limit}}

    def get(self, incident_id: UUID) -> dict | None:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id,title,description,severity,status,start_time,end_time,created_at,updated_at "
                               "FROM public.incidents WHERE id=%s", (incident_id,))
                incident = cursor.fetchone()
                if incident is None:
                    return None
                cursor.execute("SELECT ie.event_id AS id,ie.sequence_number,ie.relationship_type,e.device_id,"
                               "e.link_id,e.service_id,e.event_type,e.severity,e.status,e.timestamp,e.message "
                               "FROM public.incident_events ie JOIN public.events e ON e.id=ie.event_id "
                               "WHERE ie.incident_id=%s ORDER BY ie.sequence_number", (incident_id,))
                events = cursor.fetchall()
                cursor.execute("SELECT ia.anomaly_id AS id,ia.relationship_type,a.device_id,a.metric_id,"
                               "a.event_id,a.model_name,a.severity,a.detected_at,m.link_id,"
                               "m.timestamp AS observed_at "
                               "FROM public.incident_anomalies ia JOIN public.anomalies a ON a.id=ia.anomaly_id "
                               "LEFT JOIN public.metrics m ON m.id=a.metric_id "
                               "WHERE ia.incident_id=%s ORDER BY observed_at,ia.anomaly_id", (incident_id,))
                anomalies = cursor.fetchall()
        return {**incident, "events": events, "anomalies": anomalies}
