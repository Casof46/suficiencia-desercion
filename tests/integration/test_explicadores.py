"""Explicadores SHAP y LIME sobre los modelos de las cinco familias (F3.6).

- PU-21: el explicador que se usa corresponde al tipo de modelo, con o sin calibración.
- Las contribuciones SHAP más el valor base reproducen la salida del modelo antes de
  la calibración (aditividad), y las de las columnas de una variable se suman.
- Con la misma semilla, las explicaciones son idénticas; el generador global de NumPy
  queda como estaba.

Datos inventados de forma aleatoria: nada de esto describe estudiantes reales.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.pipeline import Pipeline

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.evaluacion.interpretabilidad import explicador_para
from suficiencia.domain.experimentos import (
    Desbalance,
    Escalado,
    Familia,
    ImputacionCategorica,
    ImputacionNumerica,
    PerfilPreprocesamiento,
)
from suficiencia.experimentation.explicadores import explicar_modelo, variables_de_columnas
from suficiencia.experimentation.modelos import estimador
from suficiencia.experimentation.pipelines import construir_preprocesador, tipos_de_columnas

PERFIL = PerfilPreprocesamiento(
    "prueba",
    ImputacionNumerica.MEDIANA,
    True,
    Escalado.ESTANDAR,
    ImputacionCategorica.CATEGORIA_FALTANTE,
)
VARIABLES = ["a", "b", "d", "vacia", "c"]


@pytest.fixture(scope="module")
def datos() -> tuple[pd.DataFrame, np.ndarray]:
    generador = np.random.default_rng(3)
    n = 260
    tabla = pd.DataFrame(
        {
            "a": generador.normal(size=n),
            "b": generador.normal(size=n),
            "d": generador.normal(size=n),
            "vacia": np.full(n, np.nan),  # sin ningún valor: el imputador la descarta
            "c": pd.array(generador.choice(["x", "y", "z"], n), dtype="string"),
        }
    )
    tabla.loc[tabla.index[:25], "b"] = np.nan
    y = (tabla["a"] + (tabla["c"] == "x").astype(int) + generador.normal(size=n)) > 0.5
    return tabla, y.astype(int).to_numpy()


def _modelo(familia: Familia, calibracion: str, x: pd.DataFrame, y: np.ndarray) -> Any:
    modelo = Pipeline(
        [
            ("preprocesamiento", construir_preprocesador(PERFIL, tipos_de_columnas(x))),
            ("modelo", estimador(familia, {}, Desbalance.PESOS_CLASE, 5, y[:180])),
        ]
    )
    with pytest.warns(UserWarning, match="without any observed values"):
        modelo.fit(x[:180], y[:180])
    if calibracion != "ninguna":
        modelo = CalibratedClassifierCV(FrozenEstimator(modelo), method=calibracion)
        with pytest.warns(UserWarning):
            modelo.fit(x[180:], y[180:])
    return modelo


def _explicar(modelo: Any, familia: Familia, x: pd.DataFrame, semilla: int = 11) -> Any:
    with pytest.warns(UserWarning):
        return explicar_modelo(
            modelo, familia.value, VARIABLES, x[:40], x[100:130], [0, 5], 64, 200, semilla
        )


@pytest.mark.parametrize("calibracion", ["ninguna", "sigmoid", "isotonic"])
@pytest.mark.parametrize("familia", list(Familia))
def test_pu21_explicador_por_familia_con_aditividad_y_reproducible(
    datos: tuple[pd.DataFrame, np.ndarray], familia: Familia, calibracion: str
) -> None:
    x, y = datos
    modelo = _modelo(familia, calibracion, x, y)
    antes = np.random.get_state(legacy=False)["state"]
    explicacion = _explicar(modelo, familia, x)
    # El generador global de NumPy queda como estaba (KernelExplainer lo usa).
    despues = np.random.get_state(legacy=False)["state"]
    np.testing.assert_array_equal(despues["key"], antes["key"])
    assert despues["pos"] == antes["pos"]
    assert (explicacion.explicador, explicacion.escala) == explicador_para(familia.value)
    assert explicacion.shap.shape == (30, len(VARIABLES))
    assert explicacion.error_aditividad < 1e-5
    assert explicacion.usa_fondo is (familia.value in {"lr", "svm"})
    assert np.all(explicacion.shap[:, VARIABLES.index("vacia")] == 0)
    assert np.abs(explicacion.shap[:, VARIABLES.index("a")]).mean() > 0
    assert len(explicacion.lime) == 2 and len(explicacion.lime_ajuste) == 2
    assert set(explicacion.lime[0]) == set(VARIABLES)
    assert explicacion.lime[0]["vacia"] == 0
    # Con la misma semilla, lo mismo, aunque el generador global esté en otro estado.
    guardado = np.random.get_state()
    np.random.seed(12345)
    try:
        otra = _explicar(modelo, familia, x)
    finally:
        np.random.set_state(guardado)
    np.testing.assert_array_equal(explicacion.shap, otra.shap)
    assert explicacion.lime == otra.lime


def test_cada_columna_preprocesada_se_asocia_con_su_variable(
    datos: tuple[pd.DataFrame, np.ndarray],
) -> None:
    x, y = datos
    modelo = _modelo(Familia.LR, "ninguna", x, y)
    preprocesador = modelo.named_steps["preprocesamiento"]
    # a, b, d escaladas ('vacia' se descarta); indicadores de b y de 'vacia', que
    # tienen faltantes en el ajuste; c=x, c=y, c=z.
    esperadas = ("a", "b", "d", "b", "vacia", "c", "c", "c")
    assert variables_de_columnas(preprocesador) == esperadas
    with pytest.warns(UserWarning):
        assert preprocesador.transform(x).shape[1] == len(esperadas)


def test_modelo_de_otra_familia_o_con_otra_forma_se_rechaza(
    datos: tuple[pd.DataFrame, np.ndarray],
) -> None:
    x, y = datos
    modelo = _modelo(Familia.LR, "ninguna", x, y)
    with pytest.raises(ConfiguracionInvalida, match="familia declarada"):
        explicar_modelo(modelo, "rf", VARIABLES, x[:40], x[100:130], [], 64, 200, 1)
    with pytest.raises(ConfiguracionInvalida, match="forma esperada"):
        explicar_modelo(object(), "lr", VARIABLES, x[:40], x[100:130], [], 64, 200, 1)


def test_sin_registros_locales_no_hay_lime(datos: tuple[pd.DataFrame, np.ndarray]) -> None:
    x, y = datos
    modelo = _modelo(Familia.XGBOOST, "ninguna", x, y)
    with pytest.warns(UserWarning):
        explicacion = explicar_modelo(
            modelo, "xgboost", VARIABLES, x[:40], x[100:130], [], 64, 200, 1
        )
    assert explicacion.lime == () and explicacion.lime_ajuste == ()


def test_random_forest_con_pesos_de_clase_cumple_la_aditividad() -> None:
    """Caso en que SHAP con muestra de fondo no reproduce la salida del bosque (D-176)."""
    generador = np.random.default_rng(1)
    n = 200
    x = pd.DataFrame(
        {
            "creditos": generador.integers(0, 30, n).astype(float),
            "promedio": generador.normal(14, 3, n).round(1),
            "beca": generador.integers(0, 2, n).astype(float),
            "deuda": generador.integers(0, 2, n).astype(float),
        }
    )
    y = (x["promedio"] + generador.normal(0, 2, n) < 13).astype(int).to_numpy()
    perfil = PerfilPreprocesamiento(
        "arboles",
        ImputacionNumerica.MEDIANA,
        False,
        Escalado.NINGUNO,
        ImputacionCategorica.CATEGORIA_FALTANTE,
    )
    modelo = Pipeline(
        [
            ("preprocesamiento", construir_preprocesador(perfil, tipos_de_columnas(x))),
            (
                "modelo",
                estimador(
                    Familia.RF,
                    {"n_estimators": 30, "max_depth": 4},
                    Desbalance.PESOS_CLASE,
                    1,
                    y,
                ),
            ),
        ]
    ).fit(x, y)
    explicacion = explicar_modelo(modelo, "rf", list(x.columns), x[:50], x[100:], [], 64, 200, 1)
    assert explicacion.error_aditividad < 1e-9
