"""Errores del dominio.

Todos los errores del motor heredan de :class:`ErrorSuficiencia` y llevan dos
partes en español: la causa y la acción sugerida (RNF-15). La línea de comandos y
la futura interfaz muestran ese texto tal cual, sin trazas internas.
"""

from __future__ import annotations

import re

_CODIGO_DECISION = re.compile(r"DP-\d{2}[a-m]?")
_CODIGO_CASO_DE_USO = re.compile(r"CU-\d{2}")


class ErrorSuficiencia(Exception):
    """Error del motor con causa y acción sugerida."""

    def __init__(self, causa: str, accion: str) -> None:
        if not causa.strip() or not accion.strip():
            raise ValueError("Un error del motor necesita causa y acción sugerida.")
        self.causa = causa.strip()
        self.accion = accion.strip()
        super().__init__(self.causa, self.accion)

    def __str__(self) -> str:
        return f"{self.causa} Acción sugerida: {self.accion}"


class ConfiguracionInvalida(ErrorSuficiencia):
    """Un archivo de configuración falta o no cumple su estructura."""


class DecisionPendiente(ErrorSuficiencia):
    """Una operación necesita un valor que depende de una decisión metodológica abierta.

    Cada decisión abierta entra en el código como un parámetro obligatorio sin
    valor por defecto. Si falta, el motor se detiene con este error en lugar de
    suponer un valor.
    """

    def __init__(self, decision: str, que_falta: str) -> None:
        if not _CODIGO_DECISION.fullmatch(decision):
            raise ValueError(f"Código de decisión no válido: {decision!r}.")
        self.decision = decision
        super().__init__(
            f"Falta {que_falta.strip()}, que depende de la decisión {decision}, todavía abierta.",
            f"Registre la decisión {decision} aprobada y su valor en la configuración "
            "antes de repetir la operación.",
        )


class CasoDeUsoNoDisponible(ErrorSuficiencia):
    """El caso de uso existe en la especificación pero aún no se ha construido."""

    def __init__(self, caso: str, hito: str) -> None:
        if not _CODIGO_CASO_DE_USO.fullmatch(caso):
            raise ValueError(f"Código de caso de uso no válido: {caso!r}.")
        self.caso = caso
        self.hito = hito
        super().__init__(
            f"El caso de uso {caso} todavía no está implementado.",
            f"Se construye en: {hito}. Consulte `suficiencia estado`.",
        )


class HuellaInvalida(ErrorSuficiencia):
    """Un texto no es una huella SHA-256 válida."""
