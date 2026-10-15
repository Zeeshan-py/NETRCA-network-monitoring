import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.network import router as network_router
from app.api.monitoring import router as monitoring_router
from app.api.pipeline import router as pipeline_router
from app.api.faults import router as faults_router
from app.api.anomalies import router as anomalies_router
from app.api.incidents import router as incidents_router
from app.api.topology import router as topology_router
from app.api.graph_analysis import router as graph_analysis_router
from app.api.rca import router as rca_router
from app.api.impact import router as impact_router
from app.api.ai import router as ai_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.network.manager import NetworkManager
from app.faults.controller import FaultController
from app.faults.store import FaultStore
from app.anomaly.service import AnomalyService
from app.anomaly.store import AnomalyStore
from app.correlation.store import IncidentStore
from app.pipeline.store import EvidenceStore
from app.topology.store import TopologyStore
from app.rca.store import RcaStore
from app.impact.store import ImpactStore
from app.explanation.provider import GeminiProvider
from app.explanation.service import ExplanationService
from app.explanation.store import ExplanationStore

logger = logging.getLogger("netrca")


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    manager = NetworkManager(enabled=settings.simulation_enabled)
    fault_controller = FaultController(manager, FaultStore(settings),
                                       enabled=settings.fault_injection_enabled,
                                       timeout=settings.simulation_operation_timeout_seconds)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            try:
                manager.close(timeout=settings.simulation_operation_timeout_seconds)
            except Exception:
                logger.error("Network cleanup failed during application shutdown")

    app = FastAPI(title="NetRCA API", version="0.1.0", lifespan=lifespan)
    app.state.network_manager = manager
    app.state.topology_store = TopologyStore(settings)
    app.state.evidence_store = EvidenceStore(settings)
    app.state.fault_controller = fault_controller
    app.state.anomaly_store = AnomalyStore(settings)
    app.state.anomaly_service = AnomalyService(settings, app.state.anomaly_store)
    app.state.incident_store = IncidentStore(settings)
    app.state.rca_store = RcaStore(settings)
    app.state.impact_store = ImpactStore(settings)
    app.state.explanation_service = ExplanationService(ExplanationStore(settings), GeminiProvider(settings))
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", "X-NetRCA-Local-Control"],
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _error: RequestValidationError):
        return error_response(422, "VALIDATION_ERROR", "Request validation failed")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException):
        code = "NOT_FOUND" if error.status_code == 404 else "HTTP_ERROR"
        message = "Resource not found" if error.status_code == 404 else "Request failed"
        return error_response(error.status_code, code, message)

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _error: Exception):
        logger.error("Unhandled request error")
        return error_response(500, "INTERNAL_ERROR", "An internal error occurred")

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(network_router, prefix="/api/v1")
    app.include_router(monitoring_router, prefix="/api/v1")
    app.include_router(pipeline_router, prefix="/api/v1")
    app.include_router(faults_router, prefix="/api/v1")
    app.include_router(anomalies_router, prefix="/api/v1")
    app.include_router(incidents_router, prefix="/api/v1")
    app.include_router(topology_router, prefix="/api/v1")
    app.include_router(graph_analysis_router, prefix="/api/v1")
    app.include_router(rca_router, prefix="/api/v1")
    app.include_router(impact_router, prefix="/api/v1")
    app.include_router(ai_router, prefix="/api/v1")
    return app


app = create_app()
