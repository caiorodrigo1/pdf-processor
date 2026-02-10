from app.services.report_parser import VeterinaryReportParser

SAMPLE_REPORT = """\
Paciente: Luna
Especie: Canino
Raza: Golden Retriever
Sexo: Hembra
Edad: 5 años
Tutor: María García
Derivante: Dr. Juan Pérez M.V.
Fecha: 15/01/2025

DIAGNÓSTICO RADIOGRÁFICO:
Se observa cardiomegalia con un índice VHS de 11.5v.
Patrón alveolar leve en lóbulos caudales.
No se observan signos de efusión pleural.

Se recomienda ecocardiograma complementario para evaluar función cardíaca.
"""


def test_parse_patient_name() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["patient_name"] == "Luna"


def test_parse_species() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["species"] == "Canino"


def test_parse_breed() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["breed"] == "Golden Retriever"


def test_parse_sex() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["sex"] == "Hembra"


def test_parse_age() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["age"] == "5 años"


def test_parse_owner() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["owner_name"] == "María García"


def test_parse_veterinarian() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["veterinarian"] == "Dr. Juan Pérez M.V."


def test_parse_date() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["date"] == "15/01/2025"


def test_parse_diagnosis() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["diagnosis"] is not None
    assert "cardiomegalia" in result["diagnosis"]
    assert "VHS" in result["diagnosis"]


def test_parse_recommendations() -> None:
    result = VeterinaryReportParser.parse(SAMPLE_REPORT)
    assert result["recommendations"] is not None
    assert "ecocardiograma" in result["recommendations"]


def test_missing_fields_return_none() -> None:
    result = VeterinaryReportParser.parse("Some random text without fields")
    assert result["patient_name"] is None
    assert result["species"] is None
    assert result["breed"] is None
    assert result["diagnosis"] is None
    assert result["recommendations"] is None


def test_parse_alternative_owner_label() -> None:
    text = "Propietario: Carlos López\nPaciente: Rex"
    result = VeterinaryReportParser.parse(text)
    assert result["owner_name"] == "Carlos López"


def test_parse_alternative_vet_label() -> None:
    text = "Profesional: Dra. Ana Ruiz\nPaciente: Firulais"
    result = VeterinaryReportParser.parse(text)
    assert result["veterinarian"] == "Dra. Ana Ruiz"


def test_parse_conclusion_as_diagnosis() -> None:
    text = """\
CONCLUSION:
Hallazgos compatibles con displasia de cadera bilateral grado III.
Osteofitos marginales en ambos acetábulos.
"""
    result = VeterinaryReportParser.parse(text)
    assert result["diagnosis"] is not None
    assert "displasia" in result["diagnosis"]


def test_parse_nombre_as_patient_name() -> None:
    text = "Nombre: Chester\nEspecie: Canino"
    result = VeterinaryReportParser.parse(text)
    assert result["patient_name"] == "Chester"


def test_parse_date_on_next_line() -> None:
    text = "Fecha\n11/03/2022\nINFORME RADIOLÓGICO"
    result = VeterinaryReportParser.parse(text)
    assert result["date"] == "11/03/2022"


def test_parse_empty_age_returns_none() -> None:
    text = "Edad:\nDATOS CLINICOS"
    result = VeterinaryReportParser.parse(text)
    assert result["age"] is None


def test_parse_diagnostico_lowercase() -> None:
    text = """\
Diagnostico radiográfico:
Imágenes sugerentes de osteosarcoma en húmero derecho.
"""
    result = VeterinaryReportParser.parse(text)
    assert result["diagnosis"] is not None
    assert "osteosarcoma" in result["diagnosis"]


def test_parse_chester_report() -> None:
    """Test with real Chester report text structure."""
    text = (
        "Fecha\n11/03/2022\n"
        "Nombre: Chester\nPropietario: Naveda\n"
        "Especie: Canino\nRaza: Dobermann\nSexo: M\nEdad:\n"
        "Referido por: Dra. Gerbeno\n"
        "Diagnostico radiográfico:\n"
        "Imágenes sugerentes de osteosarcoma en húmero derecho.\n"
        "Comentarios:\n"
        "Dr. Martin Vittaz\nMedico Veterinario\n"
    )
    result = VeterinaryReportParser.parse(text)
    assert result["patient_name"] == "Chester"
    assert result["owner_name"] == "Naveda"
    assert result["species"] == "Canino"
    assert result["breed"] == "Dobermann"
    assert result["sex"] == "M"
    assert result["age"] is None
    assert result["veterinarian"] == "Dra. Gerbeno"
    assert result["date"] == "11/03/2022"
    assert result["diagnosis"] is not None
    assert "osteosarcoma" in result["diagnosis"]
