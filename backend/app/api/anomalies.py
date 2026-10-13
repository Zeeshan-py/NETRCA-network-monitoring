"""Local-only anomaly analysis and stored finding history."""
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.anomaly.models import DetectionRequest
from app.anomaly.service import DuplicateObservation
from app.anomaly.store import MetricNotFound, StoredMetricInvalid
from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable


router = APIRouter(tags=["anomalies"])


def _access(request: Request, *, write: bool = False):
    return _local_only(request, control=write)


def _success(value):
    return JSONResponse(content=jsonable_encoder({"success": True, "data": value}))


@router.post("/anomalies/detect")
def detect_anomalies(request: Request, value: DetectionRequest):
    if denied := _access(request, write=True):
        return denied
    if value.persist and not request.app.state.settings.anomaly_writes_enabled:
        return _error(403, "ANOMALY_WRITES_DISABLED", "Anomaly persistence is disabled")
    try:
        return _success(request.app.state.anomaly_service.run(value))
    except DuplicateObservation:
        return _error(409, "DUPLICATE_OBSERVATION", "Conflicting observations share a key")
    except MetricNotFound:
        return _error(404, "METRIC_NOT_FOUND", "A stored metric was not found")
    except StoredMetricInvalid:
        return _error(409, "STORED_METRIC_INVALID", "Stored metric is not valid Phase 6 evidence")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Stored metrics are unavailable")


@router.get("/anomalies/statistics")
def anomaly_statistics(request: Request):
    if denied := _access(request):
        return denied
    try:
        return _success(request.app.state.anomaly_store.statistics())
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Anomaly history is unavailable")


@router.get("/anomalies")
def list_anomalies(request: Request, page: int = Query(1, ge=1, le=10000),
                   limit: int = Query(20, ge=1, le=100), device_id: UUID | None = None,
                   is_anomaly: bool | None = None):
    if denied := _access(request):
        return denied
    try:
        result = request.app.state.anomaly_store.list(page=page, limit=limit,
                                                      device_id=device_id, is_anomaly=is_anomaly)
        return JSONResponse(content=jsonable_encoder({"success": True, **result}))
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Anomaly history is unavailable")


@router.get("/anomalies/{anomaly_id}")
def get_anomaly(request: Request, anomaly_id: UUID):
    if denied := _access(request):
        return denied
    try:
        result = request.app.state.anomaly_store.get(anomaly_id)
        if result is None:
            return _error(404, "ANOMALY_NOT_FOUND", "Anomaly was not found")
        return _success(result)
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Anomaly history is unavailable")
