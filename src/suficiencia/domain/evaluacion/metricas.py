"""Métricas, intervalos bootstrap y diferencias pareadas (M4; RF-M4-01 a 03, RF-M4-18; F3.3).

Funciones puras sobre etiquetas (0/1) y probabilidades, sin scikit-learn: el
dominio no depende de bibliotecas de aprendizaje automático (RNF-01). PU-07
comprueba que coinciden con scikit-learn.

Qué métricas se calculan (DP-08a), la capacidad de alerta q (DP-08i) y el método
de intervalo, su nivel, sus réplicas y su estratificación (DP-08e) son datos
obligatorios: ver ``definicion_metricas_desde_datos``.

Cada métrica se informa con la prevalencia de la población evaluada (RF-M4-01).
Las diferencias se orientan para que un valor mayor sea mejor (sección de la regla
de no inferioridad de la especificación).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Métricas o intervalos: {causa}",
        "Corrija la configuración; el ejemplo válido está en "
        "config/ejemplos/experimentos_ficticio.yaml.",
    )


def _validar(y: np.ndarray, p: np.ndarray) -> None:
    if y.shape != p.shape or y.ndim != 1 or len(y) == 0:
        raise _invalida("las etiquetas y las probabilidades deben ser vectores del mismo largo.")
    if not np.isin(y, (0, 1)).all():
        raise _invalida("las etiquetas deben ser 0 o 1.")
    if not (np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all()):
        raise _invalida("las probabilidades deben estar entre 0 y 1.")


def _rangos(valores: np.ndarray) -> np.ndarray:
    """Rangos desde 1, con el promedio en los empates."""
    orden = np.argsort(valores, kind="mergesort")
    ordenados = valores[orden]
    rangos = np.empty(len(valores), dtype="float64")
    inicio = 0
    while inicio < len(ordenados):
        fin = inicio
        while fin + 1 < len(ordenados) and ordenados[fin + 1] == ordenados[inicio]:
            fin += 1
        rangos[orden[inicio : fin + 1]] = (inicio + fin) / 2 + 1
        inicio = fin + 1
    return rangos


def auc_roc(y: np.ndarray, p: np.ndarray) -> float:
    """Área bajo la curva ROC (Mann-Whitney, empates a la mitad); NaN con una sola clase."""
    _validar(y, p)
    positivos = int(y.sum())
    negativos = len(y) - positivos
    if positivos == 0 or negativos == 0:
        return math.nan
    rangos = _rangos(p)
    suma = float(rangos[y == 1].sum())
    return (suma - positivos * (positivos + 1) / 2) / (positivos * negativos)


def brier(y: np.ndarray, p: np.ndarray) -> float:
    """Error cuadrático medio de las probabilidades; menor es mejor."""
    _validar(y, p)
    return float(np.mean((p - y) ** 2))


def brier_escalado(y: np.ndarray, p: np.ndarray) -> float:
    """1 − Brier / Brier de predecir la prevalencia; mayor es mejor; NaN con una sola clase."""
    prevalencia_ = float(np.mean(y))
    referencia = prevalencia_ * (1 - prevalencia_)
    if referencia == 0:
        return math.nan
    return 1 - brier(y, p) / referencia


def recall_en_q(y: np.ndarray, p: np.ndarray, q: float) -> float:
    """Proporción de positivos entre los ``floor(q·n)`` estudiantes de mayor probabilidad.

    Los empates en el límite se reparten en proporción: si quedan ``k`` lugares para
    ``m`` estudiantes empatados, cada uno cuenta ``k/m`` (lo esperado al desempatar al
    azar). NaN si no hay positivos.
    """
    _validar(y, p)
    if not 0 < q < 1:
        raise _invalida("q debe estar entre 0 y 1, sin incluirlos.")
    positivos = int(y.sum())
    if positivos == 0:
        return math.nan
    lugares = math.floor(q * len(y))
    if lugares == 0:
        return float(0)  # sin lugares de alerta no se alcanza a nadie
    corte = np.sort(p)[::-1][lugares - 1]
    arriba = p > corte
    empatados = p == corte
    restantes = lugares - int(arriba.sum())
    alcanzados = float(y[arriba].sum()) + float(y[empatados].sum()) * restantes / int(
        empatados.sum()
    )
    return alcanzados / positivos


def prevalencia(y: np.ndarray) -> float:
    return float(np.mean(y))


@dataclass(frozen=True)
class MatrizConfusion:
    verdaderos_positivos: int
    falsos_positivos: int
    verdaderos_negativos: int
    falsos_negativos: int

    @classmethod
    def con_umbral(cls, y: np.ndarray, p: np.ndarray, umbral: float) -> MatrizConfusion:
        """Alerta cuando la probabilidad es mayor o igual que el umbral."""
        _validar(y, p)
        alerta = p >= umbral
        return cls(
            verdaderos_positivos=int((alerta & (y == 1)).sum()),
            falsos_positivos=int((alerta & (y == 0)).sum()),
            verdaderos_negativos=int((~alerta & (y == 0)).sum()),
            falsos_negativos=int((~alerta & (y == 1)).sum()),
        )

    def accuracy(self) -> float:
        total = (
            self.verdaderos_positivos
            + self.falsos_positivos
            + self.verdaderos_negativos
            + self.falsos_negativos
        )
        return (self.verdaderos_positivos + self.verdaderos_negativos) / total

    def precision(self) -> float:
        alertas = self.verdaderos_positivos + self.falsos_positivos
        return self.verdaderos_positivos / alertas if alertas else math.nan

    def recall(self) -> float:
        positivos = self.verdaderos_positivos + self.falsos_negativos
        return self.verdaderos_positivos / positivos if positivos else math.nan

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        if math.isnan(p) or math.isnan(r) or p + r == 0:
            return math.nan
        return 2 * p * r / (p + r)


# --- Qué se calcula (DP-08a, DP-08i) y cómo se estiman los intervalos (DP-08e) ------


class MetricaProbabilidad(Enum):
    """Métricas que no necesitan umbral."""

    AUC_ROC = "auc_roc"
    BRIER = "brier"
    BRIER_ESCALADO = "brier_escalado"
    RECALL_Q = "recall_q"


MAYOR_ES_MEJOR = {
    MetricaProbabilidad.AUC_ROC: True,
    MetricaProbabilidad.BRIER: False,
    MetricaProbabilidad.BRIER_ESCALADO: True,
    MetricaProbabilidad.RECALL_Q: True,
}


class MetodoIntervalo(Enum):
    PERCENTIL = "percentil"


class Estratificacion(Enum):
    """Grupos dentro de los cuales remuestrea el bootstrap."""

    COHORTE_RESULTADO = "cohorte_resultado"
    RESULTADO = "resultado"
    NINGUNA = "ninguna"


@dataclass(frozen=True)
class DefinicionMetricas:
    metricas: tuple[MetricaProbabilidad, ...]
    q: float | None
    metodo: MetodoIntervalo
    nivel: float
    replicas: int
    estratificacion: Estratificacion

    def funcion(self, metrica: MetricaProbabilidad) -> Callable[[np.ndarray, np.ndarray], float]:
        if metrica is MetricaProbabilidad.AUC_ROC:
            return auc_roc
        if metrica is MetricaProbabilidad.BRIER:
            return brier
        if metrica is MetricaProbabilidad.BRIER_ESCALADO:
            return brier_escalado
        q = self.q
        assert q is not None
        return lambda y, p: recall_en_q(y, p, q)


def _campo(datos: Mapping[str, Any], clave: str, decision: str, donde: str) -> Any:
    if clave not in datos:
        raise _invalida(f"falta '{clave}' en {donde} ({decision}).")
    if datos[clave] is None:
        raise DecisionPendiente(decision, f"'{clave}' en {donde}")
    return datos[clave]


def definicion_metricas_desde_datos(metricas: Any, intervalos: Any) -> DefinicionMetricas:
    """Lee las secciones ``metricas`` (DP-08a, DP-08i) e ``intervalos`` (DP-08e).

    Raises:
        DecisionPendiente: si una sección o un campo vale ``null``.
        ConfiguracionInvalida: si la estructura no es válida.
    """
    if metricas is None:
        raise DecisionPendiente("DP-08a", "la sección 'metricas' de la configuración")
    if intervalos is None:
        raise DecisionPendiente("DP-08e", "la sección 'intervalos' de la configuración")
    if not isinstance(metricas, Mapping) or not isinstance(intervalos, Mapping):
        raise _invalida("'metricas' e 'intervalos' deben ser conjuntos de campos.")
    extra = sorted(set(metricas) - {"calcular", "q"}) + sorted(
        set(intervalos) - {"metodo", "nivel", "replicas", "estratificacion"}
    )
    if extra:
        raise _invalida(f"campos desconocidos: {', '.join(extra)}.")
    nombres = _campo(metricas, "calcular", "DP-08a", "metricas")
    if not isinstance(nombres, list) or not nombres:
        raise _invalida("'metricas.calcular' debe listar al menos una métrica.")
    if len(set(map(str, nombres))) != len(nombres):
        raise _invalida("'metricas.calcular' tiene métricas repetidas.")
    try:
        lista = tuple(MetricaProbabilidad(n) for n in nombres)
    except ValueError:
        opciones = ", ".join(m.value for m in MetricaProbabilidad)
        raise _invalida(f"métrica desconocida en {nombres}. Opciones: {opciones}.") from None
    q = None
    if MetricaProbabilidad.RECALL_Q in lista:
        q = _campo(metricas, "q", "DP-08i", "metricas")
        if isinstance(q, bool) or not isinstance(q, int | float) or not 0 < q < 1:
            raise _invalida("'q' debe ser un número entre 0 y 1, sin incluirlos.")
        q = float(q)
    elif "q" in metricas:
        raise _invalida("'q' solo se usa con recall_q.")
    try:
        metodo = MetodoIntervalo(_campo(intervalos, "metodo", "DP-08e", "intervalos"))
        estratificacion = Estratificacion(
            _campo(intervalos, "estratificacion", "DP-08e", "intervalos")
        )
    except ValueError:
        raise _invalida(
            "'metodo' debe ser percentil y 'estratificacion', cohorte_resultado, resultado o "
            "ninguna."
        ) from None
    nivel = _campo(intervalos, "nivel", "DP-08e", "intervalos")
    if isinstance(nivel, bool) or not isinstance(nivel, int | float) or not 0 < nivel < 1:
        raise _invalida("'nivel' debe ser un número entre 0 y 1, sin incluirlos.")
    replicas = _campo(intervalos, "replicas", "DP-08e", "intervalos")
    if isinstance(replicas, bool) or not isinstance(replicas, int) or replicas < 2:
        raise _invalida("'replicas' debe ser un entero mayor o igual que 2.")
    return DefinicionMetricas(lista, q, metodo, float(nivel), replicas, estratificacion)


# --- Bootstrap -------------------------------------------------------------------


def _grupos(
    y: np.ndarray, cohorte: Sequence[str], estratificacion: Estratificacion
) -> list[np.ndarray]:
    if estratificacion is Estratificacion.NINGUNA:
        return [np.arange(len(y))]
    claves = (
        [str(r) for r in y]
        if estratificacion is Estratificacion.RESULTADO
        else [f"{c}|{r}" for c, r in zip(cohorte, y, strict=True)]
    )
    por_clave: dict[str, list[int]] = {}
    for posicion, clave in enumerate(claves):
        por_clave.setdefault(clave, []).append(posicion)
    return [np.array(por_clave[c]) for c in sorted(por_clave)]


def remuestras(
    y: np.ndarray,
    cohorte: Sequence[str],
    estratificacion: Estratificacion,
    replicas: int,
    semilla: int,
) -> np.ndarray:
    """Índices de cada réplica (una fila por réplica): remuestreo con reemplazo de
    estudiantes dentro de cada grupo, que conserva el tamaño de cada grupo."""
    rng = np.random.default_rng(semilla)
    grupos = _grupos(y, cohorte, estratificacion)
    return np.concatenate(
        [g[rng.integers(0, len(g), size=(replicas, len(g)))] for g in grupos], axis=1
    )


@dataclass(frozen=True)
class EstimacionBootstrap:
    """Valor puntual, intervalo percentil y réplicas en que la métrica estaba definida."""

    puntual: float
    limite_inferior: float
    limite_superior: float
    replicas_validas: int


def _percentil(puntual: float, valores: np.ndarray, nivel: float) -> EstimacionBootstrap:
    validos = valores[np.isfinite(valores)]
    if math.isnan(puntual) or len(validos) == 0:
        return EstimacionBootstrap(math.nan, math.nan, math.nan, len(validos))
    alfa = (1 - nivel) / 2
    inferior, superior = np.quantile(validos, [alfa, 1 - alfa])
    return EstimacionBootstrap(puntual, float(inferior), float(superior), len(validos))


def estimar(
    funcion: Callable[[np.ndarray, np.ndarray], float],
    y: np.ndarray,
    p: np.ndarray,
    indices: np.ndarray,
    nivel: float,
) -> EstimacionBootstrap:
    """Métrica con su intervalo percentil sobre las réplicas dadas (DP-08e)."""
    valores = np.array([funcion(y[i], p[i]) for i in indices])
    return _percentil(funcion(y, p), valores, nivel)


def diferencia_pareada(
    funcion: Callable[[np.ndarray, np.ndarray], float],
    mayor_es_mejor: bool,
    y: np.ndarray,
    p_evaluada: np.ndarray,
    p_referencia: np.ndarray,
    indices: np.ndarray,
    nivel: float,
) -> EstimacionBootstrap:
    """Δ = métrica(evaluada) − métrica(referencia), orientada para que mayor sea mejor.

    Ambas configuraciones predicen a los mismos estudiantes (``y`` común) y cada réplica
    remuestrea pares de predicciones con los mismos índices (RF-M4-18, PU-24).
    """
    if p_evaluada.shape != p_referencia.shape:
        raise _invalida("las dos configuraciones deben predecir a los mismos estudiantes.")
    signo = 1 if mayor_es_mejor else -1

    def delta(i: np.ndarray | slice) -> float:
        return signo * (funcion(y[i], p_evaluada[i]) - funcion(y[i], p_referencia[i]))

    valores = np.array([delta(i) for i in indices])
    return _percentil(delta(slice(None)), valores, nivel)
