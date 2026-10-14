"""Transactional Phase 11 analysis of validated, stored incident evidence."""
from hashlib import sha256
import json
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.correlation.store import _anomaly, _event
from app.db.connection import transaction
from app.rca.engine import analyze
from app.rca.models import Observation, RcaRun
from app.topology.graph import TopologyGraph
from app.topology.models import Device, Link
from app.topology.store import DEVICE_COLUMNS, LINK_COLUMNS


class IncidentNotFound(LookupError):
    pass


class AnalysisLimit(ValueError):
    pass


ANALYSIS_VERSION = "RULES_V1"
MAX_EVIDENCE_PER_KIND = 100


def _input_fingerprint(observations: list[Observation], topology: TopologyGraph,
                       window_seconds: int, limitations: list[str]) -> str:
    """Hash the exact validated inputs and rules, independent of query order."""
    payload = {
        "version": ANALYSIS_VERSION,
        "window_seconds": window_seconds,
        "observations": [item.model_dump(mode="json") for item in sorted(observations,
                         key=lambda row: (row.kind, str(row.id)))],
        "devices": [{"id": str(row.id), "status": row.status, "is_active": row.is_active}
                    for row in sorted(topology.devices, key=lambda row: str(row.id))],
        "links": [{"id": str(row.id), "source": str(row.source_device_id),
                   "destination": str(row.destination_device_id), "status": row.status}
                  for row in sorted(topology.links, key=lambda row: str(row.id))],
        "limitations": sorted(limitations),
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _load_inputs(cursor, incident_id: UUID) -> tuple[list[Observation], TopologyGraph, list[str]]:
    cursor.execute("SELECT id FROM public.incidents WHERE id=%s", (incident_id,))
    if cursor.fetchone() is None:
        raise IncidentNotFound("Incident not found")
    cursor.execute("SELECT e.id,e.device_id,e.link_id,e.service_id,e.event_type,e.severity,e.status,"
                   "e.timestamp,e.message,e.metadata "
                   "FROM public.incident_events ie JOIN public.events e ON e.id=ie.event_id "
                   "WHERE ie.incident_id=%s ORDER BY ie.sequence_number LIMIT %s",
                   (incident_id, MAX_EVIDENCE_PER_KIND + 1))
    event_rows = cursor.fetchall()
    cursor.execute("SELECT a.id,a.device_id,a.metric_id,a.event_id,a.model_name,a.is_anomaly,"
                   "a.severity,a.metadata,m.device_id AS metric_device_id,m.link_id AS metric_link_id,"
                   "m.metric_type,m.value,m.unit,m.timestamp AS metric_timestamp,m.metadata AS metric_metadata "
                   "FROM public.incident_anomalies ia JOIN public.anomalies a ON a.id=ia.anomaly_id "
                   "LEFT JOIN public.metrics m ON m.id=a.metric_id "
                   "WHERE ia.incident_id=%s ORDER BY ia.created_at,ia.anomaly_id LIMIT %s",
                   (incident_id, MAX_EVIDENCE_PER_KIND + 1))
    anomaly_rows = cursor.fetchall()
    if len(event_rows) > MAX_EVIDENCE_PER_KIND or len(anomaly_rows) > MAX_EVIDENCE_PER_KIND:
        raise AnalysisLimit("Incident evidence exceeds analysis limit")
    observations: list[Observation] = []
    invalid = 0
    for row in event_rows:
        item = _event(row)
        if item is None:
            invalid += 1
            continue
        observations.append(Observation(kind="EVENT", id=item.id, observed_at=item.observed_at,
                                        device_id=item.device_id, link_id=item.link_id,
                                        event_type=row["event_type"], event_status=row["status"]))
    for row in anomaly_rows:
        item = _anomaly(row)
        if item is None:
            invalid += 1
            continue
        observations.append(Observation(kind="ANOMALY", id=item.id, observed_at=item.observed_at,
                                        device_id=item.device_id, link_id=item.link_id,
                                        metric_id=item.metric_id, metric_type=row["metric_type"],
                                        metric_value=row["value"], source_event_id=item.event_id))
    cursor.execute(f"SELECT {DEVICE_COLUMNS} FROM public.devices ORDER BY id")
    devices = [Device.model_validate(row) for row in cursor.fetchall()]
    cursor.execute(f"SELECT {LINK_COLUMNS} FROM public.links ORDER BY id")
    links = [Link.model_validate(row) for row in cursor.fetchall()]
    limitations = ["INVALID_INCIDENT_EVIDENCE_SKIPPED"] if invalid else []
    # There is no incident_logs membership. Do not collect logs by mere time/device proximity.
    limitations.append("NO_DIRECT_INCIDENT_LOG_REFERENCES")
    return observations, TopologyGraph(devices, links), limitations


class RcaStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def analyze(self, incident_id: UUID) -> RcaRun:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                # Consistent lock order with Phase 9, then serialize concurrent RCA runs.
                cursor.execute("SELECT pg_advisory_xact_lock(47301, 9)")
                cursor.execute("SELECT pg_advisory_xact_lock(47301, 11)")
                observations, topology, limitations = _load_inputs(cursor, incident_id)
                fingerprint = _input_fingerprint(observations, topology,
                                                 self.settings.rca_timing_window_seconds, limitations)
                result = analyze(incident_id, observations, topology,
                                 window_seconds=self.settings.rca_timing_window_seconds,
                                 limitations=limitations)
                cursor.execute(
                    "INSERT INTO public.rca_runs "
                    "(incident_id,analysis_version,input_fingerprint,status,result,last_analyzed_at) "
                    "VALUES (%s,%s,%s,%s,%s,clock_timestamp()) "
                    "ON CONFLICT (incident_id,analysis_version,input_fingerprint) "
                    "DO UPDATE SET last_analyzed_at=GREATEST(public.rca_runs.last_analyzed_at,clock_timestamp()) "
                    "RETURNING id,incident_id,analysis_version,input_fingerprint,status,result,created_at,last_analyzed_at",
                    (incident_id, ANALYSIS_VERSION, fingerprint, result.status,
                     Jsonb(result.model_dump(mode="json"))),
                )
                return RcaRun.model_validate(cursor.fetchone())

    def latest(self, incident_id: UUID) -> RcaRun | None:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id FROM public.incidents WHERE id=%s", (incident_id,))
                if cursor.fetchone() is None:
                    raise IncidentNotFound("Incident not found")
                cursor.execute("SELECT id,incident_id,analysis_version,input_fingerprint,status,result,"
                               "created_at,last_analyzed_at FROM public.rca_runs WHERE incident_id=%s "
                               "ORDER BY last_analyzed_at DESC,id DESC LIMIT 1", (incident_id,))
                row = cursor.fetchone()
                return RcaRun.model_validate(row) if row else None
