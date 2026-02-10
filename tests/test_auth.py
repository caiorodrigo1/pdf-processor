from fastapi.testclient import TestClient


def test_login_success(app: TestClient) -> None:
    response = app.post(
        "/auth/token",
        data={"username": "admin", "password": "changeme123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(app: TestClient) -> None:
    response = app.post(
        "/auth/token",
        data={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_unknown_user(app: TestClient) -> None:
    response = app.post(
        "/auth/token",
        data={"username": "nobody", "password": "whatever"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
