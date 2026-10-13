"""Local-only, bounded observations of the running simulated network."""
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.network import _error, _local_only
from app.monitoring.models import MonitoringResponse, MonitoringSnapshot, ProbeRequest, ProbeResponse
from app.network.errors import NetworkError
from app.network.topology import TOPOLOGY_NAME


router = APIRouter(tags=["monitoring"])


@router.get("/network/monitoring", response_model=MonitoringResponse)
def monitoring_snapshot(request: Request):
    if denied := _local_only(request, control=False):
        return denied
    manager = request.app.state.network_manager
    state = manager.get_status().state
    if state != "RUNNING":
        snapshot = MonitoringSnapshot(
            observed_at=datetime.now(timezone.utc), topology_name=TOPOLOGY_NAME,
            network_state=state if state in {"STOPPED", "DISABLED", "UNAVAILABLE"} else "UNAVAILABLE",
            collection_status="UNAVAILABLE", devices=[], links=[], errors=["NETWORK_NOT_RUNNING"],
        )
        return MonitoringResponse(data=snapshot)
    try:
        future = manager.monitor_snapshot()
        try:
            result = future.result(timeout=request.app.state.settings.simulation_operation_timeout_seconds)
        except FutureTimeout:
            return _error(202, "NETWORK_OPERATION_IN_PROGRESS", "Monitoring snapshot is still in progress")
        return MonitoringResponse(data=result)
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))


@router.post("/network/monitoring/probe", response_model=ProbeResponse)
def monitoring_probe(request: Request, value: ProbeRequest):
    if denied := _local_only(request, control=True):
        return denied
    manager = request.app.state.network_manager
    try:
        future = manager.probe_hosts(value.source, value.destination,
                                     count=value.count, timeout_seconds=value.timeout_seconds)
        try:
            result = future.result(timeout=request.app.state.settings.simulation_operation_timeout_seconds)
        except FutureTimeout:
            return _error(202, "NETWORK_OPERATION_IN_PROGRESS", "Monitoring probe is still in progress")
        body = ProbeResponse(data=result)
        return JSONResponse(status_code=200, content=body.model_dump(mode="json"))
    except NetworkError as error:
        return _error(error.http_status, error.code, str(error))
