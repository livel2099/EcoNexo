from app.schemas import EmailRegisterIn
from app.territory import (
    DEPARTMENTS,
    MUNICIPALITIES,
    is_in_misiones,
    local_context,
    municipality_department,
)


def test_misiones_catalog_has_17_departments_and_79_municipalities():
    assert len(DEPARTMENTS) == 17
    assert len(MUNICIPALITIES) == 79
    assert municipality_department("Dos Hermanas") == "General Manuel Belgrano"
    assert municipality_department("Posadas") == "Capital"


def test_coordinate_filter_accepts_misiones_and_rejects_corrientes():
    assert is_in_misiones(-27.3621, -55.9007)  # Posadas
    assert is_in_misiones(-27.3696, -55.5818)  # Santa Ana
    assert is_in_misiones(-26.01709, -53.78987)  # San Antonio, General Manuel Belgrano
    assert not is_in_misiones(-27.4692, -58.8306)  # Corrientes capital
    assert local_context(-27.4692, -58.8306)["inside_misiones"] is False


def test_registration_normalizes_department_from_municipality():
    body = EmailRegisterIn(
        organization_name="Laboratorio Misiones",
        vertical="municipio",
        municipality="Oberá",
        department=None,
        name="Responsable Técnico",
        email="responsable@example.com",
        phone="+5493764123456",
        password="Clave2026!",
        terms_accepted=True,
    )
    assert body.department == "Oberá"


def test_georef_feature_selection_is_misiones_only():
    from app.territory import georef_misiones_feature

    payload = {
        "features": [
            {"properties": {"nombre": "CORRIENTES"}, "geometry": {"type": "Polygon", "coordinates": []}},
            {"properties": {"nombre": "MISIONES"}, "geometry": {"type": "MultiPolygon", "coordinates": []}},
        ]
    }
    selected = georef_misiones_feature(payload)
    assert selected is not None
    assert selected["properties"]["nombre"] == "MISIONES"
