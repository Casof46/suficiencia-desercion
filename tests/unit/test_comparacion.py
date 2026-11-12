"""Evaluación comparativa frente a R0 (F3.5).

PU-22 (R0 sin compuerta), PU-23 (controles), PU-25 (no inferioridad), PU-26
(anticipación, reducción y cobertura en casos escritos a mano) y PU-27 (estados C1 a
C8). Todos los valores son sintéticos o inventados.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.comparacion import (
    ConjuntoReferencia,
    DefinicionReferencia,
    EstadoComparacion,
    EstadoNoInferioridad,
    Validez,
    anticipacion,
    clasificar_comparacion,
    clasificar_no_inferioridad,
    cobertura_temprana,
    definicion_comparacion_desde_datos,
    definicion_referencia_desde_datos,
    elegir_familia_referencia,
    escenario_mas_completo,
    reduccion_informacion,
    referentes_a_construir,
)
from suficiencia.domain.evaluacion.metricas import MetricaProbabilidad

FAMILIAS = ("lr", "rf", "xgboost", "lightgbm", "svm")
VENTANAS = ("T0", "T1", "T2", "T3")
FACTIBLES = {
    "T0|A": 1,
    "T0|A+F": 2,
    "T0|A+F+S": 3,
    "T1|A": 1,
    "T1|A+F": 2,
    "T1|A+F+S+B": 4,
    "T3|A": 1,
    "T3|A+F+S+B": 4,
}
REFERENCIA = DefinicionReferencia(
    "T3", ConjuntoReferencia.MAS_COMPLETO, MetricaProbabilidad.AUC_ROC
)


# PU-22 ---------------------------------------------------------------------------


def test_pu22_r0_elige_la_mejor_en_validacion_sin_consultar_otra_regla() -> None:
    # La familia de mayor AUC-ROC es la peor calibrada (la que no pasaría una compuerta
    # de calibración); R0 no consulta nada más que la métrica de su regla.
    auc = {"lr": 0.70, "rf": 0.72, "xgboost": 0.78, "lightgbm": 0.75, "svm": 0.71}
    assert elegir_familia_referencia(auc, FAMILIAS, mayor_es_mejor=True) == "xgboost"
    # Empates: el orden de familias del protocolo.
    empate = {"lr": 0.7, "rf": 0.8, "xgboost": 0.8, "lightgbm": 0.6, "svm": 0.8}
    assert elegir_familia_referencia(empate, FAMILIAS, mayor_es_mejor=True) == "rf"
    brier = {"lr": 0.20, "rf": 0.15, "xgboost": 0.18, "lightgbm": 0.16, "svm": 0.30}
    assert elegir_familia_referencia(brier, FAMILIAS, mayor_es_mejor=False) == "rf"
    with pytest.raises(ConfiguracionInvalida):
        elegir_familia_referencia({"lr": 0.7}, FAMILIAS, mayor_es_mejor=True)


# PU-23 ---------------------------------------------------------------------------


def test_pu23_controles_r0_fam_y_r_ven() -> None:
    assert escenario_mas_completo("T3", FACTIBLES) == "T3|A+F+S+B"
    assert escenario_mas_completo("T0", FACTIBLES) == "T0|A+F+S"
    referentes = referentes_a_construir(
        REFERENCIA, {"T1|A+F": "lr", "T0|A+F+S": "rf", "T1|A+F+S+B": "lr"}, FACTIBLES
    )
    por_codigo = {r.codigo: r for r in referentes}
    assert por_codigo["R0"].escenario == "T3|A+F+S+B"
    assert por_codigo["R0"].familia is None  # se elige con la regla de R0
    # R0-fam: el escenario de R0 con cada familia seleccionada.
    assert por_codigo["R0-fam-lr"].escenario == "T3|A+F+S+B"
    assert por_codigo["R0-fam-lr"].familia == "lr"
    assert por_codigo["R0-fam-rf"].familia == "rf"
    # R-ven solo si el seleccionado no es ya el más completo de su ventana: T1 lo
    # necesita (T1|A+F no lo es); T0 no (T0|A+F+S ya es el más completo).
    assert por_codigo["R-ven-T1"].escenario == "T1|A+F+S+B"
    assert "R-ven-T0" not in por_codigo
    # En la ventana de R0, R-ven coincidiría con R0: no se construye.
    solo_t3 = referentes_a_construir(REFERENCIA, {"T3|A": "svm"}, FACTIBLES)
    assert [r.codigo for r in solo_t3] == ["R0", "R0-fam-svm"]


def test_ventana_sin_escenarios_factibles_se_rechaza() -> None:
    with pytest.raises(ConfiguracionInvalida):
        escenario_mas_completo("T2", FACTIBLES)


# PU-25 ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("centro", "esperado"),
    [
        (0.02, EstadoNoInferioridad.DEMOSTRADA),  # todo el intervalo por encima de −δ
        (-0.05, EstadoNoInferioridad.NO_CONCLUYENTE),  # el intervalo incluye −δ
        (-0.15, EstadoNoInferioridad.PERDIDA),  # todo el intervalo por debajo de −δ
    ],
)
def test_pu25_no_inferioridad_segun_la_posicion_del_intervalo(
    centro: float, esperado: EstadoNoInferioridad
) -> None:
    replicas = centro + np.linspace(-0.03, 0.03, 201)
    resultado = clasificar_no_inferioridad(centro, replicas, margen=0.05, nivel=0.95)
    assert resultado.estado is esperado
    assert resultado.bilateral[0] <= resultado.limite_unilateral <= resultado.diferencia


def test_pu25_una_diferencia_no_significativa_nunca_es_no_inferior() -> None:
    # Diferencia puntual cero, pero intervalo ancho que incluye −δ: no concluyente.
    replicas = np.linspace(-0.2, 0.2, 401)
    resultado = clasificar_no_inferioridad(0.0, replicas, margen=0.05, nivel=0.95)
    assert resultado.estado is EstadoNoInferioridad.NO_CONCLUYENTE
    with pytest.raises(ConfiguracionInvalida):
        clasificar_no_inferioridad(0.0, np.array([np.nan]), margen=0.05, nivel=0.95)


# PU-26 ---------------------------------------------------------------------------

PERIODOS = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}


def test_pu26_anticipacion_y_reduccion_en_casos_escritos_a_mano() -> None:
    assert anticipacion("T1", "T3", PERIODOS).ventanas == 2
    assert anticipacion("T1", "T3", PERIODOS).ciclos == 2
    assert anticipacion("T3", "T3", PERIODOS).ventanas == 0
    reduccion = reduccion_informacion(
        ["A", "F"], ["A", "F", "S", "B"], ["promedio", "beca"], ["promedio", "beca", "colegio"]
    )
    assert reduccion.bloques_evitados == ("B", "S")
    assert reduccion.variables_evitadas == ("colegio",)
    assert reduccion.bloques_usados == ("A", "F")


def test_pu26_cobertura_cuenta_como_no_alertado_por_r0_a_quien_deserta_antes_de_t_ref() -> None:
    # Cuatro desertores en riesgo en t* (T1). t_ref = T3 (periodo 3).
    eventos = [2, 3, 5, 6]  # los dos primeros desertan antes de llegar en riesgo a t_ref
    seleccionada = [True, True, False, True]
    referencia = [True, True, True, True]  # R0 "alertaría" a todos si los viera
    cobertura = cobertura_temprana(eventos, seleccionada, referencia, periodo_referencia=3)
    assert cobertura.desertores == 4
    assert cobertura.seleccionada == pytest.approx(3 / 4)
    assert cobertura.referencia == pytest.approx(2 / 4)  # solo los de evento después de T3
    with pytest.raises(ConfiguracionInvalida):
        cobertura_temprana([], [], [], 3)


# PU-27 ---------------------------------------------------------------------------

VALIDA = Validez(True, True, True, True, True)
D, NC, P = (
    EstadoNoInferioridad.DEMOSTRADA,
    EstadoNoInferioridad.NO_CONCLUYENTE,
    EstadoNoInferioridad.PERDIDA,
)


@pytest.mark.parametrize(
    ("validez", "regla", "mismo", "ni", "anticipa", "esperado"),
    [
        (VALIDA, "escenario_suficiente", False, [D, D], False, EstadoComparacion.C1),
        (VALIDA, "escenario_suficiente", False, [D, D], True, EstadoComparacion.C2),
        (VALIDA, "escenario_suficiente", False, [D, NC], True, EstadoComparacion.C3),
        (VALIDA, "escenario_suficiente", False, [NC, P], True, EstadoComparacion.C4),
        (VALIDA, "ningun_escenario_cumple", False, None, False, EstadoComparacion.C5),
        (VALIDA, "empate_sin_resolver", False, None, False, EstadoComparacion.C6),
        (VALIDA, "escenario_suficiente", False, None, True, EstadoComparacion.C6),
        (VALIDA, "escenario_suficiente", True, [D, D], False, EstadoComparacion.C8),
    ],
)
def test_pu27_cada_combinacion_da_el_estado_esperado(
    validez: Validez,
    regla: str,
    mismo: bool,
    ni: list[EstadoNoInferioridad] | None,
    anticipa: bool,
    esperado: EstadoComparacion,
) -> None:
    assert clasificar_comparacion(validez, regla, mismo, ni, anticipa) is esperado


@pytest.mark.parametrize("campo", list(Validez.__dataclass_fields__))
def test_pu27_comparacion_no_valida_si_difiere_algo(campo: str) -> None:
    validez = Validez(**{**VALIDA.__dict__, campo: False})
    estado = clasificar_comparacion(validez, "escenario_suficiente", False, [D, D], True)
    assert estado is EstadoComparacion.C7
    assert validez.motivos()


def test_pu27_nunca_devuelve_superior() -> None:
    assert all("superior" not in e.value for e in EstadoComparacion)


# Configuración (DP-19, DP-20) --------------------------------------------------------

REF = {"ventana": "T3", "conjunto": "mas_completo", "metrica": "auc_roc"}
COMP = {"metricas": ["auc_roc"], "margenes": {"auc_roc": 0.05}, "nivel": 0.95}


def test_lectura_de_referencia_y_comparacion() -> None:
    assert definicion_referencia_desde_datos(REF, VENTANAS) == REFERENCIA
    assert definicion_comparacion_desde_datos(COMP).margenes == {"auc_roc": 0.05}


@pytest.mark.parametrize(
    ("datos", "decision"),
    [
        (None, "DP-19"),
        ({**REF, "ventana": None}, "DP-19a"),
        ({**REF, "conjunto": None}, "DP-19b"),
        ({**REF, "metrica": None}, "DP-19c"),
    ],
)
def test_null_en_la_referencia(datos: Any, decision: str) -> None:
    with pytest.raises(DecisionPendiente, match=decision):
        definicion_referencia_desde_datos(datos, VENTANAS)


@pytest.mark.parametrize(
    ("datos", "decision"),
    [
        (None, "DP-20"),
        ({**COMP, "metricas": None}, "DP-20a"),
        ({**COMP, "margenes": None}, "DP-20b"),
        ({**COMP, "margenes": {"auc_roc": None}}, "DP-20b"),
        ({**COMP, "nivel": None}, "DP-20d"),
    ],
)
def test_null_en_la_comparacion(datos: Any, decision: str) -> None:
    with pytest.raises(DecisionPendiente, match=decision):
        definicion_comparacion_desde_datos(datos)


@pytest.mark.parametrize(
    "datos",
    [
        {**COMP, "metricas": []},
        {**COMP, "metricas": ["precision"]},
        {**COMP, "margenes": {}},
        {**COMP, "margenes": {"auc_roc": -0.1}},
        {**COMP, "nivel": 1},
        {**COMP, "extra": 1},
    ],
)
def test_comparaciones_invalidas(datos: Any) -> None:
    with pytest.raises(ConfiguracionInvalida):
        definicion_comparacion_desde_datos(datos)


@pytest.mark.parametrize(
    "datos",
    [{**REF, "ventana": "T9"}, {**REF, "conjunto": "fijo"}, {**REF, "otro": 1}],
)
def test_referencias_invalidas(datos: Any) -> None:
    with pytest.raises(ConfiguracionInvalida):
        definicion_referencia_desde_datos(datos, VENTANAS)
