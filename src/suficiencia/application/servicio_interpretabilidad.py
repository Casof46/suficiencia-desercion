"""Servicio de explicaciones SHAP y LIME (M5): CU-09.

En H2.1 solo declara sus casos de uso; ninguno tiene lógica todavía.
"""

from __future__ import annotations

from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso


class ServicioInterpretabilidad(ServicioCasosDeUso):
    """Explicaciones SHAP y LIME (M5)."""

    NOMBRE: ClassVar[str] = "interpretabilidad"
    DESCRIPCION: ClassVar[str] = "Explicaciones SHAP y LIME (M5)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso("CU-09", "Generar explicaciones", "Fase posterior a la Fase 2"),
    )
