from fastapi.testclient import TestClient


def test_health_check(app: TestClient) -> None:
    response = app.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
