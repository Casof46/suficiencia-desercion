"""Evaluación comparativa frente a la referencia convencional (M4; RF-M4-15 a 21; F3.5).

- **R0 y controles** (DP-19): R0 usa la ventana de referencia ``t_ref`` con su conjunto
  más completo y la familia con mejor métrica en validación, sin compuerta, umbrales
  mínimos ni no inferioridad; los empates se resuelven con el orden de familias.
  R0-fam usa el escenario de R0 con la familia del modelo seleccionado; R-ven usa la
  ventana seleccionada con su conjunto más completo, solo si el seleccionado no lo es.
- **No inferioridad** (DP-20): Δ orientada (mayor es mejor); demostrada si el límite
  inferior del intervalo unilateral supera −δ; pérdida mayor que el margen si todo el
  intervalo bilateral queda por debajo de −δ; si no, no concluyente. Una diferencia no
  significativa nunca se clasifica como no inferior.
- **Anticipación y reducción de información** (RF-M4-20): exactas, sin incertidumbre.
- **Cobertura temprana** (CMP-3): solo si se aprueban q (DP-08i) y D3 (DP-17).
- **Estados C1 a C8** (RF-M4-21): primero la validez de la comparación; nunca se
  declara superioridad.

Todo valor (ventana de referencia, métricas, márgenes, nivel) es dato obligatorio.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.metricas import MetricaProbabilidad


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Referencia o comparación: {causa}",
        "Corrija la configuración; el ejemplo válido está en "
        "config/ejemplos/experimentos_ficticio.yaml.",
    )


def _campo(datos: Mapping[str, Any], clave: str, decision: str, donde: str) -> Any:
    if clave not in datos:
        raise _invalida(f"falta '{clave}' en {donde} ({decision}).")
    if datos[clave] is None:
        raise DecisionPendiente(decision, f"'{clave}' en {donde}")
    return datos[clave]


# --- R0 y controles (DP-19) ----------------------------------------------------------


class ConjuntoReferencia(Enum):
    MAS_COMPLETO = "mas_completo"


@dataclass(frozen=True)
class DefinicionReferencia:
    """Regla de R0 (DP-19a a c)."""

    ventana: str
    conjunto: ConjuntoReferencia
    metrica: MetricaProbabilidad


def definicion_referencia_desde_datos(datos: Any, ventanas: Sequence[str]) -> DefinicionReferencia:
    if datos is None:
        raise DecisionPendiente("DP-19", "la sección 'referencia' de la configuración")
    if not isinstance(datos, Mapping):
        raise _invalida("'referencia' debe ser un conjunto de campos.")
    extra = sorted(set(datos) - {"ventana", "conjunto", "metrica"})
    if extra:
        raise _invalida(f"campos desconocidos en 'referencia': {', '.join(extra)}.")
    ventana = _campo(datos, "ventana", "DP-19a", "referencia")
    if ventana not in ventanas:
        raise _invalida(f"la ventana de referencia debe ser una de {', '.join(ventanas)}.")
    try:
        conjunto = ConjuntoReferencia(_campo(datos, "conjunto", "DP-19b", "referencia"))
        metrica = MetricaProbabilidad(_campo(datos, "metrica", "DP-19c", "referencia"))
    except ValueError:
        raise _invalida(
            "'conjunto' debe ser mas_completo y 'metrica', una métrica de probabilidad."
        ) from None
    return DefinicionReferencia(str(ventana), conjunto, metrica)


def escenario_mas_completo(ventana: str, factibles: Mapping[str, int]) -> str:
    """El escenario factible de la ventana con más bloques (``factibles``: código → bloques).

    Raises:
        ConfiguracionInvalida: si la ventana no tiene escenarios factibles.
    """
    candidatos = {c: n for c, n in factibles.items() if c.split("|", 1)[0] == ventana}
    if not candidatos:
        raise _invalida(f"la ventana {ventana} no tiene escenarios factibles.")
    mayor = max(candidatos.values())
    completos = [c for c, n in candidatos.items() if n == mayor]
    if len(completos) > 1:
        raise _invalida(f"la ventana {ventana} tiene más de un conjunto más completo.")
    return completos[0]


def elegir_familia_referencia(
    valores: Mapping[str, float], orden_familias: Sequence[str], mayor_es_mejor: bool
) -> str:
    """Familia de R0: la mejor en validación; empates por el orden de familias (DP-19c).

    No consulta compuerta, umbrales mínimos ni no inferioridad (PU-22).
    """
    faltan = [f for f in orden_familias if f not in valores]
    if faltan:
        raise _invalida(f"faltan resultados de validación de: {', '.join(faltan)}.")
    signo = 1 if mayor_es_mejor else -1
    if any(not math.isfinite(valores[f]) for f in orden_familias):
        raise _invalida("la métrica de R0 no está definida para alguna familia.")
    mejor = max(signo * valores[f] for f in orden_familias)
    return next(f for f in orden_familias if signo * valores[f] == mejor)


@dataclass(frozen=True)
class Referente:
    """Un referente a construir: R0, R0-fam o R-ven."""

    codigo: str
    tipo: str
    escenario: str
    familia: str | None
    """Familia fija (R0-fam); ``None`` si se elige con la regla de R0."""


def referentes_a_construir(
    referencia: DefinicionReferencia,
    seleccionados: Mapping[str, str],
    factibles: Mapping[str, int],
) -> tuple[Referente, ...]:
    """R0, un R0-fam por familia seleccionada y un R-ven por ventana que lo necesite (PU-23).

    ``seleccionados`` asocia cada escenario con la familia que eligió el método. Como el
    escenario suficiente se conoce recién en la prueba, se construyen los controles de
    todos los escenarios candidatos y se congelan antes de abrirla (RF-M4-17).
    """
    escenario_r0 = escenario_mas_completo(referencia.ventana, factibles)
    referentes = [Referente("R0", "r0", escenario_r0, None)]
    for familia in sorted(set(seleccionados.values())):
        referentes.append(Referente(f"R0-fam-{familia}", "r0_fam", escenario_r0, familia))
    ventanas = sorted({e.split("|", 1)[0] for e in seleccionados})
    for ventana in ventanas:
        completo = escenario_mas_completo(ventana, factibles)
        necesita = any(e.split("|", 1)[0] == ventana and e != completo for e in seleccionados)
        if necesita and completo != escenario_r0:
            referentes.append(Referente(f"R-ven-{ventana}", "r_ven", completo, None))
    return tuple(referentes)


# --- Protocolo comparativo (DP-20) ---------------------------------------------------


@dataclass(frozen=True)
class DefinicionComparacion:
    metricas: tuple[MetricaProbabilidad, ...]
    margenes: Mapping[str, float]
    nivel: float


def definicion_comparacion_desde_datos(datos: Any) -> DefinicionComparacion:
    if datos is None:
        raise DecisionPendiente("DP-20", "la sección 'comparacion' de la configuración")
    if not isinstance(datos, Mapping):
        raise _invalida("'comparacion' debe ser un conjunto de campos.")
    extra = sorted(set(datos) - {"metricas", "margenes", "nivel"})
    if extra:
        raise _invalida(f"campos desconocidos en 'comparacion': {', '.join(extra)}.")
    nombres = _campo(datos, "metricas", "DP-20a", "comparacion")
    if not isinstance(nombres, list) or not nombres or len(set(nombres)) != len(nombres):
        raise _invalida("'comparacion.metricas' debe listar métricas sin repetir.")
    try:
        metricas = tuple(MetricaProbabilidad(n) for n in nombres)
    except ValueError:
        raise _invalida(f"métrica desconocida en {nombres}.") from None
    margenes = _campo(datos, "margenes", "DP-20b", "comparacion")
    if not isinstance(margenes, Mapping) or set(margenes) != {m.value for m in metricas}:
        raise _invalida("'comparacion.margenes' debe dar un margen a cada métrica comparada.")
    leidos = {}
    for nombre, margen in margenes.items():
        if margen is None:
            raise DecisionPendiente("DP-20b", f"el margen de {nombre}")
        if isinstance(margen, bool) or not isinstance(margen, int | float) or margen < 0:
            raise _invalida(f"el margen de {nombre} debe ser un número mayor o igual que 0.")
        leidos[str(nombre)] = float(margen)
    nivel = _campo(datos, "nivel", "DP-20d", "comparacion")
    if isinstance(nivel, bool) or not isinstance(nivel, int | float) or not 0 < nivel < 1:
        raise _invalida("'comparacion.nivel' debe estar entre 0 y 1, sin incluirlos.")
    return DefinicionComparacion(metricas, leidos, float(nivel))


class EstadoNoInferioridad(Enum):
    DEMOSTRADA = "demostrada"
    NO_CONCLUYENTE = "no_concluyente"
    PERDIDA = "perdida_mayor_que_el_margen"


@dataclass(frozen=True)
class NoInferioridad:
    estado: EstadoNoInferioridad
    diferencia: float
    limite_unilateral: float
    bilateral: tuple[float, float]
    margen: float


def clasificar_no_inferioridad(
    diferencia: float, replicas: np.ndarray, margen: float, nivel: float
) -> NoInferioridad:
    """Regla de no inferioridad frente a R0 (RF-M4-19; PU-25).

    ``replicas`` son las réplicas bootstrap pareadas de Δ (mayor es mejor). Con
    ``nivel`` = 1 − α: unilateral, el cuantil α; bilateral, los cuantiles α/2 y 1 − α/2.

    Raises:
        ConfiguracionInvalida: si no hay réplicas válidas.
    """
    validas = replicas[np.isfinite(replicas)]
    if len(validas) == 0 or not math.isfinite(diferencia):
        raise _invalida("la diferencia no está definida en ninguna réplica.")
    alfa = 1 - nivel
    unilateral = float(np.quantile(validas, alfa))
    inferior, superior = (float(v) for v in np.quantile(validas, [alfa / 2, 1 - alfa / 2]))
    if unilateral > -margen:
        estado = EstadoNoInferioridad.DEMOSTRADA
    elif superior < -margen:
        estado = EstadoNoInferioridad.PERDIDA
    else:
        estado = EstadoNoInferioridad.NO_CONCLUYENTE
    return NoInferioridad(estado, diferencia, unilateral, (inferior, superior), margen)


# --- Anticipación, reducción de información y cobertura (RF-M4-20) ----------------------


@dataclass(frozen=True)
class Anticipacion:
    ventanas: int
    ciclos: int


def anticipacion(
    ventana_seleccionada: str, ventana_referencia: str, periodos: Mapping[str, int]
) -> Anticipacion:
    """Ventanas y ciclos de diferencia; positivos si la seleccionada es anterior a t_ref."""
    orden = list(periodos)
    return Anticipacion(
        ventanas=orden.index(ventana_referencia) - orden.index(ventana_seleccionada),
        ciclos=periodos[ventana_referencia] - periodos[ventana_seleccionada],
    )


@dataclass(frozen=True)
class Reduccion:
    bloques_usados: tuple[str, ...]
    bloques_evitados: tuple[str, ...]
    variables_usadas: tuple[str, ...]
    variables_evitadas: tuple[str, ...]


def reduccion_informacion(
    bloques_seleccionada: Sequence[str],
    bloques_referencia: Sequence[str],
    variables_seleccionada: Sequence[str],
    variables_referencia: Sequence[str],
) -> Reduccion:
    """Bloques y variables de R0 que la seleccionada no usa (exacto, sin incertidumbre)."""
    return Reduccion(
        bloques_usados=tuple(sorted(set(bloques_seleccionada))),
        bloques_evitados=tuple(sorted(set(bloques_referencia) - set(bloques_seleccionada))),
        variables_usadas=tuple(sorted(set(variables_seleccionada))),
        variables_evitadas=tuple(sorted(set(variables_referencia) - set(variables_seleccionada))),
    )


@dataclass(frozen=True)
class Cobertura:
    desertores: int
    seleccionada: float
    referencia: float


def cobertura_temprana(
    periodo_evento: Sequence[int],
    alerta_seleccionada: Sequence[bool],
    alerta_referencia: Sequence[bool],
    periodo_referencia: int,
) -> Cobertura:
    """Proporción de desertores en riesgo en t* que reciben alerta antes de su evento (CMP-3).

    Una entrada por desertor en riesgo en t*. La referencia solo alerta a quien sigue en
    riesgo en t_ref: quien deserta antes cuenta como no alertado por R0 (PU-26).
    """
    if not len(periodo_evento) == len(alerta_seleccionada) == len(alerta_referencia):
        raise _invalida("las listas de la cobertura deben tener el mismo largo.")
    total = len(periodo_evento)
    if total == 0:
        raise _invalida("no hay desertores en riesgo en la ventana seleccionada.")
    referencia = sum(
        1
        for evento, alerta in zip(periodo_evento, alerta_referencia, strict=True)
        if alerta and evento > periodo_referencia
    )
    return Cobertura(total, sum(map(bool, alerta_seleccionada)) / total, referencia / total)


# --- Validez y estados C1 a C8 (RF-M4-21) ---------------------------------------------


@dataclass(frozen=True)
class Validez:
    mismo_evento: bool
    mismo_horizonte: bool
    misma_poblacion: bool
    mismas_cohortes: bool
    referencia_evaluable: bool

    def motivos(self) -> tuple[str, ...]:
        nombres = {
            "mismo_evento": "difiere el evento",
            "mismo_horizonte": "difiere el horizonte",
            "misma_poblacion": "difiere la población comparada",
            "mismas_cohortes": "difieren las cohortes de prueba",
            "referencia_evaluable": "R0 no es evaluable",
        }
        return tuple(m for campo, m in nombres.items() if not getattr(self, campo))


class EstadoComparacion(Enum):
    C1 = "C1_suficiente_y_no_inferior"
    C2 = "C2_anticipacion_respaldada"
    C3 = "C3_no_inferioridad_no_demostrada"
    C4 = "C4_perdida_mayor_que_el_margen"
    C5 = "C5_ninguna_configuracion_suficiente"
    C6 = "C6_indeterminado"
    C7 = "C7_comparacion_no_valida"
    C8 = "C8_sin_ganancia"


def clasificar_comparacion(
    validez: Validez,
    estado_regla: str,
    mismo_escenario_que_r0: bool,
    no_inferioridad: Sequence[EstadoNoInferioridad] | None,
    anticipa: bool,
) -> EstadoComparacion:
    """Estado de la tabla de interpretación (RF-M4-21; PU-27). Nunca "superior".

    ``estado_regla`` es el de la regla de suficiencia en la prueba;
    ``no_inferioridad``, el estado de cada métrica (``None`` si no pudo evaluarse).
    """
    if validez.motivos():
        return EstadoComparacion.C7
    if estado_regla == "ningun_escenario_cumple":
        return EstadoComparacion.C5
    if estado_regla != "escenario_suficiente" or not no_inferioridad:
        return EstadoComparacion.C6
    if mismo_escenario_que_r0:
        return EstadoComparacion.C8
    if EstadoNoInferioridad.PERDIDA in no_inferioridad:
        return EstadoComparacion.C4
    if EstadoNoInferioridad.NO_CONCLUYENTE in no_inferioridad:
        return EstadoComparacion.C3
    return EstadoComparacion.C2 if anticipa else EstadoComparacion.C1
