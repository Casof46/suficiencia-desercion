"""Servicio de escenarios, poblaciones, particiones y análisis exploratorio (M2): CU-04 y CU-11.

En H2.1 solo declara sus casos de uso; ninguno tiene lógica todavía.
"""

from __future__ import annotations

from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso


class ServicioEscenarios(ServicioCasosDeUso):
    """Escenarios, poblaciones, particiones y análisis exploratorio (M2)."""

    NOMBRE: ClassVar[str] = "escenarios"
    DESCRIPCION: ClassVar[str] = (
        "Escenarios, poblaciones, particiones y análisis exploratorio (M2)."
    )
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-04",
            "Generar escenarios, poblaciones y particiones",
            "H2.2 (escenarios) y H2.5 (poblaciones y particiones)",
        ),
        DefinicionCasoDeUso("CU-11", "Ejecutar el análisis exploratorio de viabilidad", "H2.5"),
    )
