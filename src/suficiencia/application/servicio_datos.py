"""Servicio de importación, diccionario, auditoría y objetivo (M1): CU-01 a CU-03.

En H2.1 solo declara sus casos de uso; ninguno tiene lógica todavía.
"""

from __future__ import annotations

from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso


class ServicioDatos(ServicioCasosDeUso):
    """Importación, diccionario, auditoría y objetivo (M1)."""

    NOMBRE: ClassVar[str] = "datos"
    DESCRIPCION: ClassVar[str] = "Importación, diccionario, auditoría y objetivo (M1)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-01",
            "Importar y auditar un dataset",
            "H2.3 con datos sintéticos; con datos reales, además DP-02 y DP-14",
        ),
        DefinicionCasoDeUso(
            "CU-02",
            "Configurar el diccionario de variables",
            "H2.3 con un diccionario sintético; el real, además DP-03 y DP-15",
        ),
        DefinicionCasoDeUso("CU-03", "Construir el objetivo y los estados de etiqueta", "H2.4"),
    )
