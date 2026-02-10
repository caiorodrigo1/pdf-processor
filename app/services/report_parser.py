import re

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
    """Strip leading bullets and truncate at footer/signature lines."""
    text = _BULLET_RE.sub("", text).strip()
    match = _FOOTER_PATTERN.search(text)
    if match:
        text = text[: match.start()].strip()
    return text


class VeterinaryReportParser:
    """Extract structured fields from veterinary report text."""

    PATTERNS = {
        "patient_name": (
            r"(?:Paciente|Nombre|PACIENTE|NOMBRE)\s*[:\-]\s*(.+?)(?:\n|$)"
        ),
        "species": r"(?:Especie|ESPECIE)\s*[:\-]\s*(.+?)(?:\n|$)",
        "breed": r"(?:Raza|RAZA)\s*[:\-]\s*(.+?)(?:\n|$)",
        "sex": r"(?:Sexo|SEXO)\s*[:\-]\s*(.+?)(?:\n|$)",
        "age": r"(?:Edad|EDAD)[^\S\n]*[:\-][^\S\n]*(\S[^\n]*)(?:\n|$)",
        "owner_name": (
            r"(?:Tutor|Propietario|TUTOR|PROPIETARIO)\s*[:\-]\s*(.+?)(?:\n|$)"
        ),
        "veterinarian": (
            r"(?:Derivante|Profesional|Referido\s+por|"
            r"DERIVANTE|PROFESIONAL)\s*[:\-]\s*(.+?)(?:\n|$)"
        ),
        "date": (
            r"(?:Fecha|FECHA)\s*[:\-]?\s*\n?\s*"
            r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})"
        ),
    }

    DIAGNOSIS_HEADERS = [
        r"DIAGNÓSTICO\s+(?:RADIOGRÁFICO|ECOGRÁFICO|ECOCARDIOGRÁFICO)",
        r"Diagn[oó]stico\s+(?:radiogr[aá]fico|ecogr[aá]fico|ecocardiogr[aá]fico)",
        r"CONCLUSION(?:ES)?",
        r"HALLAZGOS",
    ]

    RECOMMENDATION_PATTERNS = [
        r"(?:Se\s+recomienda|Recomendaciones?|Notas?)\s*[:\-]?\s*(.+?)(?:\n\n|\Z)",
        r"(?:Comentarios?)\s*[:\-]?\s*\n([\s\S]*?)(?:\n\n|\Z)",
    ]

    @classmethod
    def parse(cls, text: str) -> dict[str, str | None]:
        result: dict[str, str | None] = {}

        for field, pattern in cls.PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            value = match.group(1).strip() if match else None
            result[field] = value if value else None

        # Normalize sex to standard values
        result["sex"] = _normalize_sex(result.get("sex"))

        # Extract and clean multi-line sections
        diagnosis = cls._extract_section(text, cls.DIAGNOSIS_HEADERS)
        result["diagnosis"] = _clean_text(diagnosis) if diagnosis else None

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
                r"(?:\n\n\n|\n[A-ZÁÉÍÓÚÑ]{2,}|\Z)"
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
