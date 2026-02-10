from pydantic import BaseModel


class ImageInfo(BaseModel):
    page_number: int
    gcs_uri: str
    width: int
    height: int
    mime_type: str


class PageInfo(BaseModel):
    page_number: int
    width: float
    height: float
    text: str
    detected_languages: list[str]


class ReportInfo(BaseModel):
    """Structured fields parsed from veterinary report text."""

    patient_name: str | None = None
    species: str | None = None
    breed: str | None = None
    sex: str | None = None
    age: str | None = None
    owner_name: str | None = None
    veterinarian: str | None = None
    date: str | None = None
    diagnosis: str | None = None
    recommendations: str | None = None


class PDFUploadResponse(BaseModel):
    document_id: str
    filename: str
    gcs_uri: str
    total_pages: int
    images: list[ImageInfo]
    report_info: ReportInfo
    processing_time_seconds: float


class PDFRecord(BaseModel):
    """Full stored record returned by GET endpoint."""

    document_id: str
    filename: str
    gcs_uri: str
    total_pages: int
    images: list[ImageInfo]
    report_info: ReportInfo
    processing_time_seconds: float
    created_at: str
    uploaded_by: str
