"""Servicio de trazabilidad y reportes (M6): CU-10.

En H2.1 solo declara sus casos de uso; ninguno tiene lógica todavía.
"""

from __future__ import annotations

from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso


class ServicioReportes(ServicioCasosDeUso):
    """Trazabilidad y reportes (M6)."""

    NOMBRE: ClassVar[str] = "reportes"
    DESCRIPCION: ClassVar[str] = "Trazabilidad y reportes (M6)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso("CU-10", "Consultar trazabilidad y exportar reporte", "H2.7"),
    )
