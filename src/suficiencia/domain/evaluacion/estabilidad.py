"""Estabilidad descriptiva de la selección y de las explicaciones (F4.2).

- **Estabilidad de la selección (CMP-5; RF-M4-22):** en cada fold de desarrollo se
  aplica el criterio del protocolo a las probabilidades de validación de ese fold, y se
  cuenta en cuántos folds cada escenario cumple las condiciones y en cuántos la regla
  lo elegiría. Es descriptiva: no es una prueba entre cohortes (DP-20g).
- **Estabilidad de las explicaciones (RF-M5-06):** se compara la importancia que dan
  los modelos de cada fold con la del modelo congelado: proporción de cada bloque y
  correlación de rangos de Spearman de las variables.

No contiene umbrales: el criterio llega del protocolo y nada se compara con un valor
fijo. Ninguna salida es una conclusión sobre el método.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.evaluacion.suficiencia import (
    CriterioSuficiencia,
    EstadoEscenario,
    ProcedimientoMultiplicidad,
    ResultadoEscenario,
    aplicar_regla,
)

# --- Selección por fold (CMP-5) -------------------------------------------------------


@dataclass(frozen=True)
class FrecuenciaEscenario:
    """Cuántos folds de desarrollo cumplió cada escenario y cuántos lo eligió la regla."""

    escenario: str
    folds: int
    evaluables: int
    """Folds en los que todas las condiciones se pudieron evaluar."""
    cumple: int
    elegido: int


@dataclass(frozen=True)
class ReglaEnFold:
    fold: int
    estado: str
    escenario: str | None


def estabilidad_seleccion(
    criterio: CriterioSuficiencia,
    por_fold: Mapping[int, Sequence[ResultadoEscenario]],
    procedimientos: Mapping[str, ProcedimientoMultiplicidad],
) -> tuple[tuple[FrecuenciaEscenario, ...], tuple[ReglaEnFold, ...]]:
    """Aplica la regla en cada fold y cuenta, por escenario, cumplimientos y elecciones.

    ``por_fold`` asocia cada fold con los resultados de todos los escenarios en ese
    fold; todos los folds deben tener los mismos escenarios.

    Raises:
        ConfiguracionInvalida: si no hay folds o los escenarios cambian entre folds.
    """
    if not por_fold:
        raise ConfiguracionInvalida(
            "No hay folds de desarrollo para describir la estabilidad.",
            "Entrene los escenarios con la validación cronológica por cohortes (DP-07).",
        )
    escenarios = [r.escenario for r in next(iter(por_fold.values()))]
    for resultados in por_fold.values():
        if sorted(r.escenario for r in resultados) != sorted(escenarios):
            raise ConfiguracionInvalida(
                "Los folds no tienen los mismos escenarios.",
                "Use las corridas de los mismos escenarios en todos los folds.",
            )
    cuentas = {e: {"evaluables": 0, "cumple": 0, "elegido": 0} for e in escenarios}
    reglas = []
    for fold in sorted(por_fold):
        resultado = aplicar_regla(criterio, por_fold[fold], procedimientos)
        for evaluacion in resultado.evaluaciones:
            cuenta = cuentas[evaluacion.escenario]
            if evaluacion.estado is not EstadoEscenario.NO_EVALUABLE:
                cuenta["evaluables"] += 1
            if evaluacion.estado is EstadoEscenario.CUMPLE:
                cuenta["cumple"] += 1
        if resultado.escenario is not None:
            cuentas[resultado.escenario]["elegido"] += 1
        reglas.append(ReglaEnFold(fold, resultado.estado.value, resultado.escenario))
    frecuencias = tuple(
        FrecuenciaEscenario(
            escenario=e,
            folds=len(por_fold),
            evaluables=cuentas[e]["evaluables"],
            cumple=cuentas[e]["cumple"],
            elegido=cuentas[e]["elegido"],
        )
        for e in escenarios
    )
    return frecuencias, tuple(reglas)


# --- Explicaciones entre folds (RF-M5-06) -----------------------------------------------


def _rangos(valores: np.ndarray) -> np.ndarray:
    """Rangos con empates promediados (1 = el menor)."""
    orden = np.argsort(valores, kind="mergesort")
    ordenados = valores[orden]
    rangos = np.empty(len(valores), dtype="float64")
    inicio = 0
    while inicio < len(valores):
        fin = inicio
        while fin + 1 < len(valores) and ordenados[fin + 1] == ordenados[inicio]:
            fin += 1
        rangos[orden[inicio : fin + 1]] = (inicio + fin) / 2 + 1
        inicio = fin + 1
    return rangos


def correlacion_rangos(a: Mapping[str, float], b: Mapping[str, float]) -> float | None:
    """Correlación de Spearman entre dos importancias por variable.

    Devuelve ``None`` si hay menos de dos variables o si alguna importancia es
    constante (la correlación no está definida).

    Raises:
        ConfiguracionInvalida: si las dos importancias no tienen las mismas variables.
    """
    if set(a) != set(b):
        raise ConfiguracionInvalida(
            "Las importancias comparadas no tienen las mismas variables.",
            "Compare modelos del mismo escenario.",
        )
    nombres = sorted(a)
    if len(nombres) < 2:
        return None
    ra = _rangos(np.array([a[n] for n in nombres], dtype="float64"))
    rb = _rangos(np.array([b[n] for n in nombres], dtype="float64"))
    if np.all(ra == ra[0]) or np.all(rb == rb[0]):
        return None
    valor = float(np.corrcoef(ra, rb)[0, 1])
    return valor if math.isfinite(valor) else None


def proporciones(importancias: Mapping[str, float]) -> dict[str, float]:
    """Parte de la importancia total que corresponde a cada clave (0 si el total es 0)."""
    total = sum(importancias.values())
    return {k: (v / total if total > 0 else 0) for k, v in importancias.items()}


@dataclass(frozen=True)
class EstabilidadExplicaciones:
    """Importancia de los modelos de cada fold frente a la del modelo congelado."""

    bloques_por_fold: Mapping[int, Mapping[str, float]]
    """Proporción de la importancia de cada bloque, por fold."""
    bloques_congelado: Mapping[str, float]
    correlaciones: Mapping[int, float | None]
    """Spearman entre la importancia por variable de cada fold y la del congelado."""

    @property
    def rango_bloques(self) -> dict[str, tuple[float, float]]:
        """Proporción mínima y máxima de cada bloque entre los folds."""
        bloques = list(self.bloques_congelado)
        return {
            b: (
                min(f.get(b, 0) for f in self.bloques_por_fold.values()),
                max(f.get(b, 0) for f in self.bloques_por_fold.values()),
            )
            for b in bloques
        }

    @property
    def correlacion_minima(self) -> float | None:
        definidas = [c for c in self.correlaciones.values() if c is not None]
        return min(definidas) if definidas else None

    @property
    def correlacion_media(self) -> float | None:
        definidas = [c for c in self.correlaciones.values() if c is not None]
        return sum(definidas) / len(definidas) if definidas else None


def estabilidad_explicaciones(
    congelado_variables: Mapping[str, float],
    congelado_bloques: Mapping[str, float],
    folds_variables: Mapping[int, Mapping[str, float]],
    folds_bloques: Mapping[int, Mapping[str, float]],
) -> EstabilidadExplicaciones:
    """Compara la importancia de cada fold con la del modelo congelado (RF-M5-06).

    Raises:
        ConfiguracionInvalida: si no hay folds o los folds no coinciden.
    """
    if not folds_variables or set(folds_variables) != set(folds_bloques):
        raise ConfiguracionInvalida(
            "Faltan las importancias de los modelos de los folds.",
            "Explique los modelos de todos los folds de la corrida.",
        )
    return EstabilidadExplicaciones(
        bloques_por_fold={f: proporciones(folds_bloques[f]) for f in sorted(folds_bloques)},
        bloques_congelado=proporciones(congelado_bloques),
        correlaciones={
            f: correlacion_rangos(congelado_variables, folds_variables[f])
            for f in sorted(folds_variables)
        },
    )
