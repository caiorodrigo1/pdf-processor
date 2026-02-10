from google.cloud import firestore

from app.exceptions import FirestoreError

PDF_COLLECTION = "pdf_records"
USERS_COLLECTION = "users"


class FirestoreService:
    def __init__(self, project_id: str, database: str = "(default)"):
        self._client = firestore.Client(project=project_id, database=database)
        self._collection = self._client.collection(PDF_COLLECTION)

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

    # --- User methods ---

    def save_user(self, username: str, data: dict) -> None:
        try:
            self._client.collection(USERS_COLLECTION).document(username).set(data)
        except Exception as exc:
            raise FirestoreError(f"Failed to save user: {exc}") from exc

    def get_user(self, username: str) -> dict | None:
        try:
            doc = (
                self._client.collection(USERS_COLLECTION).document(username).get()
            )
            return doc.to_dict() if doc.exists else None
        except Exception as exc:
            raise FirestoreError(f"Failed to get user: {exc}") from exc

    def get_user_by_email(self, email: str) -> dict | None:
        try:
            docs = (
                self._client.collection(USERS_COLLECTION)
                .where("email", "==", email)
                .limit(1)
                .stream()
            )
            for doc in docs:
                return doc.to_dict()
            return None
        except Exception as exc:
            raise FirestoreError(f"Failed to get user by email: {exc}") from exc

    def get_user_by_verification_token(self, token: str) -> dict | None:
        try:
            docs = (
                self._client.collection(USERS_COLLECTION)
                .where("verification_token", "==", token)
                .limit(1)
                .stream()
            )
            for doc in docs:
                data = doc.to_dict()
                data["_doc_id"] = doc.id
                return data
            return None
        except Exception as exc:
            raise FirestoreError(
                f"Failed to get user by token: {exc}"
            ) from exc

    def update_user(self, username: str, data: dict) -> None:
        try:
            self._client.collection(USERS_COLLECTION).document(username).update(data)
        except Exception as exc:
            raise FirestoreError(f"Failed to update user: {exc}") from exc
