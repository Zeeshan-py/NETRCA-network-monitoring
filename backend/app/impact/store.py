"""Transactional, idempotent persistence tied to a current validated RCA run."""
from hashlib import sha256
import json
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from app.core.config import Settings
from app.db.connection import transaction
from app.impact.engine import analyze
from app.impact.models import ImpactRun
from app.rca.models import RcaRun
from app.rca.store import IncidentNotFound, _input_fingerprint, _load_inputs


ANALYSIS_VERSION = "IMPACT_RULES_V1"


class RcaNotFound(LookupError):
    pass


class StaleRca(ValueError):
    pass


class InvalidStoredAnalysis(ValueError):
    pass


def _digest(value: dict) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _bindings(cursor) -> list[dict]:
    cursor.execute("SELECT ds.device_id,ds.service_id,ds.status,s.status AS service_status "
                   "FROM public.device_services ds JOIN public.services s ON s.id=ds.service_id "
                   "ORDER BY ds.device_id,ds.service_id")
    return [dict(row) for row in cursor.fetchall()]


def _topology_input(topology, bindings):
    return {
        "devices": [{"id": str(d.id), "status": d.status, "is_active": d.is_active}
                    for d in sorted(topology.devices, key=lambda x: str(x.id))],
        "links": [{"id": str(l.id), "source_device_id": str(l.source_device_id),
                   "destination_device_id": str(l.destination_device_id), "status": l.status}
                  for l in sorted(topology.links, key=lambda x: str(x.id))],
        "service_bindings": [{"device_id": str(b["device_id"]), "service_id": str(b["service_id"]),
                              "status": b["status"], "service_status": b["service_status"]}
                             for b in bindings],
    }


def _latest_rca(cursor, incident_id: UUID) -> RcaRun:
    cursor.execute("SELECT id,incident_id,analysis_version,input_fingerprint,status,result,"
                   "created_at,last_analyzed_at FROM public.rca_runs WHERE incident_id=%s "
                   "ORDER BY last_analyzed_at DESC,id DESC LIMIT 1", (incident_id,))
    row = cursor.fetchone()
    if row is None:
        raise RcaNotFound("No RCA run exists")
    try:
        return RcaRun.model_validate(row)
    except ValidationError:
        raise InvalidStoredAnalysis("Stored RCA result failed validation") from None


class ImpactStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def analyze(self, incident_id: UUID) -> ImpactRun:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                # Phase 9 membership, Phase 11 RCA, then Phase 12 impact writer order.
                for phase in (9, 11, 12):
                    cursor.execute("SELECT pg_advisory_xact_lock(47301, %s)", (phase,))
                observations, topology, limitations = _load_inputs(cursor, incident_id)
                rca = _latest_rca(cursor, incident_id)
                if rca.input_fingerprint != _input_fingerprint(
                        observations, topology, self.settings.rca_timing_window_seconds, limitations):
                    raise StaleRca("RCA inputs changed; rerun RCA before impact analysis")
                bindings = _bindings(cursor)
                topology_input = _topology_input(topology, bindings)
                topology_fingerprint = _digest(topology_input)
                result = analyze(rca, observations, topology, bindings)
                result.topology_input = topology_input
                result.limitations = sorted(set(result.limitations) | set(rca.result.limitations))
                fingerprint = _digest({"version": ANALYSIS_VERSION, "rca_run_id": str(rca.id),
                                       "rca_input_fingerprint": rca.input_fingerprint,
                                       "topology_fingerprint": topology_fingerprint,
                                       "result": result.model_dump(mode="json")})
                cursor.execute(
                    "INSERT INTO public.impact_runs "
                    "(rca_run_id,analysis_version,input_fingerprint,topology_fingerprint,status,result,last_analyzed_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,clock_timestamp()) "
                    "ON CONFLICT (rca_run_id,analysis_version,input_fingerprint) "
                    "DO UPDATE SET last_analyzed_at=GREATEST(public.impact_runs.last_analyzed_at,clock_timestamp()) "
                    "RETURNING id,rca_run_id,analysis_version,input_fingerprint,topology_fingerprint,status,"
                    "result,created_at,last_analyzed_at",
                    (rca.id, ANALYSIS_VERSION, fingerprint, topology_fingerprint,
                     result.status, Jsonb(result.model_dump(mode="json"))),
                )
                return ImpactRun.model_validate(cursor.fetchone())

    def latest(self, incident_id: UUID) -> ImpactRun | None:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id FROM public.incidents WHERE id=%s", (incident_id,))
                if cursor.fetchone() is None:
                    raise IncidentNotFound("Incident not found")
                rca = _latest_rca(cursor, incident_id)
                cursor.execute("SELECT id,rca_run_id,analysis_version,input_fingerprint,topology_fingerprint,"
                               "status,result,created_at,last_analyzed_at FROM public.impact_runs "
                               "WHERE rca_run_id=%s ORDER BY last_analyzed_at DESC,id DESC LIMIT 1", (rca.id,))
                row = cursor.fetchone()
                try:
                    return ImpactRun.model_validate(row) if row else None
                except ValidationError:
                    raise InvalidStoredAnalysis("Stored impact result failed validation") from None
