"""Local-only, opt-in Phase 13 explanation endpoint."""
from uuid import UUID

from fastapi import APIRouter, Request

from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable
from app.explanation.models import ExplanationResponse
from app.explanation.provider import ProviderUnavailable
from app.explanation.store import ExplanationNotReady
from app.rca.store import AnalysisLimit, IncidentNotFound


router = APIRouter(tags=["ai"])


@router.post("/ai/incidents/{incident_id}/explain", response_model=ExplanationResponse)
def explain_incident(request: Request, incident_id: UUID):
    if denied := _local_only(request, control=True):
        return denied
    if not request.app.state.settings.gemini_enabled:
        return _error(403, "GEMINI_DISABLED", "Gemini explanations are disabled")
    try:
        return ExplanationResponse(data=request.app.state.explanation_service.explain(incident_id))
    except IncidentNotFound:
        return _error(404, "INCIDENT_NOT_FOUND", "Incident was not found")
    except ExplanationNotReady as error:
        if str(error) == "RCA_REQUIRED":
            return _error(409, "RCA_REQUIRED", "Run deterministic RCA before requesting an explanation")
        return _error(409, "ANALYSIS_NOT_READY", "Stored analysis or evidence is incomplete or stale")
    except AnalysisLimit:
        return _error(409, "ANALYSIS_LIMIT", "Incident has too much evidence for one explanation")
    except ProviderUnavailable:
        return _error(503, "GEMINI_UNAVAILABLE", "Gemini explanation is unavailable; retry later")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Explanation storage is unavailable")
