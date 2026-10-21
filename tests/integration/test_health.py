from fastapi.testclient import TestClient

from ai_agent.api.app import create_app
from ai_agent.core.config import Settings


def test_health_returns_json_and_correlation_id():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health", headers={"X-Request-ID": "test-123"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-123"
