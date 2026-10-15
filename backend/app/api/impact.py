"""Local-only Phase 12 impact and failure-chain routes."""
from uuid import UUID

from fastapi import APIRouter, Request

from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable
from app.impact.models import ImpactResponse
from app.impact.store import InvalidStoredAnalysis, RcaNotFound, StaleRca
from app.rca.store import AnalysisLimit, IncidentNotFound


router = APIRouter(tags=["impact"])


def _get(request: Request, incident_id: UUID):
    if denied := _local_only(request, control=False):
        return denied
    try:
        run = request.app.state.impact_store.latest(incident_id)
        if run is None:
            return _error(404, "IMPACT_NOT_FOUND", "No impact analysis exists for the current RCA run")
        return ImpactResponse(data=run)
    except IncidentNotFound:
        return _error(404, "INCIDENT_NOT_FOUND", "Incident was not found")
    except RcaNotFound:
        return _error(404, "RCA_NOT_FOUND", "No RCA run exists for this incident")
    except InvalidStoredAnalysis:
        return _error(409, "INVALID_STORED_ANALYSIS", "Stored analysis failed validation")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Impact storage is unavailable")


@router.post("/incidents/{incident_id}/impact/analyze", response_model=ImpactResponse)
def analyze_incident(request: Request, incident_id: UUID):
    if denied := _local_only(request, control=True):
        return denied
    if not request.app.state.settings.impact_writes_enabled:
        return _error(403, "IMPACT_WRITES_DISABLED", "Impact writes are disabled")
    try:
        return ImpactResponse(data=request.app.state.impact_store.analyze(incident_id))
    except IncidentNotFound:
        return _error(404, "INCIDENT_NOT_FOUND", "Incident was not found")
    except RcaNotFound:
        return _error(404, "RCA_NOT_FOUND", "No RCA run exists for this incident")
    except (StaleRca, InvalidStoredAnalysis):
        return _error(409, "RCA_INPUT_INVALID", "RCA is stale or its stored input is invalid")
    except AnalysisLimit:
        return _error(409, "ANALYSIS_LIMIT", "Incident has too much evidence for one analysis")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Impact storage is unavailable")


@router.get("/incidents/{incident_id}/impact", response_model=ImpactResponse)
def latest_impact(request: Request, incident_id: UUID):
    return _get(request, incident_id)


@router.get("/incidents/{incident_id}/failure-chain", response_model=ImpactResponse)
def latest_failure_chain(request: Request, incident_id: UUID):
    return _get(request, incident_id)
