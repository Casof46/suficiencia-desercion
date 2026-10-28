"""Servicio de experimentos de desarrollo, selección y congelamiento (M3, M4): CU-06 y CU-07.

En H2.1 solo declara sus casos de uso; ninguno tiene lógica todavía.
"""

from __future__ import annotations

from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso


class ServicioExperimentos(ServicioCasosDeUso):
    """Experimentos de desarrollo, selección y congelamiento (M3, M4)."""

    NOMBRE: ClassVar[str] = "experimentos"
    DESCRIPCION: ClassVar[str] = "Experimentos de desarrollo, selección y congelamiento (M3, M4)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-06", "Ejecutar experimentos de desarrollo", "una fase posterior a la Fase 2"
        ),
        DefinicionCasoDeUso(
            "CU-07",
            "Seleccionar y congelar configuraciones",
            "H2.6 (congelamiento) y fase posterior a la Fase 2 (selección)",
        ),
    )
