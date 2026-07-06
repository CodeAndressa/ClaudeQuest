from fastapi.testclient import TestClient


def test_health_returns_service_identity(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["app"] == "ClaudeQuest"
    assert body["data"]["status"] == "ok"
    assert "request_id" in body["metadata"]
    assert body["metadata"]["execution_time_ms"] >= 0


def test_live_reports_process_running(client: TestClient) -> None:
    response = client.get("/api/v1/live")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_ready_reports_ok_when_database_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_ready_returns_503_when_database_unreachable(
    client_with_db_down: TestClient,
) -> None:
    response = client_with_db_down.get("/api/v1/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "database_unavailable"
    assert "trace_id" in body
    assert "timestamp" in body


def test_response_carries_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-trace-123"})

    assert response.headers["X-Request-ID"] == "test-trace-123"
    assert response.json()["metadata"]["request_id"] == "test-trace-123"
