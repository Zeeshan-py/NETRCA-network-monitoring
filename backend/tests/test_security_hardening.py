"""Phase 14 checks for the local-only API boundary and request resource limits."""
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_forwarded_headers_cannot_claim_a_loopback_client():
    app = create_app(Settings(_env_file=None, simulation_enabled=False,
                              pipeline_writes_enabled=True))
    protected = "/api/v1/network/status"
    spoofed_headers = (
        {"X-Forwarded-For": "127.0.0.1"},
        {"Forwarded": "for=127.0.0.1;proto=http;host=localhost"},
        {"X-Real-IP": "127.0.0.1"},
        {"X-Forwarded-Host": "localhost"},
        {"X-Forwarded-Proto": "http"},
    )
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        for headers in spoofed_headers:
            response = client.get(protected, headers=headers)
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "UNTRUSTED_PROXY_HEADERS"
        remote = TestClient(app, client=("203.0.113.5", 50000))
        for headers in spoofed_headers:
            response = remote.get(protected, headers=headers)
            assert response.status_code == 403


def test_invalid_origin_and_control_header_are_rejected():
    app = create_app(Settings(_env_file=None, cors_origins="http://localhost:3000",
                              simulation_enabled=False))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        denied_origin = client.get("/api/v1/network/status", headers={"Origin": "https://evil.example"})
        assert denied_origin.status_code == 403
        path = "/api/v1/network/start"
        for value in (None, "", "0", "1, 1", "true"):
            headers = {} if value is None else {"X-NetRCA-Local-Control": value}
            response = client.post(path, headers=headers)
            assert response.status_code == 403
            assert response.json()["error"]["code"] in {
                "LOCAL_CONTROL_REQUIRED", "MININET_UNAVAILABLE"}


def test_oversized_json_body_rejected_before_route_validation():
    app = create_app(Settings(_env_file=None, max_request_body_bytes=65536,
                              cors_origins="http://localhost:3000",
                              pipeline_writes_enabled=True))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.post("/api/v1/events", content=b"x" * 65537,
                               headers={"Content-Type": "application/json",
                                        "X-NetRCA-Local-Control": "1",
                                        "Origin": "http://localhost:3000"})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_api_security_and_cache_headers_are_present():
    app = create_app(Settings(_env_file=None))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
