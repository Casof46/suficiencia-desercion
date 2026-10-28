"""Huella SHA-256 de un contenido (RNF-16).

Datos, particiones, protocolos y configuraciones congeladas se identifican por la
huella de su contenido. Calcularla no requiere entrada ni salida: recibe bytes.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from suficiencia.domain.errores import HuellaInvalida

_FORMATO = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class Huella:
    """Huella SHA-256 en hexadecimal, 64 caracteres en minúscula."""

    valor: str

    def __post_init__(self) -> None:
        if not isinstance(self.valor, str) or not _FORMATO.fullmatch(self.valor):
            raise HuellaInvalida(
                f"{self.valor!r} no es una huella SHA-256 válida.",
                "Use 64 caracteres hexadecimales en minúscula, o calcule la huella "
                "con Huella.de_bytes().",
            )

    @classmethod
    def de_bytes(cls, contenido: bytes) -> Huella:
        """Calcula la huella del contenido."""
        return cls(hashlib.sha256(contenido).hexdigest())

    def __str__(self) -> str:
        return self.valor
