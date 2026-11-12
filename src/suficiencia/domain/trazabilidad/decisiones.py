"""Estado de las decisiones metodológicas DP-01 a DP-20 (RF-M6-05; H2.8).

Cruza el catálogo de la sección 12 de la especificación con el registro de
decisiones. Una decisión está **registrada** solo si el registro tiene una entrada
con su código exacto. Los subcódigos registrados (por ejemplo, DP-08h) se muestran
junto a su decisión, pero no la cierran: DP-08 sigue abierta aunque DP-08h esté
decidida. Este módulo no decide nada: solo informa.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from suficiencia.domain.errores import ConfiguracionInvalida

_CODIGO = re.compile(r"DP-\d{2}")
_CAMPOS = ("codigo", "nombre", "decide", "resolver_antes_de")


@dataclass(frozen=True)
class DecisionCatalogada:
    codigo: str
    nombre: str
    decide: str
    resolver_antes_de: str


@dataclass(frozen=True)
class DecisionRegistrada:
    codigo: str
    fecha: str
    decision: str
    responsable: str
    observaciones: str | None


@dataclass(frozen=True)
class EstadoDecision:
    catalogada: DecisionCatalogada
    registros: tuple[DecisionRegistrada, ...]

    @property
    def registrada(self) -> bool:
        return any(r.codigo == self.catalogada.codigo for r in self.registros)

    @property
    def subcodigos(self) -> tuple[DecisionRegistrada, ...]:
        return tuple(r for r in self.registros if r.codigo != self.catalogada.codigo)


def _invalido(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Catálogo de decisiones: {causa}",
        "Corrija config/decisiones_metodologicas.yaml (sección 12 de la especificación).",
    )


def catalogo_desde_datos(datos: Any) -> tuple[DecisionCatalogada, ...]:
    """Lee el catálogo; exige DP-01 a DP-20, una vez cada una y en orden."""
    if not isinstance(datos, Mapping) or not isinstance(datos.get("decisiones"), list):
        raise _invalido("falta la lista 'decisiones'.")
    catalogo = []
    for elemento in datos["decisiones"]:
        if not isinstance(elemento, Mapping) or set(elemento) != set(_CAMPOS):
            raise _invalido(f"cada decisión debe tener exactamente: {', '.join(_CAMPOS)}.")
        if not all(isinstance(elemento[c], str) and elemento[c].strip() for c in _CAMPOS):
            raise _invalido(f"la decisión {elemento.get('codigo')!r} tiene campos vacíos.")
        if not _CODIGO.fullmatch(elemento["codigo"]):
            raise _invalido(f"'{elemento['codigo']}' no es un código DP-xx.")
        catalogo.append(DecisionCatalogada(*(elemento[c].strip() for c in _CAMPOS)))
    esperados = [f"DP-{n:02d}" for n in range(1, 21)]
    if [d.codigo for d in catalogo] != esperados:
        raise _invalido("debe listar DP-01 a DP-20, una vez cada una y en orden.")
    return tuple(catalogo)


def estado_decisiones(
    catalogo: Sequence[DecisionCatalogada], registros: Sequence[DecisionRegistrada]
) -> tuple[EstadoDecision, ...]:
    """Asocia a cada decisión del catálogo sus registros y los de sus subcódigos, en orden."""
    return tuple(
        EstadoDecision(
            catalogada=decision,
            registros=tuple(r for r in registros if r.codigo[:5] == decision.codigo),
        )
        for decision in catalogo
    )
