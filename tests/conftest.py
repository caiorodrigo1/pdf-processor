from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def test_settings() -> Settings:
    return Settings(
        jwt_secret_key="test-secret-key-for-testing-only",
        gcp_project_id="test-project",
        gcp_processor_id="test-processor",
        gcs_bucket_name="test-bucket",
        debug=True,
    )


@pytest.fixture()
def app(test_settings: Settings) -> TestClient:
    application = create_app(settings=test_settings)

    # Replace GCP services with mocks to avoid real API calls
    mock_storage = MagicMock()
    mock_storage.upload_pdf.return_value = "gs://test-bucket/uploads/test.pdf"
    mock_storage.upload_image.return_value = (
        "gs://test-bucket/extracted_images/abc123/page1_img0.png"
    )

    mock_doc_ai = MagicMock()

    mock_firestore = MagicMock()
    mock_firestore.save_record.return_value = None
    mock_firestore.get_record.return_value = None

    application.state.storage_service = mock_storage
    application.state.document_ai_service = mock_doc_ai
    application.state.firestore_service = mock_firestore

    return TestClient(application)


@pytest.fixture()
def auth_headers(app: TestClient) -> dict[str, str]:
    response = app.post(
        "/auth/token",
        data={"username": "admin", "password": "changeme123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
