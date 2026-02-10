import re


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
        "date": r"(?:Fecha|FECHA)\s*[:\-]?\s*\n?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
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
            # Discard empty or garbage captures
            result[field] = value if value else None

        result["diagnosis"] = cls._extract_section(text, cls.DIAGNOSIS_HEADERS)
        result["recommendations"] = cls._extract_recommendations(text)

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
