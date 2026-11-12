"""Selección del modelo representativo y del umbral (F3.4).

RF-M4-08 (regla de selección como dato, DP-10) y RF-M4-07 (umbral con validación,
DP-06). Los valores son sintéticos.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.metricas import MetricaProbabilidad
from suficiencia.domain.evaluacion.seleccion import (
    DefinicionSeleccion,
    DefinicionUmbral,
    Reentrenamiento,
    ReglaUmbral,
    definicion_seleccion_desde_datos,
    definicion_umbral_desde_datos,
    elegir_umbral,
    seleccionar_familia,
)
from suficiencia.domain.experimentos import configuracion_experimentos_desde_datos
from suficiencia.persistence.protocolo_yaml import leer_yaml

FAMILIAS = ("lr", "rf", "xgboost", "lightgbm", "svm")
EJEMPLO = Path(__file__).resolve().parents[2] / "config/ejemplos/experimentos_ficticio.yaml"


def _regla(metrica: MetricaProbabilidad, margen: float) -> DefinicionSeleccion:
    return DefinicionSeleccion(metrica, margen, FAMILIAS, Reentrenamiento.ULTIMO_FOLD)


def test_sin_margen_gana_la_mejor_y_con_margen_la_primera_del_orden() -> None:
    valores = {"lr": 0.70, "rf": 0.74, "xgboost": 0.73, "lightgbm": 0.60, "svm": 0.745}
    assert seleccionar_familia(valores, _regla(MetricaProbabilidad.AUC_ROC, 0)) == "svm"
    # Con margen 0,02, quedan rf, xgboost y svm: gana rf, la primera del orden.
    assert seleccionar_familia(valores, _regla(MetricaProbabilidad.AUC_ROC, 0.02)) == "rf"
    assert seleccionar_familia(valores, _regla(MetricaProbabilidad.AUC_ROC, 0.05)) == "lr"


def test_en_las_metricas_donde_menor_es_mejor_se_invierte_la_orientacion() -> None:
    brier = {"lr": 0.20, "rf": 0.15, "xgboost": 0.18, "lightgbm": 0.16, "svm": 0.30}
    assert seleccionar_familia(brier, _regla(MetricaProbabilidad.BRIER, 0)) == "rf"
    assert seleccionar_familia(brier, _regla(MetricaProbabilidad.BRIER, 0.03)) == "rf"
    assert seleccionar_familia(brier, _regla(MetricaProbabilidad.BRIER, 0.05)) == "lr"


def test_faltan_familias_o_valores_no_definidos() -> None:
    with pytest.raises(ConfiguracionInvalida, match="svm"):
        seleccionar_familia(
            {"lr": 0.7, "rf": 0.7, "xgboost": 0.7, "lightgbm": 0.7},
            _regla(MetricaProbabilidad.AUC_ROC, 0),
        )
    with pytest.raises(ConfiguracionInvalida):
        seleccionar_familia(
            {"lr": math.nan, "rf": 0.7, "xgboost": 0.7, "lightgbm": 0.7, "svm": 0.7},
            _regla(MetricaProbabilidad.AUC_ROC, 0),
        )


def _validacion() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(4)
    y = (rng.random(400) < 0.25).astype("int64")
    p = np.clip(0.25 + 0.2 * (y - 0.25) + rng.normal(0, 0.15, 400), 0, 1)
    return y, p


def test_umbral_fijo_cuantil_y_recall_minimo() -> None:
    y, p = _validacion()
    assert elegir_umbral(y, p, DefinicionUmbral(ReglaUmbral.FIJO, 0.3), None) == 0.3
    umbral = elegir_umbral(y, p, DefinicionUmbral(ReglaUmbral.CUANTIL_Q, None), 0.2)
    assert np.mean(p >= umbral) == pytest.approx(0.2, abs=0.01)
    corte = elegir_umbral(y, p, DefinicionUmbral(ReglaUmbral.RECALL_MINIMO, 0.6), None)
    recall = np.mean(p[y == 1] >= corte)
    assert recall >= 0.6
    # Es el mayor umbral que lo cumple: cualquier umbral apenas mayor ya no alcanza.
    siguiente = np.min(p[y == 1][p[y == 1] > corte])
    assert np.mean(p[y == 1] >= siguiente) < 0.6


def test_recall_minimo_sin_positivos_se_rechaza() -> None:
    with pytest.raises(ConfiguracionInvalida):
        elegir_umbral(
            np.zeros(5, dtype="int64"),
            np.full(5, 0.2),
            DefinicionUmbral(ReglaUmbral.RECALL_MINIMO, 0.5),
            None,
        )


SELECCION = {
    "metrica": "auc_roc",
    "margen": 0.01,
    "orden_familias": list(FAMILIAS),
    "reentrenamiento": "todo_desarrollo",
}


def test_lectura_de_la_seleccion_y_del_umbral() -> None:
    definicion = definicion_seleccion_desde_datos(SELECCION, FAMILIAS)
    assert definicion.reentrenamiento is Reentrenamiento.TODO_DESARROLLO
    assert definicion_umbral_desde_datos({"regla": "cuantil_q"}, 0.2).regla is ReglaUmbral.CUANTIL_Q
    assert definicion_umbral_desde_datos({"regla": "fijo", "valor": 0.4}, None).valor == 0.4


@pytest.mark.parametrize("clave", list(SELECCION))
def test_un_null_en_la_seleccion_detiene_con_dp10(clave: str) -> None:
    with pytest.raises(DecisionPendiente, match="DP-10"):
        definicion_seleccion_desde_datos({**SELECCION, clave: None}, FAMILIAS)


def test_null_y_q_faltante_en_el_umbral() -> None:
    with pytest.raises(DecisionPendiente, match="DP-10"):
        definicion_seleccion_desde_datos(None, FAMILIAS)
    with pytest.raises(DecisionPendiente, match="DP-06"):
        definicion_umbral_desde_datos(None, 0.2)
    with pytest.raises(DecisionPendiente, match="DP-06"):
        definicion_umbral_desde_datos({"regla": "fijo", "valor": None}, None)
    with pytest.raises(DecisionPendiente, match="DP-08i"):
        definicion_umbral_desde_datos({"regla": "cuantil_q"}, None)


@pytest.mark.parametrize(
    "cambio",
    [
        {"metrica": "precision"},
        {"margen": -0.1},
        {"margen": True},
        {"orden_familias": ["lr", "rf"]},
        {"orden_familias": ["lr", "lr", "xgboost", "lightgbm", "svm"]},
        {"reentrenamiento": "nunca"},
        {"extra": 1},
    ],
)
def test_selecciones_invalidas(cambio: dict[str, Any]) -> None:
    with pytest.raises(ConfiguracionInvalida):
        definicion_seleccion_desde_datos({**SELECCION, **cambio}, FAMILIAS)


@pytest.mark.parametrize(
    "datos",
    [
        {"regla": "optimo"},
        {"regla": "fijo"},
        {"regla": "fijo", "valor": 1.5},
        {"regla": "cuantil_q", "valor": 0.2},
        {"regla": "recall_minimo", "valor": "alto"},
        {"regla": "fijo", "valor": 0.3, "extra": 1},
    ],
)
def test_umbrales_invalidos(datos: dict[str, Any]) -> None:
    with pytest.raises(ConfiguracionInvalida):
        definicion_umbral_desde_datos(datos, 0.2)


def test_el_ejemplo_declara_seleccion_y_umbral_y_exige_q_para_recall_q() -> None:
    datos = leer_yaml(EJEMPLO)
    configuracion = configuracion_experimentos_desde_datos(datos)
    assert configuracion.seleccion.orden_familias == FAMILIAS
    assert configuracion.umbral.regla is ReglaUmbral.CUANTIL_Q
    for clave, decision in (("seleccion", "DP-10"), ("umbral", "DP-06")):
        otro = copy.deepcopy(datos)
        otro[clave] = None
        with pytest.raises(DecisionPendiente, match=decision):
            configuracion_experimentos_desde_datos(otro)
    sin_q = copy.deepcopy(datos)
    sin_q["metricas"] = {"calcular": ["auc_roc"]}
    sin_q["umbral"] = {"regla": "fijo", "valor": 0.3}
    sin_q["seleccion"]["metrica"] = "recall_q"
    with pytest.raises(DecisionPendiente, match="DP-08i"):
        configuracion_experimentos_desde_datos(sin_q)
