"""Local-only Phase 9 correlation control and incident history."""
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.network import _error, _local_only
from app.correlation.models import CorrelationRequest
from app.correlation.store import AmbiguousMembership, EvidenceNotFound
from app.db.connection import DatabaseUnavailable


router = APIRouter(tags=["incidents"])


@router.post("/events/correlate")
def correlate_events(request: Request, value: CorrelationRequest):
    if denied := _local_only(request, control=True):
        return denied
    if not request.app.state.settings.correlation_writes_enabled:
        return _error(403, "CORRELATION_WRITES_DISABLED", "Incident correlation writes are disabled")
    try:
        result = request.app.state.incident_store.correlate(value)
        return JSONResponse(content=jsonable_encoder({"success": True, "data": result}))
    except EvidenceNotFound:
        return _error(404, "EVIDENCE_NOT_FOUND", "Stored validated evidence was not found")
    except AmbiguousMembership:
        return _error(409, "AMBIGUOUS_MEMBERSHIP", "Evidence already belongs to multiple incidents")
    except ValueError:
        return _error(409, "CORRELATION_LIMIT", "Correlation window contains too many incident anchors")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Incident storage is unavailable")


@router.get("/incidents")
def list_incidents(request: Request, page: int = Query(1, ge=1, le=10000),
                   limit: int = Query(20, ge=1, le=100),
                   status: str | None = Query(None, pattern="^(DETECTED|INVESTIGATING|ROOT_CAUSE_IDENTIFIED|RESOLVED|CLOSED)$"),
                   severity: str | None = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")):
    if denied := _local_only(request, control=False):
        return denied
    try:
        result = request.app.state.incident_store.list(page=page, limit=limit, status=status, severity=severity)
        return JSONResponse(content=jsonable_encoder({"success": True, **result}))
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Incident storage is unavailable")


@router.get("/incidents/{incident_id}")
def get_incident(request: Request, incident_id: UUID):
    if denied := _local_only(request, control=False):
        return denied
    try:
        result = request.app.state.incident_store.get(incident_id)
        if result is None:
            return _error(404, "INCIDENT_NOT_FOUND", "Incident was not found")
        return JSONResponse(content=jsonable_encoder({"success": True, "data": result}))
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Incident storage is unavailable")
