"""Local-only, read-only analysis of validated physical topology."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.network import _error, _local_only
from app.db.connection import DatabaseUnavailable
from app.network.errors import NetworkError
from app.topology.analysis import GraphAnalysis
from app.topology.graph import from_mininet


router = APIRouter(tags=["graph-analysis"])


def _analysis(request: Request, source: Literal["live", "stored"]):
    if source == "stored":
        topology = request.app.state.topology_store.load()
    else:
        topology = from_mininet(request.app.state.network_manager.get_topology())
    return GraphAnalysis(topology)


def _result(value) -> JSONResponse:
    return JSONResponse(content={"success": True, "data": value.model_dump(mode="json")})


def _failure(error: Exception) -> JSONResponse:
    if isinstance(error, DatabaseUnavailable):
        return _error(503, "DATABASE_UNAVAILABLE", "Topology or incident storage is unavailable")
    if isinstance(error, NetworkError):
        return _error(error.http_status, error.code, str(error))
    if isinstance(error, ValueError):
        return _error(409, "INVALID_TOPOLOGY", "Topology failed validation")
    raise error


@router.get("/topology/analysis")
def topology_analysis(request: Request, source: Literal["live", "stored"] = "live"):
    if denied := _local_only(request, control=False):
        return denied
    try:
        return _result(_analysis(request, source).summary())
    except (DatabaseUnavailable, NetworkError, ValueError) as error:
        return _failure(error)


@router.get("/topology/path")
def topology_path(request: Request, source_id: UUID, destination_id: UUID,
                  source: Literal["live", "stored"] = "live"):
    if denied := _local_only(request, control=False):
        return denied
    try:
        return _result(_analysis(request, source).path(source_id, destination_id))
    except KeyError:
        return _error(404, "DEVICE_NOT_FOUND", "Topology device was not found")
    except (DatabaseUnavailable, NetworkError, ValueError) as error:
        return _failure(error)


@router.get("/topology/devices/{device_id}/neighbors")
def topology_neighbors(request: Request, device_id: UUID,
                       source: Literal["live", "stored"] = "live"):
    if denied := _local_only(request, control=False):
        return denied
    try:
        return _result(_analysis(request, source).neighbors(device_id))
    except KeyError:
        return _error(404, "DEVICE_NOT_FOUND", "Topology device was not found")
    except (DatabaseUnavailable, NetworkError, ValueError) as error:
        return _failure(error)


@router.get("/topology/importance")
def topology_importance(request: Request, source: Literal["live", "stored"] = "live"):
    if denied := _local_only(request, control=False):
        return denied
    try:
        return _result(_analysis(request, source).importance())
    except (DatabaseUnavailable, NetworkError, ValueError) as error:
        return _failure(error)


@router.get("/incidents/{incident_id}/topology-context")
def incident_topology_context(request: Request, incident_id: UUID):
    if denied := _local_only(request, control=False):
        return denied
    try:
        incident = request.app.state.incident_store.get(incident_id)
        if incident is None:
            return _error(404, "INCIDENT_NOT_FOUND", "Incident was not found")
        return _result(_analysis(request, "stored").incident_context(incident))
    except (DatabaseUnavailable, NetworkError, ValueError) as error:
        return _failure(error)
