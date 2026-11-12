"""Selección del modelo representativo y del umbral, solo con desarrollo (M4; F3.4).

- **Selección del modelo** (DP-10; RF-M4-08): en cada escenario se compara la métrica
  declarada de las cinco familias sobre sus probabilidades de validación fuera de
  fold. Entre las que quedan dentro del margen declarado respecto de la mejor, gana
  la primera en el orden de familias declarado (por ejemplo, de la más simple a la
  más compleja). Con margen cero gana la mejor.
- **Umbral** (DP-06; RF-M4-07): se elige con las probabilidades de validación del
  modelo seleccionado, nunca con la prueba.
- **Reentrenamiento** (DP-10): usar el modelo del último fold o volver a ajustar con
  todo el desarrollo.

Todo es dato obligatorio: un ``null`` detiene el programa con la decisión pendiente.
Este módulo no lee ninguna prueba: recibe solo probabilidades de validación.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.metricas import MAYOR_ES_MEJOR, MetricaProbabilidad


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Selección o umbral: {causa}",
        "Corrija la configuración; el ejemplo válido está en "
        "config/ejemplos/experimentos_ficticio.yaml.",
    )


def _campo(datos: Mapping[str, Any], clave: str, decision: str, donde: str) -> Any:
    if clave not in datos:
        raise _invalida(f"falta '{clave}' en {donde} ({decision}).")
    if datos[clave] is None:
        raise DecisionPendiente(decision, f"'{clave}' en {donde}")
    return datos[clave]


def _numero(valor: Any, campo: str, minimo: float, maximo: float | None) -> float:
    if isinstance(valor, bool) or not isinstance(valor, int | float) or not math.isfinite(valor):
        raise _invalida(f"'{campo}' debe ser un número.")
    if valor < minimo or (maximo is not None and valor > maximo):
        if maximo is None:
            raise _invalida(f"'{campo}' debe ser mayor o igual que {minimo:g}.")
        raise _invalida(f"'{campo}' debe estar entre {minimo:g} y {maximo:g}.")
    return float(valor)


class Reentrenamiento(Enum):
    ULTIMO_FOLD = "ultimo_fold"
    TODO_DESARROLLO = "todo_desarrollo"


@dataclass(frozen=True)
class DefinicionSeleccion:
    """Regla de selección del modelo representativo (DP-10)."""

    metrica: MetricaProbabilidad
    margen: float
    orden_familias: tuple[str, ...]
    reentrenamiento: Reentrenamiento


def definicion_seleccion_desde_datos(datos: Any, familias: tuple[str, ...]) -> DefinicionSeleccion:
    """Lee la sección ``seleccion``; ``familias`` son las cinco de RF-M3-01."""
    if datos is None:
        raise DecisionPendiente("DP-10", "la sección 'seleccion' de la configuración")
    if not isinstance(datos, Mapping):
        raise _invalida("'seleccion' debe ser un conjunto de campos.")
    extra = sorted(set(datos) - {"metrica", "margen", "orden_familias", "reentrenamiento"})
    if extra:
        raise _invalida(f"campos desconocidos en 'seleccion': {', '.join(extra)}.")
    try:
        metrica = MetricaProbabilidad(_campo(datos, "metrica", "DP-10", "seleccion"))
        reentrenamiento = Reentrenamiento(_campo(datos, "reentrenamiento", "DP-10", "seleccion"))
    except ValueError:
        raise _invalida(
            "'metrica' debe ser una métrica de probabilidad y 'reentrenamiento', "
            "ultimo_fold o todo_desarrollo."
        ) from None
    orden = _campo(datos, "orden_familias", "DP-10", "seleccion")
    if not isinstance(orden, list) or sorted(map(str, orden)) != sorted(familias):
        raise _invalida(
            f"'orden_familias' debe listar exactamente una vez cada familia: {', '.join(familias)}."
        )
    return DefinicionSeleccion(
        metrica=metrica,
        margen=_numero(_campo(datos, "margen", "DP-10", "seleccion"), "margen", 0, None),
        orden_familias=tuple(map(str, orden)),
        reentrenamiento=reentrenamiento,
    )


def seleccionar_familia(valores: Mapping[str, float], definicion: DefinicionSeleccion) -> str:
    """Familia representativa según la regla (DP-10), a partir de métricas de validación.

    Raises:
        ConfiguracionInvalida: si falta alguna familia o alguna métrica no está definida.
    """
    faltan = [f for f in definicion.orden_familias if f not in valores]
    if faltan:
        raise _invalida(f"faltan resultados de validación de: {', '.join(faltan)}.")
    signo = 1 if MAYOR_ES_MEJOR[definicion.metrica] else -1
    orientados = {f: signo * valores[f] for f in definicion.orden_familias}
    if any(not math.isfinite(v) for v in orientados.values()):
        raise _invalida(
            f"la métrica {definicion.metrica.value} no está definida para alguna familia."
        )
    mejor = max(orientados.values())
    return next(f for f in definicion.orden_familias if orientados[f] >= mejor - definicion.margen)


class ReglaUmbral(Enum):
    FIJO = "fijo"
    CUANTIL_Q = "cuantil_q"
    RECALL_MINIMO = "recall_minimo"


@dataclass(frozen=True)
class DefinicionUmbral:
    """Regla del umbral (DP-06). ``valor`` es el umbral fijo o el Recall mínimo."""

    regla: ReglaUmbral
    valor: float | None


def definicion_umbral_desde_datos(datos: Any, q: float | None) -> DefinicionUmbral:
    """Lee la sección ``umbral``; ``q`` es la capacidad de alerta (DP-08i), si se declaró."""
    if datos is None:
        raise DecisionPendiente("DP-06", "la sección 'umbral' de la configuración")
    if not isinstance(datos, Mapping):
        raise _invalida("'umbral' debe ser un conjunto de campos.")
    extra = sorted(set(datos) - {"regla", "valor"})
    if extra:
        raise _invalida(f"campos desconocidos en 'umbral': {', '.join(extra)}.")
    try:
        regla = ReglaUmbral(_campo(datos, "regla", "DP-06", "umbral"))
    except ValueError:
        raise _invalida("'regla' debe ser fijo, cuantil_q o recall_minimo.") from None
    if regla is ReglaUmbral.CUANTIL_Q:
        if "valor" in datos:
            raise _invalida("la regla cuantil_q usa q (DP-08i) y no lleva 'valor'.")
        if q is None:
            raise DecisionPendiente("DP-08i", "q, que la regla de umbral cuantil_q necesita")
        return DefinicionUmbral(regla, None)
    valor = _numero(_campo(datos, "valor", "DP-06", "umbral"), "valor", 0, 1)
    return DefinicionUmbral(regla, valor)


def elegir_umbral(
    y_validacion: np.ndarray,
    p_validacion: np.ndarray,
    definicion: DefinicionUmbral,
    q: float | None,
) -> float:
    """Umbral según la regla, con las probabilidades de validación (RF-M4-07).

    - ``fijo``: el valor declarado.
    - ``cuantil_q``: el cuantil 1 − q de las probabilidades de validación, para que
      alerte aproximadamente a la fracción q.
    - ``recall_minimo``: el mayor umbral cuyo Recall en validación alcanza el valor
      declarado (alerta cuando la probabilidad es mayor o igual que el umbral).
    """
    if definicion.regla is ReglaUmbral.FIJO:
        assert definicion.valor is not None
        return definicion.valor
    if definicion.regla is ReglaUmbral.CUANTIL_Q:
        assert q is not None
        return float(np.quantile(p_validacion, 1 - q))
    assert definicion.valor is not None
    positivos = p_validacion[y_validacion == 1]
    if len(positivos) == 0:
        raise _invalida("la validación no tiene positivos para la regla recall_minimo.")
    # El Recall con umbral t es la fracción de positivos con p ≥ t: el mayor t que
    # deja al menos ceil(valor · positivos) positivos es esa probabilidad positiva.
    necesarios = max(1, math.ceil(definicion.valor * len(positivos)))
    return float(np.sort(positivos)[::-1][necesarios - 1])
