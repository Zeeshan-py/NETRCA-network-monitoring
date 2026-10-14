"""Local-only Phase 11 analysis control and latest ranked result."""
from uuid import UUID

from fastapi import APIRouter, Request

from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable
from app.rca.models import RcaResponse
from app.rca.store import AnalysisLimit, IncidentNotFound


router = APIRouter(tags=["rca"])


@router.post("/incidents/{incident_id}/root-cause/analyze", response_model=RcaResponse)
def analyze_incident(request: Request, incident_id: UUID):
    if denied := _local_only(request, control=True):
        return denied
    if not request.app.state.settings.rca_writes_enabled:
        return _error(403, "RCA_WRITES_DISABLED", "RCA writes are disabled")
    try:
        result = request.app.state.rca_store.analyze(incident_id)
        return RcaResponse(data=result)
    except IncidentNotFound:
        return _error(404, "INCIDENT_NOT_FOUND", "Incident was not found")
    except AnalysisLimit:
        return _error(409, "ANALYSIS_LIMIT", "Incident has too much evidence for one RCA run")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "RCA storage is unavailable")


@router.get("/incidents/{incident_id}/root-causes", response_model=RcaResponse)
def latest_analysis(request: Request, incident_id: UUID):
    if denied := _local_only(request, control=False):
        return denied
    try:
        result = request.app.state.rca_store.latest(incident_id)
        if result is None:
            return _error(404, "RCA_NOT_FOUND", "No RCA run exists for this incident")
        return RcaResponse(data=result)
    except IncidentNotFound:
        return _error(404, "INCIDENT_NOT_FOUND", "Incident was not found")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "RCA storage is unavailable")
