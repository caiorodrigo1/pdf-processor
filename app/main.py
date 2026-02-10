import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import Settings
from app.dependencies import limiter
from app.exceptions import PDFProcessorError, pdf_processor_error_handler
from app.routers import auth, health, pdf
from app.services.document_ai import DocumentAIService
from app.services.firestore import FirestoreService
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        # Only create real GCP services if not already set (tests inject mocks)
        if not hasattr(app.state, "storage_service"):
            try:
                app.state.storage_service = StorageService(
                    settings.gcs_bucket_name,
                    project_id=settings.gcp_project_id,
                )
            except Exception as exc:
                logger.warning("Cloud Storage unavailable: %s", exc)
                app.state.storage_service = None
        if not hasattr(app.state, "document_ai_service"):
            try:
                app.state.document_ai_service = DocumentAIService(
                    project_id=settings.gcp_project_id,
                    location=settings.gcp_location,
                    processor_id=settings.gcp_processor_id,
                )
            except Exception as exc:
                logger.warning("Document AI unavailable: %s", exc)
                app.state.document_ai_service = None
        if not hasattr(app.state, "firestore_service"):
            try:
                app.state.firestore_service = FirestoreService(
                    project_id=settings.gcp_project_id,
                    database=settings.firestore_database,
                )
            except Exception as exc:
                logger.warning("Firestore unavailable: %s", exc)
                app.state.firestore_service = None
        yield

    application = FastAPI(
        title="PDF Processor API",
        description="Upload and process PDF files with Google Cloud Document AI",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    application.state.settings = settings
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_exception_handler(PDFProcessorError, pdf_processor_error_handler)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(pdf.router)

    return application


def _create_default_app() -> FastAPI:
    """Create app with settings from environment. Used by uvicorn."""
    try:
        return create_app()
    except Exception:
        # During testing or when env vars aren't set, return a placeholder.
        # Tests use create_app(settings=...) directly.
        return FastAPI()


app = _create_default_app()
