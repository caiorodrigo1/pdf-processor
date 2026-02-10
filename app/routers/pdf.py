import re
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, UploadFile

from app.config import Settings
from app.dependencies import get_current_user, get_settings, limiter
from app.exceptions import FileValidationError, PDFProcessorError
from app.models.pdf import PDFRecord, PDFUploadResponse, ReportInfo
from app.services.document_ai import (
    DocumentAIService,
    build_image_infos,
    extract_embedded_images,
)
from app.services.report_parser import VeterinaryReportParser
from app.services.storage import StorageService

router = APIRouter(prefix="/pdf", tags=["pdf"])

PDF_MAGIC_BYTES = b"%PDF-"
ALLOWED_MIME_TYPES = {"application/pdf"}
MAX_FILENAME_LENGTH = 200
SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _sanitize_filename(filename: str) -> str:
    # Strip path components (e.g. ../../evil.pdf -> evil.pdf)
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    # Replace unsafe characters with underscores
    name = SAFE_FILENAME_RE.sub("_", name)
    # Truncate to safe length
    name = name[:MAX_FILENAME_LENGTH] if name else "upload.pdf"
    return name or "upload.pdf"


def _validate_pdf(content: bytes, max_size_mb: int) -> None:
    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileValidationError(
            f"File exceeds maximum size of {max_size_mb}MB"
        )
    if not content.startswith(PDF_MAGIC_BYTES):
        raise FileValidationError("File does not appear to be a valid PDF")


@router.post("/upload", response_model=PDFUploadResponse)
@limiter.limit("10/minute")
def upload_pdf(
    request: Request,
    file: UploadFile,
    current_user: Annotated[str, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PDFUploadResponse:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise FileValidationError(
            f"Invalid file type: {file.content_type}. Only PDF files are accepted."
        )

    # Check Content-Length before reading to reject oversized uploads early
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        raise FileValidationError(
            f"File exceeds maximum size of {settings.max_file_size_mb}MB"
        )

    content = file.file.read()
    _validate_pdf(content, settings.max_file_size_mb)

    safe_filename = _sanitize_filename(file.filename or "upload.pdf")
    start = time.monotonic()
    doc_id = uuid.uuid4().hex[:12]

    storage: StorageService | None = request.app.state.storage_service
    doc_ai: DocumentAIService | None = request.app.state.document_ai_service

    if storage is None or doc_ai is None:
        raise PDFProcessorError(
            "GCP services are unavailable. Check credentials and configuration.",
            status_code=503,
        )

    gcs_uri = storage.upload_pdf(content, safe_filename, doc_id)

    # Document AI: text extraction
    full_text, pages = doc_ai.process_pdf(content)

    # PyMuPDF: extract actual embedded images (not full page renders)
    raw_images = extract_embedded_images(
        content,
        min_width=settings.min_image_width,
        min_height=settings.min_image_height,
        min_file_size_kb=settings.min_image_file_size_kb,
    )

    image_gcs_uris: list[str] = []
    for i, (img_bytes, page_num, mime_type, _w, _h) in enumerate(raw_images):
        uri = storage.upload_image(img_bytes, doc_id, page_num, i, mime_type)
        image_gcs_uris.append(uri)

    images = build_image_infos(raw_images, image_gcs_uris)
    elapsed = time.monotonic() - start

    # Parse structured report fields from extracted text
    report_data = VeterinaryReportParser.parse(full_text)
    report_info = ReportInfo(**report_data)

    # Save to Firestore if available
    firestore_svc = getattr(request.app.state, "firestore_service", None)
    if firestore_svc is not None:
        record = {
            "document_id": doc_id,
            "filename": safe_filename,
            "gcs_uri": gcs_uri,
            "total_pages": len(pages),
            "full_text": full_text,
            "pages": [p.model_dump() for p in pages],
            "images": [img.model_dump() for img in images],
            "report_info": report_info.model_dump(),
            "processing_time_seconds": round(elapsed, 3),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "uploaded_by": current_user,
        }
        firestore_svc.save_record(doc_id, record)

    return PDFUploadResponse(
        document_id=doc_id,
        filename=safe_filename,
        gcs_uri=gcs_uri,
        total_pages=len(pages),
        images=images,
        report_info=report_info,
        processing_time_seconds=round(elapsed, 3),
    )


@router.get("/{document_id}", response_model=PDFRecord)
def get_pdf_record(
    request: Request,
    document_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
) -> PDFRecord:
    firestore_svc = getattr(request.app.state, "firestore_service", None)
    if firestore_svc is None:
        raise PDFProcessorError("Firestore unavailable", status_code=503)

    record = firestore_svc.get_record(document_id)
    if record is None:
        raise PDFProcessorError("Document not found", status_code=404)

    return PDFRecord(**record)
