from datetime import datetime, timezone

from google.cloud import storage

from app.exceptions import StorageError


class StorageService:
    def __init__(self, bucket_name: str, project_id: str | None = None):
        self._client = storage.Client(project=project_id)
        self._bucket = self._client.bucket(bucket_name)

    def upload_pdf(
        self, file_content: bytes, filename: str, doc_id: str
    ) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        blob_path = f"uploads/{timestamp}_{doc_id}_{filename}"
        try:
            blob = self._bucket.blob(blob_path)
            blob.upload_from_string(
                file_content, content_type="application/pdf"
            )
            return f"gs://{self._bucket.name}/{blob_path}"
        except Exception as exc:
            raise StorageError(f"Failed to upload PDF: {exc}") from exc

    def upload_image(
        self,
        image_data: bytes,
        doc_id: str,
        page_number: int,
        image_index: int,
        mime_type: str,
    ) -> str:
        ext = mime_type.split("/")[-1] if "/" in mime_type else "png"
        blob_path = (
            f"extracted_images/{doc_id}/"
            f"page{page_number}_img{image_index}.{ext}"
        )
        try:
            blob = self._bucket.blob(blob_path)
            blob.upload_from_string(image_data, content_type=mime_type)
            return f"gs://{self._bucket.name}/{blob_path}"
        except Exception as exc:
            raise StorageError(f"Failed to upload image: {exc}") from exc
