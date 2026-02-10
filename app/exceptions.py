from fastapi import Request
from fastapi.responses import JSONResponse


class PDFProcessorError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class FileValidationError(PDFProcessorError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=422)


class DocumentAIError(PDFProcessorError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=502)


class StorageError(PDFProcessorError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=502)


class FirestoreError(PDFProcessorError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=502)


async def pdf_processor_error_handler(
    request: Request, exc: PDFProcessorError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
