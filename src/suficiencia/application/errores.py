"""Errores que pueden recibir quienes usan los servicios de aplicación.

Se reexportan desde el dominio para que la línea de comandos y la futura interfaz
los capturen sin importar el dominio directamente (contratos de ``.importlinter``).
"""

from __future__ import annotations

from suficiencia.domain.errores import (
    CasoDeUsoNoDisponible,
    ConfiguracionInvalida,
    DecisionPendiente,
    ErrorSuficiencia,
    HuellaInvalida,
)

__all__ = [
    "CasoDeUsoNoDisponible",
    "ConfiguracionInvalida",
    "DecisionPendiente",
    "ErrorSuficiencia",
    "HuellaInvalida",
]
