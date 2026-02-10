from io import BytesIO
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.models.pdf import PageInfo


def test_upload_requires_auth(app: TestClient) -> None:
    response = app.post(
        "/pdf/upload",
        files={"file": ("test.pdf", b"fake", "application/pdf")},
    )
    assert response.status_code == 401


def test_upload_rejects_non_pdf(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    response = app.post(
        "/pdf/upload",
        headers=auth_headers,
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 422
    assert "Invalid file type" in response.json()["detail"]


def test_upload_rejects_invalid_pdf_bytes(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    response = app.post(
        "/pdf/upload",
        headers=auth_headers,
        files={
            "file": ("test.pdf", b"not a real pdf", "application/pdf")
        },
    )
    assert response.status_code == 422
    assert "valid PDF" in response.json()["detail"]


def test_upload_success(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    pdf_content = b"%PDF-1.4 fake pdf content for testing"

    mock_doc_ai: MagicMock = app.app.state.document_ai_service
    mock_doc_ai.process_pdf.return_value = (
        "Extracted text from PDF",
        [
            PageInfo(
                page_number=1,
                width=612.0,
                height=792.0,
                text="Extracted text from PDF",
                detected_languages=["en"],
            )
        ],
    )

    with patch(
        "app.routers.pdf.extract_embedded_images", return_value=[]
    ):
        response = app.post(
            "/pdf/upload",
            headers=auth_headers,
            files={
                "file": (
                    "sample.pdf",
                    BytesIO(pdf_content),
                    "application/pdf",
                )
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "sample.pdf"
    assert body["total_pages"] == 1
    assert "full_text" not in body
    assert "pages" not in body
    assert "document_id" in body
    assert "gcs_uri" in body
    assert "processing_time_seconds" in body
    assert "report_info" in body
    assert isinstance(body["report_info"], dict)


def test_upload_with_images(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    pdf_content = b"%PDF-1.4 fake pdf with images"

    mock_doc_ai: MagicMock = app.app.state.document_ai_service
    mock_doc_ai.process_pdf.return_value = (
        "Page text",
        [
            PageInfo(
                page_number=1,
                width=612.0,
                height=792.0,
                text="Page text",
                detected_languages=["en"],
            )
        ],
    )

    fake_image_data = b"\x89PNG fake image bytes"
    fake_raw_images = [
        (fake_image_data, 1, "image/png", 100, 200),
    ]

    mock_storage: MagicMock = app.app.state.storage_service
    mock_storage.upload_image.return_value = (
        "gs://test-bucket/extracted_images/abc/page1_img0.png"
    )

    with patch(
        "app.routers.pdf.extract_embedded_images",
        return_value=fake_raw_images,
    ):
        response = app.post(
            "/pdf/upload",
            headers=auth_headers,
            files={
                "file": (
                    "doc.pdf",
                    BytesIO(pdf_content),
                    "application/pdf",
                )
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["images"]) == 1
    assert body["images"][0]["page_number"] == 1
    assert body["images"][0]["mime_type"] == "image/png"
    assert body["images"][0]["width"] == 100
    assert body["images"][0]["height"] == 200

    mock_storage.upload_image.assert_called_once()


def test_upload_sanitizes_filename(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    pdf_content = b"%PDF-1.4 fake"

    mock_doc_ai: MagicMock = app.app.state.document_ai_service
    mock_doc_ai.process_pdf.return_value = ("text", [])

    with patch(
        "app.routers.pdf.extract_embedded_images", return_value=[]
    ):
        response = app.post(
            "/pdf/upload",
            headers=auth_headers,
            files={
                "file": (
                    "../../etc/evil file.pdf",
                    BytesIO(pdf_content),
                    "application/pdf",
                )
            },
        )
    assert response.status_code == 200
    body = response.json()
    # Path traversal stripped, spaces replaced
    assert "/" not in body["filename"]
    assert "\\" not in body["filename"]
    assert ".." not in body["filename"]


def test_upload_parses_veterinary_fields(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    pdf_content = b"%PDF-1.4 fake pdf"

    vet_text = (
        "Paciente: Luna\nEspecie: Canino\nRaza: Golden Retriever\n"
        "Tutor: María García\nDerivante: Dr. Pérez\n"
    )

    mock_doc_ai: MagicMock = app.app.state.document_ai_service
    mock_doc_ai.process_pdf.return_value = (vet_text, [])

    with patch(
        "app.routers.pdf.extract_embedded_images", return_value=[]
    ):
        response = app.post(
            "/pdf/upload",
            headers=auth_headers,
            files={
                "file": (
                    "report.pdf",
                    BytesIO(pdf_content),
                    "application/pdf",
                )
            },
        )
    assert response.status_code == 200
    info = response.json()["report_info"]
    assert info["patient_name"] == "Luna"
    assert info["species"] == "Canino"
    assert info["breed"] == "Golden Retriever"
    assert info["owner_name"] == "María García"
    assert info["veterinarian"] == "Dr. Pérez"


def test_upload_saves_to_firestore(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    pdf_content = b"%PDF-1.4 fake pdf"

    mock_doc_ai: MagicMock = app.app.state.document_ai_service
    mock_doc_ai.process_pdf.return_value = ("text", [])

    mock_firestore: MagicMock = app.app.state.firestore_service

    with patch(
        "app.routers.pdf.extract_embedded_images", return_value=[]
    ):
        response = app.post(
            "/pdf/upload",
            headers=auth_headers,
            files={
                "file": (
                    "test.pdf",
                    BytesIO(pdf_content),
                    "application/pdf",
                )
            },
        )
    assert response.status_code == 200
    mock_firestore.save_record.assert_called_once()
    call_args = mock_firestore.save_record.call_args
    saved_data = call_args[0][1]
    assert saved_data["filename"] == "test.pdf"
    assert "uploaded_by" in saved_data
    assert "created_at" in saved_data
    assert "report_info" in saved_data


def test_get_pdf_record_success(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    mock_firestore: MagicMock = app.app.state.firestore_service
    mock_firestore.get_record.return_value = {
        "document_id": "abc123",
        "filename": "test.pdf",
        "gcs_uri": "gs://bucket/uploads/test.pdf",
        "total_pages": 1,
        "full_text": "Sample text",
        "pages": [
            {
                "page_number": 1,
                "width": 612.0,
                "height": 792.0,
                "text": "Sample text",
                "detected_languages": ["es"],
            }
        ],
        "images": [],
        "report_info": {
            "patient_name": "Luna",
            "species": "Canino",
            "breed": None,
            "sex": None,
            "age": None,
            "owner_name": None,
            "veterinarian": None,
            "date": None,
            "diagnosis": None,
            "recommendations": None,
        },
        "processing_time_seconds": 1.5,
        "created_at": "2025-01-15T10:00:00+00:00",
        "uploaded_by": "admin",
    }

    response = app.get("/pdf/abc123", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == "abc123"
    assert body["filename"] == "test.pdf"
    assert body["report_info"]["patient_name"] == "Luna"
    assert body["uploaded_by"] == "admin"


def test_get_pdf_record_not_found(
    app: TestClient, auth_headers: dict[str, str]
) -> None:
    mock_firestore: MagicMock = app.app.state.firestore_service
    mock_firestore.get_record.return_value = None

    response = app.get("/pdf/nonexistent", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_pdf_record_requires_auth(app: TestClient) -> None:
    response = app.get("/pdf/abc123")
    assert response.status_code == 401
