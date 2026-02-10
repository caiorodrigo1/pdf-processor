from google.cloud import firestore

from app.exceptions import FirestoreError

COLLECTION = "pdf_records"


class FirestoreService:
    def __init__(self, project_id: str, database: str = "(default)"):
        self._client = firestore.Client(project=project_id, database=database)
        self._collection = self._client.collection(COLLECTION)

    def save_record(self, doc_id: str, data: dict) -> None:
        """Save a processed PDF record."""
        try:
            self._collection.document(doc_id).set(data)
        except Exception as exc:
            raise FirestoreError(f"Failed to save record: {exc}") from exc

    def get_record(self, doc_id: str) -> dict | None:
        """Get a record by document_id. Returns None if not found."""
        try:
            doc = self._collection.document(doc_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as exc:
            raise FirestoreError(f"Failed to get record: {exc}") from exc
