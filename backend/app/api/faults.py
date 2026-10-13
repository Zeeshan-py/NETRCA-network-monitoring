"""Loopback-only control of the owned Mininet lab's fault lifecycle."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable
from app.faults.controller import FaultNotFound
from app.faults.models import FaultRequest
from app.network.errors import NetworkError


router = APIRouter(tags=["faults"])
FAULT_TYPES = ["INTERFACE_FAILURE", "LINK_FAILURE", "PACKET_LOSS", "HIGH_LATENCY"]


def _access(request: Request, *, write: bool = False):
    if denied := _local_only(request, control=write):
        return denied
    if write and not request.app.state.settings.fault_injection_enabled:
        return _error(403, "FAULT_INJECTION_DISABLED", "Fault injection is disabled")
    return None


def _success(data, *, status: int = 200):
    return JSONResponse(status_code=status, content=jsonable_encoder({"success": True, "data": data}))


def _record_response(record, *, created: bool = False):
    if (record.error_code and record.restoration_result == "FAILED") or record.end_reason == "APPLY_FAILED":
        return JSONResponse(status_code=503, content=jsonable_encoder({
            "success": False, "error": {"code": record.error_code or "FAULT_APPLY_FAILED",
                                          "message": "Fault operation or restoration failed"},
            "data": record.model_dump(mode="json")}))
    return _success(record.model_dump(mode="json"), status=201 if created else 200)


@router.get("/faults/types")
def fault_types(request: Request):
    if denied := _access(request):
        return denied
    return _success(FAULT_TYPES)


@router.post("/faults/inject")
def inject_fault(request: Request, value: FaultRequest):
    if denied := _access(request, write=True):
        return denied
    try:
        return _record_response(request.app.state.fault_controller.inject(value), created=True)
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))


@router.get("/faults")
def list_faults(request: Request, source: Literal["local", "stored"] = "local",
                page: int = Query(1, ge=1, le=10000), limit: int = Query(20, ge=1, le=100)):
    if denied := _access(request):
        return denied
    try:
        result = (request.app.state.fault_controller.list(page=page, limit=limit) if source == "local"
                  else request.app.state.fault_controller.store.list(page=page, limit=limit))
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Stored fault history is unavailable")
    return JSONResponse(content=jsonable_encoder({"success": True, **result}))


@router.get("/faults/{fault_id}")
def get_fault(request: Request, fault_id: UUID, source: Literal["local", "stored"] = "local"):
    if denied := _access(request):
        return denied
    try:
        record = (request.app.state.fault_controller.get(fault_id).model_dump(mode="json") if source == "local"
                  else request.app.state.fault_controller.store.get(fault_id))
    except FaultNotFound:
        return _error(404, "FAULT_NOT_FOUND", "Fault was not found in this process")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Stored fault history is unavailable")
    if record is None:
        return _error(404, "FAULT_NOT_FOUND", "Fault was not found")
    return _success(record)


@router.post("/faults/{fault_id}/recover")
def recover_fault(request: Request, fault_id: UUID):
    if denied := _access(request, write=True):
        return denied
    try:
        return _record_response(request.app.state.fault_controller.recover(fault_id))
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))


@router.post("/faults/{fault_id}/cancel")
def cancel_fault(request: Request, fault_id: UUID):
    if denied := _access(request, write=True):
        return denied
    try:
        return _record_response(request.app.state.fault_controller.recover(fault_id, cancel=True))
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))


@router.post("/faults/reset")
def reset_faults(request: Request):
    if denied := _access(request, write=True):
        return denied
    controller = request.app.state.fault_controller
    try:
        record = controller.reset()
        return _record_response(record) if record is not None else _success([])
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))
