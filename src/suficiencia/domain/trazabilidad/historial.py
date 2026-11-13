"""Funciones del visor que dependen de decisiones abiertas y comparación del historial
de experimentos (F4.4; RF-UI-04, RF-M6-02).

- **Dependencias (RF-UI-04):** cada función del visor declara las decisiones de las que
  depende su versión con datos y configuración del proyecto. Mientras alguna esté
  abierta en el registro de decisiones, esa versión queda desactivada; la demostración
  con ejemplos ficticios sigue disponible. Este módulo no decide nada: cruza la lista
  con el estado de las decisiones.
- **Historial (RF-M6-02):** compara dos registros de experimento campo por campo, con
  lo que guardó el registro. No recalcula nada.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FuncionVisor:
    """Una función del visor y las decisiones de las que depende con datos del proyecto."""

    codigo: str
    nombre: str
    decisiones: tuple[str, ...]


# Decisiones de las que depende cada función con datos y configuración del proyecto
# (sección 12 de la especificación v0.6, columna "resolver antes de", y los módulos que
# usa cada página). Con los ejemplos ficticios, todas las funciones están disponibles.
FUNCIONES_VISOR: tuple[FuncionVisor, ...] = (
    FuncionVisor("datos", "Importar y auditar datos", ("DP-02", "DP-03", "DP-14", "DP-15")),
    FuncionVisor("escenarios", "Generar escenarios y verificar fugas", ("DP-01", "DP-03")),
    FuncionVisor("objetivo", "Construir el objetivo", ("DP-01", "DP-18")),
    FuncionVisor(
        "poblaciones",
        "Poblaciones, partición y sello de la prueba",
        ("DP-01", "DP-04", "DP-05", "DP-17"),
    ),
    FuncionVisor(
        "validacion",
        "Métricas de los escenarios en validación",
        ("DP-06", "DP-07", "DP-08", "DP-09", "DP-12"),
    ),
    FuncionVisor(
        "resultados",
        "Selección, evaluación final, comparación con R0 y explicaciones",
        ("DP-06", "DP-07", "DP-08", "DP-09", "DP-10", "DP-11", "DP-12", "DP-19", "DP-20"),
    ),
    FuncionVisor(
        "estabilidad",
        "Estabilidad de la selección y de las explicaciones, y R-max (F4.2)",
        ("DP-11", "DP-19", "DP-20"),
    ),
)


@dataclass(frozen=True)
class Disponibilidad:
    funcion: FuncionVisor
    abiertas: tuple[str, ...]

    @property
    def con_datos_del_proyecto(self) -> bool:
        """Solo si todas sus decisiones están registradas."""
        return not self.abiertas


def disponibilidad(
    funciones: Sequence[FuncionVisor], registradas: Mapping[str, bool]
) -> tuple[Disponibilidad, ...]:
    """Qué decisiones siguen abiertas para cada función.

    Una decisión que no aparece en ``registradas`` cuenta como abierta.
    """
    return tuple(
        Disponibilidad(f, tuple(d for d in f.decisiones if not registradas.get(d, False)))
        for f in funciones
    )


# --- Historial de experimentos (RF-M6-02) ---------------------------------------------

CAMPOS_COMPARADOS = (
    "estado",
    "modo",
    "version_protocolo",
    "huella_datos",
    "configuracion",
    "semillas",
    "error",
)


def _texto(valor: Any) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, str):
        return valor
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


def aplanar(contenido: Mapping[str, Any], prefijo: str = "") -> dict[str, str]:
    """Campos anidados como ``configuracion.escenario``; las listas quedan como texto."""
    plano: dict[str, str] = {}
    for clave, valor in contenido.items():
        nombre = f"{prefijo}{clave}"
        if isinstance(valor, Mapping):
            plano.update(aplanar(valor, f"{nombre}."))
        else:
            plano[nombre] = _texto(valor)
    return plano


@dataclass(frozen=True)
class DiferenciaCampo:
    campo: str
    valor_a: str
    valor_b: str

    @property
    def igual(self) -> bool:
        return self.valor_a == self.valor_b


def comparar_registros(
    a: Mapping[str, Any], b: Mapping[str, Any], campos: Sequence[str] = CAMPOS_COMPARADOS
) -> tuple[DiferenciaCampo, ...]:
    """Cada campo de los dos experimentos, en orden alfabético; «—» si a uno le falta."""
    plano_a = aplanar({c: a[c] for c in campos if c in a})
    plano_b = aplanar({c: b[c] for c in campos if c in b})
    return tuple(
        DiferenciaCampo(campo, plano_a.get(campo, "—"), plano_b.get(campo, "—"))
        for campo in sorted(set(plano_a) | set(plano_b))
    )
