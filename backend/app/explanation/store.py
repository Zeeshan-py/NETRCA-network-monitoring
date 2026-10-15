"""One read-only snapshot of incident evidence and its exact analysis runs."""
from dataclasses import dataclass
from uuid import UUID

from psycopg.rows import dict_row
from pydantic import ValidationError

from app.core.config import Settings
from app.db.connection import transaction
from app.impact.models import ImpactRun
from app.impact.store import _bindings, _digest, _topology_input
from app.rca.models import Observation, RcaRun
from app.rca.store import _input_fingerprint, _load_inputs
from app.topology.graph import TopologyGraph


class ExplanationNotReady(ValueError):
    """The latest stored analysis cannot be explained safely."""


@dataclass(frozen=True)
class Snapshot:
    incident_id: UUID
    observations: list[Observation]
    topology: TopologyGraph
    rca: RcaRun
    impact: ImpactRun | None


class ExplanationStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def load(self, incident_id: UUID) -> Snapshot:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                observations, topology, limitations = _load_inputs(cursor, incident_id)
                cursor.execute(
                    "SELECT id,incident_id,analysis_version,input_fingerprint,status,result,"
                    "created_at,last_analyzed_at FROM public.rca_runs WHERE incident_id=%s "
                    "ORDER BY last_analyzed_at DESC,id DESC LIMIT 1", (incident_id,))
                row = cursor.fetchone()
                if row is None:
                    raise ExplanationNotReady("RCA_REQUIRED")
                try:
                    rca = RcaRun.model_validate(row)
                except ValidationError:
                    raise ExplanationNotReady("INVALID_RCA") from None
                if (rca.incident_id != incident_id or rca.result.incident_id != incident_id
                        or rca.status != rca.result.status
                        or rca.input_fingerprint != _input_fingerprint(
                            observations, topology, self.settings.rca_timing_window_seconds, limitations)):
                    raise ExplanationNotReady("STALE_OR_MISMATCHED_RCA")
                cursor.execute(
                    "SELECT id,rca_run_id,analysis_version,input_fingerprint,topology_fingerprint,"
                    "status,result,created_at,last_analyzed_at FROM public.impact_runs "
                    "WHERE rca_run_id=%s ORDER BY last_analyzed_at DESC,id DESC LIMIT 1", (rca.id,))
                row = cursor.fetchone()
                try:
                    impact = ImpactRun.model_validate(row) if row else None
                except ValidationError:
                    raise ExplanationNotReady("INVALID_IMPACT") from None
                if impact is not None:
                    current_topology_input = _topology_input(topology, _bindings(cursor))
                    if (impact.rca_run_id != rca.id or impact.result.rca_run_id != rca.id
                            or impact.result.incident_id != incident_id
                            or impact.status != impact.result.status
                            or impact.topology_fingerprint != _digest(current_topology_input)
                            or impact.result.topology_input != current_topology_input):
                        raise ExplanationNotReady("STALE_OR_MISMATCHED_IMPACT")
                return Snapshot(incident_id, observations, topology, rca, impact)
