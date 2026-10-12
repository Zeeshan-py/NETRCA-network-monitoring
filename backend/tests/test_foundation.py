import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_health_reports_only_api_state():
    client = TestClient(create_app(Settings(cors_origins="http://localhost:3000")))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"api": "UP"}}


def test_unknown_route_uses_sanitized_error_envelope():
    client = TestClient(create_app(Settings(cors_origins="")))
    response = client.get("/api/v1/missing?token=secret-value")
    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {"code": "NOT_FOUND", "message": "Resource not found"},
    }
    assert "secret-value" not in response.text


def test_configuration_rejects_invalid_origin():
    with pytest.raises(ValidationError):
        Settings(cors_origins="file:///private/path")


def test_cors_allows_only_configured_origin():
    client = TestClient(create_app(Settings(cors_origins="http://localhost:3000")))
    allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    denied = client.get("/api/v1/health", headers={"Origin": "http://example.com"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers
