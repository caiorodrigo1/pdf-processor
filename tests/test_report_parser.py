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
    assert result["sex"] == "Macho"
    assert result["age"] is None
    assert result["veterinarian"] == "Dra. Gerbeno"
    assert result["date"] == "11/03/2022"
    assert result["diagnosis"] is not None
    assert "osteosarcoma" in result["diagnosis"]


def test_normalize_sex_macho_castrado() -> None:
    text = "Sexo: Macho-Castrado\nEspecie: Canino"
    result = VeterinaryReportParser.parse(text)
    assert result["sex"] == "Macho castrado"


def test_normalize_sex_hembra_castrada() -> None:
    text = "Sexo: hembra castrada\nEspecie: Canino"
    result = VeterinaryReportParser.parse(text)
    assert result["sex"] == "Hembra castrada"


def test_normalize_sex_single_letter() -> None:
    text = "Sexo: M\nEdad: 5"
    result = VeterinaryReportParser.parse(text)
    assert result["sex"] == "Macho"


def test_normalize_sex_lowercase() -> None:
    text = "Sexo: macho\nEdad: 10"
    result = VeterinaryReportParser.parse(text)
    assert result["sex"] == "Macho"


def test_recommendations_strips_footer() -> None:
    text = (
        "Se recomienda control en 30 días.\n"
        "M.V. Alborno Nicolás E.\nM.P. 2938\nDiagnoVet"
    )
    result = VeterinaryReportParser.parse(text)
    assert result["recommendations"] == "control en 30 días."


def test_recommendations_strips_bullets() -> None:
    text = "Se recomienda • estudio radiológico de control."
    result = VeterinaryReportParser.parse(text)
    assert result["recommendations"] is not None
    assert not result["recommendations"].startswith("•")


def test_diagnosis_strips_bullets_and_newlines() -> None:
    text = """\
CONCLUSION:
• Catarata intumescente bilateral.
• Desprendimiento vítreo posterior.
"""
    result = VeterinaryReportParser.parse(text)
    assert result["diagnosis"] is not None
    assert "•" not in result["diagnosis"]
    assert "\n" not in result["diagnosis"]
    assert "Catarata intumescente bilateral." in result["diagnosis"]
    assert "Desprendimiento vítreo posterior." in result["diagnosis"]


def test_parse_date_yyyy_mm_dd_normalized() -> None:
    """Date in YYYY/MM/DD format is normalized to DD/MM/YYYY."""
    text = "Fecha: 2025/08/27\nPaciente: Ramón"
    result = VeterinaryReportParser.parse(text)
    assert result["date"] == "27/08/2025"


def test_parse_date_dd_mm_yyyy_unchanged() -> None:
    """Date already in DD/MM/YYYY stays as-is."""
    text = "Fecha: 15/01/2025\nPaciente: Luna"
    result = VeterinaryReportParser.parse(text)
    assert result["date"] == "15/01/2025"


def test_parse_ramon_report() -> None:
    """Test with real Ramón report text structure (diagnosis + Notas section)."""
    text = (
        "Informe Radiográfico\n"
        "Fecha: 2025/08/27\n"
        "Paciente: Ramón Tutor: Simonetti\n"
        "Especie: Canino Raza: Schnauzer miniatura\n"
        "Sexo: Macho-Castrado Edad: 13 años\n"
        "Derivante: Ghersevich Carolina\n"
        "Solicitud:\n"
        "Radiografía de tórax\n\n"
        "Se observa:\n"
        "Silueta cardiaca aumentada.\n"
        "No se observan signos de efusión pleural ni de neumotórax.\n\n"
        "M.V. Alborno Nicolás E.\nM.P. 2938\n351-3417639\n\n"
        "DIAGNÓSTICO RADIOGRÁFICO\n"
        "Espondilosis T13-L1.\n"
        "Signos de bronquitis crónica moderada.\n"
        "Presuntivo de mineralización distrófica pulmonar. "
        "Diagnostico menos probable:\nneoplasia miliar.\n"
        "Cardiomegalia.\n\n"
        "Notas:\n"
        "Se recomienda estudio radiológico de control en 30 días, "
        "según criterio clínico.\n\n"
        "M.V. Alborno Nicolás E.\nM.P. 2938\n351-3417639\n"
    )
    result = VeterinaryReportParser.parse(text)
    assert result["patient_name"] == "Ramón"
    assert result["owner_name"] == "Simonetti"
    assert result["date"] == "27/08/2025"
    assert result["sex"] == "Macho castrado"
    assert result["species"] == "Canino"
    assert result["breed"] == "Schnauzer miniatura"
    assert result["age"] == "13 años"
    assert result["veterinarian"] == "Ghersevich Carolina"
    assert result["diagnosis"] is not None
    assert "Espondilosis" in result["diagnosis"]
    assert "Cardiomegalia" in result["diagnosis"]
    assert "\n" not in result["diagnosis"]
    assert "•" not in result["diagnosis"]
    # Diagnosis should NOT include the Notas section
    assert "recomienda" not in (result["diagnosis"] or "")
    assert result["recommendations"] is not None
    assert "Se recomienda" in result["recommendations"]
    assert "estudio radiológico" in result["recommendations"]


def test_notas_section_multiline() -> None:
    """Notas: on its own line with content on the next line."""
    text = (
        "DIAGNÓSTICO RADIOGRÁFICO\n"
        "Cardiomegalia.\n\n"
        "Notas:\n"
        "• Se recomienda ecocardiograma complementario.\n\n"
        "M.V. Test\n"
    )
    result = VeterinaryReportParser.parse(text)
    assert result["recommendations"] is not None
    assert "Se recomienda" in result["recommendations"]
    assert "ecocardiograma" in result["recommendations"]


def test_diagnosis_stops_before_notas() -> None:
    """Diagnosis extraction should stop at Notas: section."""
    text = (
        "DIAGNÓSTICO RADIOGRÁFICO\n"
        "Espondilosis T13-L1.\n"
        "Cardiomegalia.\n"
        "\nNotas:\n"
        "Se recomienda control en 30 días.\n"
    )
    result = VeterinaryReportParser.parse(text)
    assert result["diagnosis"] is not None
    assert "Espondilosis" in result["diagnosis"]
    assert "recomienda" not in result["diagnosis"]
