"""Métricas, intervalos bootstrap y diferencias pareadas (F3.3).

PU-07 (las métricas propias coinciden con scikit-learn), PU-20 (el intervalo
contiene el valor puntual y se reproduce con la misma semilla, sin depender del
método que se elija en DP-08e) y PU-24 (la diferencia pareada usa exactamente los
mismos estudiantes, con la orientación de cada métrica). Los vectores son
sintéticos.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.metricas import (
    MAYOR_ES_MEJOR,
    Estratificacion,
    MatrizConfusion,
    MetricaProbabilidad,
    auc_roc,
    brier,
    brier_escalado,
    definicion_metricas_desde_datos,
    diferencia_pareada,
    estimar,
    recall_en_q,
    remuestras,
)

METRICAS = {"calcular": ["auc_roc", "brier", "brier_escalado", "recall_q"], "q": 0.2}
INTERVALOS = {
    "metodo": "percentil",
    "nivel": 0.95,
    "replicas": 200,
    "estratificacion": "cohorte_resultado",
}


def _caso(n: int = 300, semilla: int = 0) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(semilla)
    y = (rng.random(n) < 0.25).astype("int64")
    p = np.clip(0.25 + 0.2 * (y - 0.25) + rng.normal(0, 0.15, n), 0, 1)
    cohorte = [f"20{10 + i % 4}-1" for i in range(n)]
    return y, p, cohorte


# PU-07 ---------------------------------------------------------------------------

vectores = st.integers(min_value=2, max_value=60).flatmap(
    lambda n: st.tuples(
        st.lists(st.integers(0, 1), min_size=n, max_size=n),
        # Pocos valores posibles para que haya empates.
        st.lists(st.sampled_from([0.0, 0.1, 0.25, 0.5, 0.5, 0.75, 1.0]), min_size=n, max_size=n),
    )
)


@settings(max_examples=150, deadline=None)
@given(vectores)
def test_pu07_auc_y_brier_coinciden_con_scikit_learn(par: tuple[list[int], list[float]]) -> None:
    y, p = np.array(par[0]), np.array(par[1])
    assert brier(y, p) == pytest.approx(brier_score_loss(y, p))
    if len(set(par[0])) == 2:
        assert auc_roc(y, p) == pytest.approx(roc_auc_score(y, p))
    else:
        assert math.isnan(auc_roc(y, p))


@settings(max_examples=150, deadline=None)
@given(vectores, st.sampled_from([0.1, 0.25, 0.5, 0.75]))
def test_pu07_metricas_con_umbral_coinciden_con_scikit_learn(
    par: tuple[list[int], list[float]], umbral: float
) -> None:
    y, p = np.array(par[0]), np.array(par[1])
    matriz = MatrizConfusion.con_umbral(y, p, umbral)
    prediccion = (p >= umbral).astype(int)
    assert matriz.accuracy() == pytest.approx(accuracy_score(y, prediccion))
    if prediccion.sum() > 0:
        assert matriz.precision() == pytest.approx(precision_score(y, prediccion))
    else:
        assert math.isnan(matriz.precision())
    if y.sum() > 0:
        assert matriz.recall() == pytest.approx(recall_score(y, prediccion))
    if prediccion.sum() > 0 and y.sum() > 0 and (prediccion & y).sum() > 0:
        assert matriz.f1() == pytest.approx(f1_score(y, prediccion))


def test_brier_escalado_respecto_de_predecir_la_prevalencia() -> None:
    y = np.array([1, 0, 0, 0])
    assert brier_escalado(y, np.full(4, 0.25)) == pytest.approx(0.0)
    assert brier_escalado(y, y.astype(float)) == pytest.approx(1.0)
    assert brier_escalado(y, np.array([0.9, 0.2, 0.1, 0.3])) == pytest.approx(
        1 - brier(y, np.array([0.9, 0.2, 0.1, 0.3])) / (0.25 * 0.75)
    )
    assert math.isnan(brier_escalado(np.zeros(3, dtype=int), np.full(3, 0.1)))


def test_recall_en_q_con_y_sin_empates() -> None:
    y = np.array([1, 0, 1, 0, 0, 1, 0, 0, 0, 0])
    p = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0])
    # q = 0.3: 3 lugares, para 0.9, 0.8 y 0.7: 2 de los 3 positivos.
    assert recall_en_q(y, p, 0.3) == pytest.approx(2 / 3)
    assert recall_en_q(y, p, 0.05) == 0.0  # floor(0.5) = 0 lugares
    # Empate en el límite: 1 lugar para dos estudiantes con 0.9 (uno positivo).
    empate = np.array([0.9, 0.9, 0.1, 0.1])
    assert recall_en_q(np.array([1, 0, 0, 1]), empate, 0.25) == pytest.approx(0.5 * 0.5)
    assert math.isnan(recall_en_q(np.zeros(4, dtype=int), empate, 0.5))
    with pytest.raises(ConfiguracionInvalida):
        recall_en_q(y, p, 1.0)


def test_entradas_invalidas_se_rechazan() -> None:
    with pytest.raises(ConfiguracionInvalida):
        brier(np.array([0, 2]), np.array([0.1, 0.2]))
    with pytest.raises(ConfiguracionInvalida):
        brier(np.array([0, 1]), np.array([0.1, 1.2]))
    with pytest.raises(ConfiguracionInvalida):
        auc_roc(np.array([0, 1]), np.array([0.1]))


# PU-20 ---------------------------------------------------------------------------


@pytest.mark.parametrize("estratificacion", list(Estratificacion))
def test_pu20_el_intervalo_contiene_el_valor_y_se_reproduce(
    estratificacion: Estratificacion,
) -> None:
    y, p, cohorte = _caso()
    indices = remuestras(y, cohorte, estratificacion, 300, semilla=5)
    np.testing.assert_array_equal(indices, remuestras(y, cohorte, estratificacion, 300, 5))
    assert not np.array_equal(indices, remuestras(y, cohorte, estratificacion, 300, 6))
    for funcion in (auc_roc, brier, brier_escalado, lambda a, b: recall_en_q(a, b, 0.2)):
        estimacion = estimar(funcion, y, p, indices, 0.95)
        assert estimacion.limite_inferior <= estimacion.puntual <= estimacion.limite_superior
        assert estimar(funcion, y, p, indices, 0.95) == estimacion
        # Con el nivel más alto, el intervalo no se achica.
        mas_ancho = estimar(funcion, y, p, indices, 0.99)
        assert mas_ancho.limite_inferior <= estimacion.limite_inferior
        assert mas_ancho.limite_superior >= estimacion.limite_superior


def test_la_estratificacion_conserva_el_tamano_de_cada_grupo() -> None:
    y, p, cohorte = _caso()
    indices = remuestras(y, cohorte, Estratificacion.COHORTE_RESULTADO, 50, semilla=1)
    grupos = {(c, r) for c, r in zip(cohorte, y, strict=True)}
    originales = {g: sum((c, r) == g for c, r in zip(cohorte, y, strict=True)) for g in grupos}
    for replica in indices:
        contados = {g: sum((cohorte[i], y[i]) == g for i in replica) for g in grupos}
        assert contados == originales
    # Estratificar por resultado conserva los eventos en cada réplica.
    por_resultado = remuestras(y, cohorte, Estratificacion.RESULTADO, 50, semilla=1)
    assert {int(y[r].sum()) for r in por_resultado} == {int(y.sum())}


# PU-24 ---------------------------------------------------------------------------


def test_pu24_diferencia_pareada_mismos_estudiantes_y_orientacion() -> None:
    y, p, cohorte = _caso()
    rng = np.random.default_rng(3)
    p_ref = np.clip(p + rng.normal(0, 0.2, len(p)), 0, 1)
    indices = remuestras(y, cohorte, Estratificacion.COHORTE_RESULTADO, 200, semilla=2)
    # Contra sí misma, la diferencia es exactamente cero en todas las réplicas.
    cero = diferencia_pareada(auc_roc, True, y, p, p, indices, 0.95)
    assert (cero.puntual, cero.limite_inferior, cero.limite_superior) == (0.0, 0.0, 0.0)
    for metrica, funcion in (
        (MetricaProbabilidad.AUC_ROC, auc_roc),
        (MetricaProbabilidad.BRIER, brier),
        (MetricaProbabilidad.BRIER_ESCALADO, brier_escalado),
    ):
        signo = 1 if MAYOR_ES_MEJOR[metrica] else -1
        resultado = diferencia_pareada(funcion, MAYOR_ES_MEJOR[metrica], y, p, p_ref, indices, 0.95)
        assert resultado.puntual == pytest.approx(signo * (funcion(y, p) - funcion(y, p_ref)))
        # Cada réplica remuestrea pares: los mismos índices para las dos configuraciones.
        esperadas = np.array(
            [signo * (funcion(y[i], p[i]) - funcion(y[i], p_ref[i])) for i in indices]
        )
        alfa = 0.025
        assert resultado.limite_inferior == pytest.approx(np.quantile(esperadas, alfa))
        assert resultado.limite_superior == pytest.approx(np.quantile(esperadas, 1 - alfa))
    # Orientación: el Brier es menor es mejor; una referencia peor da una diferencia positiva.
    peor = np.clip(p + 0.3, 0, 1)
    assert diferencia_pareada(brier, False, y, p, peor, indices, 0.95).puntual > 0
    with pytest.raises(ConfiguracionInvalida):
        diferencia_pareada(brier, False, y, p, p[:-1], indices, 0.95)


# Configuración (DP-08a, DP-08e, DP-08i) --------------------------------------------


def test_definicion_desde_datos() -> None:
    definicion = definicion_metricas_desde_datos(METRICAS, INTERVALOS)
    assert definicion.q == 0.2
    assert definicion.replicas == 200
    assert definicion.estratificacion is Estratificacion.COHORTE_RESULTADO
    sin_recall = definicion_metricas_desde_datos({"calcular": ["auc_roc"]}, INTERVALOS)
    assert sin_recall.q is None


@pytest.mark.parametrize(
    ("seccion", "clave", "decision"),
    [
        ("metricas", None, "DP-08a"),
        ("intervalos", None, "DP-08e"),
        ("metricas", "calcular", "DP-08a"),
        ("metricas", "q", "DP-08i"),
        ("intervalos", "nivel", "DP-08e"),
        ("intervalos", "replicas", "DP-08e"),
        ("intervalos", "metodo", "DP-08e"),
        ("intervalos", "estratificacion", "DP-08e"),
    ],
)
def test_un_null_detiene_con_la_decision_pendiente(
    seccion: str, clave: str | None, decision: str
) -> None:
    datos: dict[str, Any] = {"metricas": copy.deepcopy(METRICAS), "intervalos": dict(INTERVALOS)}
    if clave is None:
        datos[seccion] = None
    else:
        datos[seccion][clave] = None
    with pytest.raises(DecisionPendiente, match=decision):
        definicion_metricas_desde_datos(datos["metricas"], datos["intervalos"])


@pytest.mark.parametrize(
    ("metricas", "intervalos"),
    [
        ({"calcular": []}, INTERVALOS),
        ({"calcular": ["auc_roc", "auc_roc"]}, INTERVALOS),
        ({"calcular": ["precision"]}, INTERVALOS),
        ({"calcular": ["recall_q"]}, INTERVALOS),  # falta q
        ({"calcular": ["recall_q"], "q": 1.5}, INTERVALOS),
        ({"calcular": ["auc_roc"], "q": 0.2}, INTERVALOS),  # q sin recall_q
        (METRICAS, {**INTERVALOS, "nivel": 1.0}),
        (METRICAS, {**INTERVALOS, "replicas": 1}),
        (METRICAS, {**INTERVALOS, "metodo": "bca"}),
        (METRICAS, {**INTERVALOS, "estratificacion": "carrera"}),
        (METRICAS, {**INTERVALOS, "extra": 1}),
    ],
)
def test_estructuras_invalidas_se_rechazan(metricas: Any, intervalos: Any) -> None:
    with pytest.raises(ConfiguracionInvalida):
        definicion_metricas_desde_datos(metricas, intervalos)
