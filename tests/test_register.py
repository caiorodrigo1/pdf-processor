from fastapi.testclient import TestClient

from tests.conftest import ADMIN_USER


def test_register_success(app: TestClient) -> None:
    response = app.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newuser"
    assert body["email"] == "newuser@example.com"
    assert "verify" in body["message"].lower() or "check" in body["message"].lower()

    # Verify Firestore save was called
    fs = app.app.state.firestore_service
    fs.save_user.assert_called_once()
    call_args = fs.save_user.call_args
    assert call_args[0][0] == "newuser"
    saved = call_args[0][1]
    assert saved["username"] == "newuser"
    assert saved["email"] == "newuser@example.com"
    assert saved["is_verified"] is False
    assert "verification_token" in saved

    # Verify email was sent
    email_svc = app.app.state.email_service
    email_svc.send_verification_email.assert_called_once()


def test_register_duplicate_username(app: TestClient) -> None:
    # "admin" already exists via mock
    response = app.post(
        "/auth/register",
        json={
            "username": "admin",
            "email": "other@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 409
    assert "username" in response.json()["detail"].lower()


def test_register_duplicate_email(app: TestClient) -> None:
    fs = app.app.state.firestore_service
    fs.get_user_by_email.return_value = ADMIN_USER

    response = app.post(
        "/auth/register",
        json={
            "username": "another",
            "email": "taken@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 409
    assert "email" in response.json()["detail"].lower()

    # Reset for other tests
    fs.get_user_by_email.return_value = None


def test_verify_success(app: TestClient) -> None:
    fs = app.app.state.firestore_service
    fs.get_user_by_verification_token.return_value = {
        "username": "newuser",
        "email": "newuser@example.com",
        "hashed_password": "hashed",
        "is_verified": False,
        "verification_token": "test-token-123",
    }

    response = app.get("/auth/verify?token=test-token-123")
    assert response.status_code == 200
    assert "verified" in response.json()["message"].lower()

    fs.update_user.assert_called_with(
        "newuser",
        {"is_verified": True, "verification_token": ""},
    )


def test_verify_invalid_token(app: TestClient) -> None:
    response = app.get("/auth/verify?token=bad-token")
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_login_unverified_user(app: TestClient) -> None:
    from app.services.auth import hash_password

    fs = app.app.state.firestore_service
    unverified_user = {
        "username": "unverified",
        "email": "unverified@example.com",
        "hashed_password": hash_password("mypassword"),
        "is_verified": False,
    }
    original_side_effect = fs.get_user.side_effect
    fs.get_user.side_effect = (
        lambda u: unverified_user if u == "unverified" else original_side_effect(u)
    )

    response = app.post(
        "/auth/token",
        data={"username": "unverified", "password": "mypassword"},
    )
    assert response.status_code == 403
    assert "not verified" in response.json()["detail"].lower()

    # Restore
    fs.get_user.side_effect = original_side_effect


def test_login_verified_user(app: TestClient) -> None:
    # Admin is verified by default in the mock
    response = app.post(
        "/auth/token",
        data={"username": "admin", "password": "changeme123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
