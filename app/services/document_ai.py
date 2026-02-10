import fitz
from google.cloud import documentai_v1 as documentai

from app.exceptions import DocumentAIError
from app.models.pdf import ImageInfo, PageInfo

MAX_PAGES_PER_REQUEST = 15


class DocumentAIService:
    def __init__(self, project_id: str, location: str, processor_id: str):
        self._client = documentai.DocumentProcessorServiceClient()
        self._processor_name = self._client.processor_path(
            project_id, location, processor_id
        )

    def process_pdf(
        self, file_content: bytes
    ) -> tuple[str, list[PageInfo]]:
        """Process a PDF with Document AI for text extraction.

        Automatically splits PDFs with more than 15 pages into chunks
        and merges results.

        Returns:
            Tuple of (full_text, pages).
        """
        doc = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(doc)

        if total_pages <= MAX_PAGES_PER_REQUEST:
            doc.close()
            return self._process_chunk(file_content, page_offset=0)

        # Split into chunks of MAX_PAGES_PER_REQUEST pages
        all_text_parts: list[str] = []
        all_pages: list[PageInfo] = []

        for start in range(0, total_pages, MAX_PAGES_PER_REQUEST):
            end = min(start + MAX_PAGES_PER_REQUEST, total_pages)
            chunk_doc = fitz.open()
            chunk_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
            chunk_bytes = chunk_doc.tobytes()
            chunk_doc.close()

            chunk_text, chunk_pages = self._process_chunk(
                chunk_bytes, page_offset=start
            )
            all_text_parts.append(chunk_text)
            all_pages.extend(chunk_pages)

        doc.close()
        return "\n".join(all_text_parts), all_pages

    def _process_chunk(
        self, file_content: bytes, page_offset: int = 0
    ) -> tuple[str, list[PageInfo]]:
        """Process a single chunk through Document AI."""
        raw_document = documentai.RawDocument(
            content=file_content, mime_type="application/pdf"
        )
        request = documentai.ProcessRequest(
            name=self._processor_name, raw_document=raw_document
        )
        try:
            result = self._client.process_document(request=request)
        except Exception as exc:
            raise DocumentAIError(f"Document AI processing failed: {exc}") from exc

        document = result.document
        full_text = document.text

        pages: list[PageInfo] = []
        for i, page in enumerate(document.pages, start=1):
            page_text = self._extract_page_text(document.text, page)
            detected_langs = [
                lang.language_code
                for lang in page.detected_languages
                if lang.language_code
            ]
            width = page.dimension.width if page.dimension else 0.0
            height = page.dimension.height if page.dimension else 0.0

            pages.append(
                PageInfo(
                    page_number=page_offset + i,
                    width=width,
                    height=height,
                    text=page_text,
                    detected_languages=detected_langs,
                )
            )

        return full_text, pages

    @staticmethod
    def _extract_page_text(full_text: str, page: documentai.Document.Page) -> str:
        segments: list[str] = []
        if not page.layout or not page.layout.text_anchor:
            return ""
        for segment in page.layout.text_anchor.text_segments:
            start = int(segment.start_index) if segment.start_index else 0
            end = int(segment.end_index) if segment.end_index else 0
            segments.append(full_text[start:end])
        return "".join(segments)


def extract_embedded_images(
    file_content: bytes,
    min_width: int = 0,
    min_height: int = 0,
    min_file_size_kb: int = 0,
) -> list[tuple[bytes, int, str, int, int]]:
    """Extract unique medical images from PDF using PyMuPDF.

    Filters out decorative images (logos, icons, backgrounds) by:
    1. Deduplicating by xref — same image object on many pages = decorative.
    2. Applying minimum dimension filters.
    3. Applying minimum file size filter (logos are tiny files).

    Args:
        file_content: Raw PDF bytes.
        min_width: Minimum image width to include.
        min_height: Minimum image height to include.
        min_file_size_kb: Minimum image file size in KB.

    Returns:
        List of (image_bytes, page_number, mime_type, width, height).
    """
    doc = fitz.open(stream=file_content, filetype="pdf")
    total_pages = len(doc)

    # First pass: count how many pages each xref appears on
    xref_page_count: dict[int, int] = {}
    for page_num in range(total_pages):
        page = doc[page_num]
        seen_on_page: set[int] = set()
        for img in page.get_images(full=True):
            xref = img[0]
            if xref not in seen_on_page:
                seen_on_page.add(xref)
                xref_page_count[xref] = xref_page_count.get(xref, 0) + 1

    # Threshold: if an image appears on >30% of pages, it's decorative
    repeat_threshold = max(2, int(total_pages * 0.3))

    # Second pass: extract only unique, non-decorative images
    raw_images: list[tuple[bytes, int, str, int, int]] = []
    seen_xrefs: set[int] = set()

    for page_num in range(total_pages):
        page = doc[page_num]
        for img in page.get_images(full=True):
            xref = img[0]

            # Skip decorative images (repeated across many pages)
            if xref_page_count.get(xref, 0) >= repeat_threshold:
                continue

            # Skip already-extracted xrefs (same image on 2 pages)
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            base_image = doc.extract_image(xref)
            if not base_image or not base_image.get("image"):
                continue

            image_data = base_image["image"]
            w = base_image.get("width", 0)
            h = base_image.get("height", 0)
            if w < min_width or h < min_height:
                continue
            if len(image_data) < min_file_size_kb * 1024:
                continue

            ext = base_image.get("ext", "png")
            mime_type = f"image/{ext}" if ext != "jpeg" else "image/jpeg"
            raw_images.append((
                image_data,
                page_num + 1,
                mime_type,
                w,
                h,
            ))

    doc.close()
    return raw_images


def build_image_infos(
    raw_images: list[tuple[bytes, int, str, int, int]],
    gcs_uris: list[str],
) -> list[ImageInfo]:
    return [
        ImageInfo(
            page_number=img[1],
            gcs_uri=uri,
            width=img[3],
            height=img[4],
            mime_type=img[2],
        )
        for img, uri in zip(raw_images, gcs_uris)
    ]
