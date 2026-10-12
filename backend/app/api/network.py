"""Local development simulator endpoints. No arbitrary host commands or input."""
from concurrent.futures import TimeoutError as FutureTimeout
from ipaddress import IPv6Address, ip_address
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.network.errors import NetworkError
from app.network.manager import NetworkManager
from app.network.models import ConnectivityResponse, OperationResponse, StatusResponse, TopologyResponse

router = APIRouter(tags=["network"])


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"success": False, "error": {"code": code, "message": message}})


def _local_only(request: Request, *, control: bool) -> JSONResponse | None:
    settings: Settings = request.app.state.settings
    peer = request.client.host if request.client else ""
    try:
        address = ip_address(peer)
        mapped = address.ipv4_mapped if isinstance(address, IPv6Address) else None
        if not (address.is_loopback or mapped is not None and mapped.is_loopback):
            raise ValueError
    except ValueError:
        return _error(403, "LOCAL_ONLY", "Network simulation is available only from the local host")
    origin = request.headers.get("origin")
    if origin:
        try:
            host = urlsplit(origin).hostname
        except ValueError:
            host = None
        if origin not in settings.allowed_origins or host not in {"localhost", "127.0.0.1", "::1"}:
            return _error(403, "LOCAL_ONLY", "Network simulation requires a configured local origin")
    if control and request.headers.get("X-NetRCA-Local-Control") != "1":
        return _error(403, "LOCAL_CONTROL_REQUIRED", "Local control header is required")
    return None


def _manager(request: Request) -> NetworkManager:
    return request.app.state.network_manager


def _run(request: Request, operation: str, message: str) -> JSONResponse:
    denied = _local_only(request, control=True)
    if denied:
        return denied
    manager = _manager(request)
    try:
        future = {
            "start": manager.start_network,
            "stop": manager.stop_network,
            "restart": lambda: manager.reset_network(require_running=True),
            "reset": manager.reset_network,
        }[operation]()
        try:
            future.result(timeout=request.app.state.settings.simulation_operation_timeout_seconds)
        except FutureTimeout:
            status = manager.get_status()
            body = OperationResponse(data=status, message="Network operation is still in progress")
            return JSONResponse(status_code=202, content=body.model_dump(mode="json"))
        body = OperationResponse(data=manager.get_status(), message=message)
        return JSONResponse(status_code=200, content=body.model_dump(mode="json"))
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))


@router.get("/network/status", response_model=StatusResponse)
def network_status(request: Request):
    denied = _local_only(request, control=False)
    if denied:
        return denied
    return StatusResponse(data=_manager(request).get_status())


@router.get("/topology", response_model=TopologyResponse)
def topology(request: Request):
    denied = _local_only(request, control=False)
    if denied:
        return denied
    try:
        return TopologyResponse(data=_manager(request).get_topology())
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))


@router.post("/network/start", response_model=OperationResponse)
def start(request: Request):
    return _run(request, "start", "Network started")


@router.post("/network/stop", response_model=OperationResponse)
def stop(request: Request):
    return _run(request, "stop", "Network stopped")


@router.post("/network/restart", response_model=OperationResponse)
def restart(request: Request):
    return _run(request, "restart", "Network restarted")


@router.post("/network/reset", response_model=OperationResponse)
def reset(request: Request):
    return _run(request, "reset", "Network reset to initial topology")


@router.post("/network/connectivity-test", response_model=ConnectivityResponse)
def connectivity_test(request: Request):
    denied = _local_only(request, control=True)
    if denied:
        return denied
    manager = _manager(request)
    try:
        future = manager.test_connectivity(timeout=2)
        try:
            result = future.result(timeout=request.app.state.settings.simulation_operation_timeout_seconds)
        except FutureTimeout:
            return _error(202, "NETWORK_OPERATION_IN_PROGRESS", "Connectivity test is still in progress")
        body = ConnectivityResponse(data=result)
        return JSONResponse(status_code=200 if result.connected else 503, content=body.model_dump(mode="json"))
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))
