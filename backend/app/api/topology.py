"""Local development access to stored topology; writes are disabled by default."""
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable
from app.topology.models import DeviceCreate, LinkCreate, SnapshotCreate
from app.topology.store import TopologyConflict, TopologyNotFound


router = APIRouter(tags=["topology"])


def _access(request: Request, *, write: bool = False) -> JSONResponse | None:
    denied = _local_only(request, control=write)
    if denied:
        return denied
    if write and not request.app.state.settings.topology_writes_enabled:
        return _error(403, "TOPOLOGY_WRITES_DISABLED", "Topology writes are disabled")
    return None


def _success(data: object, status: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status, content={"success": True, "data": data})


@router.get("/topology/snapshots")
def list_snapshots(request: Request, limit: int = Query(default=20, ge=1, le=100)):
    if denied := _access(request):
        return denied
    try:
        items = request.app.state.topology_store.list_snapshots(limit)
        return _success([item.model_dump(mode="json") for item in items])
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")


@router.post("/topology/snapshots")
def create_snapshot(request: Request, value: SnapshotCreate):
    if denied := _access(request, write=True):
        return denied
    try:
        item = request.app.state.topology_store.create_snapshot(value.reason)
        return _success(item.model_dump(mode="json"), 201)
    except TopologyConflict:
        return _error(409, "INVALID_TOPOLOGY", "Stored topology failed validation")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")


@router.get("/devices")
def list_devices(request: Request):
    if denied := _access(request):
        return denied
    try:
        graph = request.app.state.topology_store.load()
        return _success([device.model_dump(mode="json") for device in graph.devices])
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")


@router.get("/devices/{device_id}")
def get_device(request: Request, device_id: UUID):
    if denied := _access(request):
        return denied
    try:
        value = request.app.state.topology_store.get_device(device_id)
        return _success(value.model_dump(mode="json"))
    except TopologyNotFound:
        return _error(404, "DEVICE_NOT_FOUND", "Device was not found")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")


@router.post("/devices")
def create_device(request: Request, value: DeviceCreate):
    if denied := _access(request, write=True):
        return denied
    try:
        record = request.app.state.topology_store.create_device(value)
        return _success(record.model_dump(mode="json"), 201)
    except TopologyConflict as error:
        return _error(409, error.code, "Device conflicts with existing topology")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")


@router.get("/links")
def list_links(request: Request):
    if denied := _access(request):
        return denied
    try:
        graph = request.app.state.topology_store.load()
        return _success([link.model_dump(mode="json") for link in graph.links])
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")


@router.get("/links/{link_id}")
def get_link(request: Request, link_id: UUID):
    if denied := _access(request):
        return denied
    try:
        value = request.app.state.topology_store.get_link(link_id)
        return _success(value.model_dump(mode="json"))
    except TopologyNotFound:
        return _error(404, "LINK_NOT_FOUND", "Link was not found")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")


@router.post("/links")
def create_link(request: Request, value: LinkCreate):
    if denied := _access(request, write=True):
        return denied
    try:
        record = request.app.state.topology_store.create_link(value)
        return _success(record.model_dump(mode="json"), 201)
    except TopologyConflict as error:
        return _error(409, error.code, "Link conflicts with existing topology")
    except DatabaseUnavailable:
        return _error(503, "DATABASE_UNAVAILABLE", "Topology storage is unavailable")
