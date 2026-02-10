import re
import unicodedata

# Patterns that indicate footer/signature content (cut recommendations here)
_FOOTER_PATTERN = re.compile(
    r"\n\s*(?:M\.?V\.?\s|M\.?P\.?\s|Mat\.\s*\d|DiagnoVet|\d{3}[\-\s]?\d{7})",
    re.IGNORECASE,
)

# Leading bullet characters to strip
_BULLET_RE = re.compile(r"^[\s•●\-\*]+")

# Sex normalization map
_SEX_MAP = {
    "hembra": "Hembra",
    "macho": "Macho",
    "h": "Hembra",
    "m": "Macho",
    "hembra castrada": "Hembra castrada",
    "hembra-castrada": "Hembra castrada",
    "hembra - castrada": "Hembra castrada",
    "macho castrado": "Macho castrado",
    "macho-castrado": "Macho castrado",
    "macho - castrado": "Macho castrado",
}


def _normalize_sex(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    return _SEX_MAP.get(key, raw.strip())


def _clean_text(text: str) -> str:
    """Strip leading bullets, truncate at footer, collapse to single line."""
    text = _BULLET_RE.sub("", text).strip()
    match = _FOOTER_PATTERN.search(text)
    if match:
        text = text[: match.start()].strip()
    # Replace newlines with spaces and collapse multiple spaces
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def _clean_diagnosis(text: str) -> str:
    """Clean diagnosis: strip bullets, collapse to single line, trim footer."""
    match = _FOOTER_PATTERN.search(text)
    if match:
        text = text[: match.start()]
    # Remove bullet characters
    text = re.sub(r"[•●]", "", text)
    # Replace newlines (and surrounding whitespace) with a single space
    text = re.sub(r"\s*\n\s*", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)
    return text.strip()


def _normalize_date(raw: str | None) -> str | None:
    """Normalize date to DD/MM/YYYY format."""
    if not raw:
        return None
    # Try YYYY/MM/DD or YYYY-MM-DD or YYYY.MM.DD
    m = re.match(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$", raw)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    # Already DD/MM/YYYY or similar — return as-is
    return raw


class VeterinaryReportParser:
    """Extract structured fields from veterinary report text."""

    # Known field labels used to detect column boundaries on same line
    _FIELD_LABELS = (
        r"Paciente|Nombre|Especie|Raza|Sexo|Edad|"
        r"Tutor|Propietario|Derivante|Profesional|"
        r"Fecha|Referido"
    )

    # End-of-value: next field label on same line (horizontal whitespace),
    # or newline, or end of string.
    _VALUE_END = (
        rf"(?=[^\S\n]+(?:{_FIELD_LABELS})\s*[:\-]|\n|$)"
    )

    PATTERNS = {
        "patient_name": (
            rf"(?:Paciente|Nombre|PACIENTE|NOMBRE)\s*[:\-]\s*(.+?){_VALUE_END}"
        ),
        "species": rf"(?:Especie|ESPECIE)\s*[:\-]\s*(.+?){_VALUE_END}",
        "breed": rf"(?:Raza|RAZA)\s*[:\-]\s*(.+?){_VALUE_END}",
        "sex": rf"(?:Sexo|SEXO)\s*[:\-]\s*(.+?){_VALUE_END}",
        "age": rf"(?:Edad|EDAD)[^\S\n]*[:\-][^\S\n]*(\S[^\n]*?){_VALUE_END}",
        "owner_name": (
            rf"(?:Tutor|Propietario|TUTOR|PROPIETARIO)\s*[:\-]\s*(.+?){_VALUE_END}"
        ),
        "veterinarian": (
            rf"(?:Derivante|Profesional|Referido\s+por|"
            rf"DERIVANTE|PROFESIONAL)\s*[:\-]\s*(.+?){_VALUE_END}"
        ),
        "date": (
            r"(?:Fecha|FECHA)\s*[:\-]?\s*\n?\s*"
            r"(\d{1,4}[/\-.]\d{1,2}[/\-.]\d{2,4})"
        ),
    }

    DIAGNOSIS_HEADERS = [
        r"DIAGNÓSTICO\s+(?:RADIOGRÁFICO|ECOGRÁFICO|ECOCARDIOGRÁFICO)",
        r"Diagn[oó]stico\s+(?:radiogr[aá]fico|ecogr[aá]fico|ecocardiogr[aá]fico)",
        r"CONCLUSION(?:ES)?",
        r"HALLAZGOS",
    ]

    RECOMMENDATION_PATTERNS = [
        # Notas: as section header (content on next line) — must be before Se recomienda
        r"(?:Notas?)\s*[:\-]\s*\n([\s\S]*?)(?:\n\n\n|\n\n(?=[A-ZÁÉÍÓÚÑM])|\Z)",
        # Notas: with content on same line
        r"(?:Notas?)\s*[:\-]?\s*(.+?)(?:\n\n|\Z)",
        # Se recomienda (standalone) — include the phrase itself in the capture
        r"(Se\s+recomienda\b[\s\S]*?)(?:\n\n|\Z)",
        # Recomendaciones header — capture content after the label
        r"(?:Recomendaciones?)\s*[:\-]\s*([\s\S]*?)(?:\n\n|\Z)",
        r"(?:Comentarios?)\s*[:\-]?\s*\n([\s\S]*?)(?:\n\n|\Z)",
    ]

    @classmethod
    def parse(cls, text: str) -> dict[str, str | None]:
        # Normalize Unicode so decomposed accents (from Document AI OCR)
        # match precomposed characters in our regex patterns.
        text = unicodedata.normalize("NFC", text)

        result: dict[str, str | None] = {}

        for field, pattern in cls.PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            value = match.group(1).strip() if match else None
            result[field] = value if value else None

        # Normalize sex to standard values
        result["sex"] = _normalize_sex(result.get("sex"))

        # Normalize date to DD/MM/YYYY
        result["date"] = _normalize_date(result.get("date"))

        # Extract and clean multi-line sections
        diagnosis = cls._extract_section(text, cls.DIAGNOSIS_HEADERS)
        result["diagnosis"] = _clean_diagnosis(diagnosis) if diagnosis else None

        recommendations = cls._extract_recommendations(text)
        result["recommendations"] = (
            _clean_text(recommendations) if recommendations else None
        )

        return result

    @classmethod
    def _extract_section(cls, text: str, headers: list[str]) -> str | None:
        for header in headers:
            pattern = (
                rf"(?:{header})\s*[:\-]?\s*\n"
                r"([\s\S]*?)"
                # (?-i:...) disables IGNORECASE so only UPPERCASE lines terminate
                r"(?:\n\n\n|\n(?-i:[A-ZÁÉÍÓÚÑ]{2,})"
                r"|\nNotas?\s*[:\-]"
                r"|\nSe\s+recomienda"
                r"|\nRecomendaciones?\s*[:\-]"
                r"|\nComentarios?\s*[:\-]"
                r"|\Z)"
            )
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                section = match.group(1).strip()
                if len(section) > 10:
                    return section
        return None

    @classmethod
    def _extract_recommendations(cls, text: str) -> str | None:
        for pattern in cls.RECOMMENDATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                rec = match.group(1).strip()
                if len(rec) > 5:
                    return rec
        return None
