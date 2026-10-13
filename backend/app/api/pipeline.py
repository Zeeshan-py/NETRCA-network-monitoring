"""Local, opt-in ingestion and bounded evidence history endpoints."""
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable
from app.monitoring.models import ProbeRequest
from app.network.errors import NetworkError
from app.pipeline.models import EventIn, LogIn, MetricIn
from app.pipeline.store import EvidenceConflict


router = APIRouter(tags=["evidence"])


class MetricBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[MetricIn] = Field(min_length=1, max_length=100)


def _access(request: Request, *, write: bool = False):
    if denied := _local_only(request, control=write):
        return denied
    if write and not request.app.state.settings.pipeline_writes_enabled:
        return _error(403, "PIPELINE_WRITES_DISABLED", "Evidence writes are disabled")
    return None


def _success(value, status: int = 200):
    return JSONResponse(status_code=status, content=jsonable_encoder({"success": True, **value}))


def _failure(error):
    if isinstance(error, DatabaseUnavailable):
        return _error(503, "DATABASE_UNAVAILABLE", "Evidence storage is unavailable")
    if isinstance(error, EvidenceConflict):
        return _error(409, error.code, "Evidence conflicts with stored resources or observation state")
    return _error(error.http_status, error.code, str(error))


@router.post("/metrics")
def ingest_metrics(request: Request, batch: MetricBatch):
    if denied := _access(request, write=True):
        return denied
    if any(item.source != "manual" for item in batch.items):
        return _error(422, "INVALID_SOURCE", "API metrics must use manual source")
    try:
        return _success({"data": request.app.state.evidence_store.ingest_metrics(batch.items)})
    except (DatabaseUnavailable, EvidenceConflict) as error:
        return _failure(error)


@router.post("/logs")
def ingest_log(request: Request, value: LogIn):
    if denied := _access(request, write=True):
        return denied
    if value.source != "operator":
        return _error(422, "INVALID_SOURCE", "API logs must use operator source")
    try:
        return _success({"data": request.app.state.evidence_store.ingest_log(value)})
    except (DatabaseUnavailable, EvidenceConflict) as error:
        return _failure(error)


@router.post("/events")
def ingest_event(request: Request, value: EventIn):
    if denied := _access(request, write=True):
        return denied
    if value.source != "operator":
        return _error(422, "INVALID_SOURCE", "API events must use operator source")
    try:
        return _success({"data": request.app.state.evidence_store.ingest_event(value)})
    except (DatabaseUnavailable, EvidenceConflict) as error:
        return _failure(error)


@router.post("/pipeline/collect")
def collect_snapshot(request: Request):
    if denied := _access(request, write=True):
        return denied
    manager = request.app.state.network_manager
    try:
        snapshot = manager.monitor_snapshot().result(
            timeout=request.app.state.settings.simulation_operation_timeout_seconds)
        result = request.app.state.evidence_store.ingest_snapshot(snapshot)
        return _success({"data": {"observed_at": snapshot.observed_at, **result}})
    except FutureTimeout:
        return _error(504, "COLLECTION_TIMEOUT", "Collection timed out; no evidence was stored")
    except NetworkError as error:
        if manager.get_status().state == "RUNNING":
            try:
                request.app.state.evidence_store.ingest_event(EventIn(
                    event_type="COLLECTION_FAILURE", severity="MEDIUM", source="netrca",
                    timestamp=datetime.now(timezone.utc), dedup_key="collection:mininet_snapshot",
                    message="Monitoring collection failed"))
            except (DatabaseUnavailable, EvidenceConflict):
                return _error(503, "COLLECTION_STORAGE_FAILED", "Collection failed and its event could not be stored")
        return _failure(error)
    except (DatabaseUnavailable, EvidenceConflict) as error:
        return _failure(error)


@router.post("/pipeline/probe")
def collect_probe(request: Request, value: ProbeRequest):
    if denied := _access(request, write=True):
        return denied
    try:
        probe = request.app.state.network_manager.probe_hosts(
            value.source, value.destination, count=value.count,
            timeout_seconds=value.timeout_seconds).result(
                timeout=request.app.state.settings.simulation_operation_timeout_seconds)
        result = request.app.state.evidence_store.ingest_probe(probe)
        return _success({"data": {"observed_at": probe.observed_at, "probe_status": probe.status, **result}})
    except FutureTimeout:
        return _error(504, "COLLECTION_TIMEOUT", "Probe timed out; no evidence was stored")
    except (DatabaseUnavailable, EvidenceConflict, NetworkError) as error:
        return _failure(error)


def _list(request: Request, table: str, page: int, limit: int, device_id: UUID | None,
          link_id: UUID | None, name: str | None, from_time: datetime | None,
          to_time: datetime | None):
    if denied := _access(request):
        return denied
    if (from_time and from_time.utcoffset() is None) or (to_time and to_time.utcoffset() is None) or (
        from_time and to_time and from_time > to_time
    ):
        return _error(422, "INVALID_TIME_RANGE", "Use timezone-aware timestamps in ascending order")
    try:
        return _success(request.app.state.evidence_store.list_records(
            table, page=page, limit=limit, device_id=device_id, link_id=link_id,
            name=name, from_time=from_time, to_time=to_time))
    except DatabaseUnavailable as error:
        return _failure(error)


@router.get("/metrics")
def list_metrics(request: Request, page: int = Query(1, ge=1, le=10000),
                 limit: int = Query(50, ge=1, le=100), device_id: UUID | None = None,
                 link_id: UUID | None = None,
                 metric_type: str | None = Query(None, max_length=32),
                 from_time: datetime | None = Query(None, alias="from"),
                 to_time: datetime | None = Query(None, alias="to")):
    return _list(request, "metrics", page, limit, device_id, link_id, metric_type, from_time, to_time)


@router.get("/logs")
def list_logs(request: Request, page: int = Query(1, ge=1, le=10000),
              limit: int = Query(50, ge=1, le=100), device_id: UUID | None = None,
              severity: str | None = Query(None, max_length=16),
              from_time: datetime | None = Query(None, alias="from"),
              to_time: datetime | None = Query(None, alias="to")):
    return _list(request, "logs", page, limit, device_id, None, severity, from_time, to_time)


@router.get("/events")
def list_events(request: Request, page: int = Query(1, ge=1, le=10000),
                limit: int = Query(50, ge=1, le=100), device_id: UUID | None = None,
                link_id: UUID | None = None,
                event_type: str | None = Query(None, max_length=64),
                from_time: datetime | None = Query(None, alias="from"),
                to_time: datetime | None = Query(None, alias="to")):
    return _list(request, "events", page, limit, device_id, link_id, event_type, from_time, to_time)
