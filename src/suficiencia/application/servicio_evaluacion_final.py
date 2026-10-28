"""Servicio de evaluación final y comparación con la referencia (M4): CU-08 y CU-12.

En H2.1 solo declara sus casos de uso; ninguno tiene lógica todavía.
"""

from __future__ import annotations

from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso


class ServicioEvaluacionFinal(ServicioCasosDeUso):
    """Evaluación final, regla de suficiencia y comparación con la referencia (M4)."""

    NOMBRE: ClassVar[str] = "evaluacion_final"
    DESCRIPCION: ClassVar[str] = (
        "Evaluación final, regla de suficiencia y comparación con la referencia (M4)."
    )
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-08",
            "Ejecutar evaluación final y regla de suficiencia",
            "Fase posterior a la Fase 2",
        ),
        DefinicionCasoDeUso(
            "CU-12",
            "Ejecutar la evaluación comparativa frente a la referencia",
            "Fase posterior a la Fase 2",
        ),
    )
