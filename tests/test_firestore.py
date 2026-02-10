from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import FirestoreError
from app.services.firestore import FirestoreService


@pytest.fixture()
def mock_client() -> MagicMock:
    with patch("app.services.firestore.firestore.Client") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


@pytest.fixture()
def service(mock_client: MagicMock) -> FirestoreService:
    return FirestoreService(project_id="test-project")


def test_save_record(service: FirestoreService, mock_client: MagicMock) -> None:
    data = {"document_id": "abc123", "filename": "test.pdf"}
    service.save_record("abc123", data)

    collection = mock_client.collection.return_value
    collection.document.assert_called_once_with("abc123")
    collection.document.return_value.set.assert_called_once_with(data)


def test_get_record_found(
    service: FirestoreService, mock_client: MagicMock
) -> None:
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"document_id": "abc123", "filename": "test.pdf"}

    collection = mock_client.collection.return_value
    collection.document.return_value.get.return_value = mock_doc

    result = service.get_record("abc123")
    assert result == {"document_id": "abc123", "filename": "test.pdf"}


def test_get_record_not_found(
    service: FirestoreService, mock_client: MagicMock
) -> None:
    mock_doc = MagicMock()
    mock_doc.exists = False

    collection = mock_client.collection.return_value
    collection.document.return_value.get.return_value = mock_doc

    result = service.get_record("nonexistent")
    assert result is None


def test_save_record_raises_firestore_error(
    service: FirestoreService, mock_client: MagicMock
) -> None:
    collection = mock_client.collection.return_value
    collection.document.return_value.set.side_effect = RuntimeError("connection lost")

    with pytest.raises(FirestoreError, match="Failed to save record"):
        service.save_record("abc123", {"data": "test"})


def test_get_record_raises_firestore_error(
    service: FirestoreService, mock_client: MagicMock
) -> None:
    collection = mock_client.collection.return_value
    collection.document.return_value.get.side_effect = RuntimeError("timeout")

    with pytest.raises(FirestoreError, match="Failed to get record"):
        service.get_record("abc123")
