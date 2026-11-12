"""Explicadores SHAP y LIME de un modelo congelado (M5; RF-M5-01 a 03; F3.6).

Un modelo congelado es el preprocesamiento seguido del estimador, y a veces envuelto
en la calibración (DP-09). Se explica la **salida del estimador antes de la
calibración**, en el espacio de las columnas preprocesadas:

- regresión logística: ``LinearExplainer`` (log-odds);
- Random Forest, XGBoost y LightGBM: ``TreeExplainer`` con las coberturas de los
  propios árboles, sin muestra de fondo (probabilidad en Random Forest; log-odds en
  XGBoost y LightGBM);
- SVM: ``KernelExplainer`` con la muestra de fondo sobre el margen de la SVC.

Las contribuciones de las columnas de una misma variable (columnas 0/1 de una
categoría, indicador de faltante) se suman para obtener la de la variable. LIME
ajusta un modelo lineal local alrededor de cada registro con la probabilidad del
mismo estimador; sus pesos también se suman por variable.

Toda la aleatoriedad usa la semilla de la configuración. ``KernelExplainer`` usa el
generador global de NumPy: se fija la semilla y después se restaura el estado.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.evaluacion.interpretabilidad import (
    Escala,
    TipoExplicador,
    explicador_para,
    valores_por_variable,
)


@dataclass(frozen=True)
class ExplicacionModelo:
    """Contribuciones de un modelo, ya sumadas por variable."""

    explicador: TipoExplicador
    escala: Escala
    valor_base: float
    shap: np.ndarray
    """Filas explicadas × variables: contribución SHAP de cada variable."""
    error_aditividad: float
    """Máximo de |valor base + suma de contribuciones − salida del modelo|."""
    usa_fondo: bool
    """Si SHAP usó la muestra de fondo (el de árboles no la usa; LIME, siempre)."""
    lime: tuple[dict[str, float], ...]
    """Por registro local, el peso LIME de cada variable."""
    lime_ajuste: tuple[float, ...]
    """Por registro local, el R² del modelo lineal local de LIME."""


def _pipeline(modelo: Any) -> Pipeline:
    """El preprocesamiento y el estimador, sin la calibración."""
    if isinstance(modelo, CalibratedClassifierCV) and hasattr(modelo, "calibrated_classifiers_"):
        interno = modelo.calibrated_classifiers_[0].estimator
        modelo = getattr(interno, "estimator", interno)  # FrozenEstimator
    if not (
        isinstance(modelo, Pipeline)
        and "preprocesamiento" in modelo.named_steps
        and "modelo" in modelo.named_steps
    ):
        raise ConfiguracionInvalida(
            "El modelo congelado no tiene la forma esperada (preprocesamiento y estimador).",
            "Es un defecto del programa o el archivo no es un modelo de este proyecto.",
        )
    return modelo


def variables_de_columnas(preprocesador: Pipeline) -> tuple[str, ...]:
    """Variable original de cada columna que produce el preprocesamiento ajustado."""
    columnas: ColumnTransformer = preprocesador.named_steps["columnas"]
    salida: list[str] = []
    for nombre, transformador, variables in columnas.transformers_:
        if nombre == "remainder" or transformador == "drop":
            continue
        variables = list(variables)
        if nombre == "numericas":
            # El imputador descarta las variables sin ningún valor en el ajuste.
            imputador = transformador.named_steps["imputacion"]
            salida.extend(str(v) for v in imputador.get_feature_names_out(variables))
        elif nombre == "indicadores":
            salida.extend(variables[i] for i in transformador.features_)
        elif nombre == "categoricas":
            codificador = transformador.named_steps["codificacion"]
            imputador = transformador.named_steps["imputacion"]
            conservadas = [str(v) for v in imputador.get_feature_names_out(variables)]
            for variable, categorias in zip(conservadas, codificador.categories_, strict=True):
                salida.extend([variable] * len(categorias))
        else:
            raise ConfiguracionInvalida(
                f"El preprocesamiento tiene una parte desconocida: {nombre}.",
                "Es un defecto del programa; informe el caso.",
            )
    return tuple(salida)


def _binarias(variables_columna: Sequence[str], preprocesador: Pipeline) -> list[int]:
    """Columnas 0/1 (indicadores y categorías), que LIME trata como categóricas."""
    columnas: ColumnTransformer = preprocesador.named_steps["columnas"]
    inicio = 0
    binarias: list[int] = []
    for nombre, transformador, variables in columnas.transformers_:
        if nombre == "remainder" or transformador == "drop":
            continue
        if nombre == "numericas":
            ancho = len(transformador.named_steps["imputacion"].get_feature_names_out(variables))
        elif nombre == "indicadores":
            ancho = len(transformador.features_)
        else:
            ancho = sum(len(c) for c in transformador.named_steps["codificacion"].categories_)
        if nombre != "numericas":
            binarias.extend(range(inicio, inicio + ancho))
        inicio += ancho
    if inicio != len(variables_columna):  # pragma: no cover - protección
        raise ConfiguracionInvalida(
            "No se pudo asociar cada columna preprocesada con su variable.",
            "Es un defecto del programa; informe el caso.",
        )
    return binarias


_ESTIMADORES = {
    "lr": "LogisticRegression",
    "rf": "RandomForestClassifier",
    "xgboost": "XGBClassifier",
    "lightgbm": "LGBMClassifier",
    "svm": "CalibratedClassifierCV",  # SVC con Platt interno (D-139)
}


def _comprobar_tipo(estimador: Any, familia: str) -> None:
    """El estimador debe ser el de la familia declarada: si no, el explicador no corresponde."""
    if type(estimador).__name__ != _ESTIMADORES[familia]:
        raise ConfiguracionInvalida(
            f"El modelo congelado no es de la familia declarada ({familia}): "
            f"es {type(estimador).__name__}.",
            "Revise que la configuración congelada y su archivo de modelo correspondan.",
        )


def _shap(
    explicador: TipoExplicador,
    familia: str,
    estimador: Any,
    fondo: np.ndarray,
    explicar: np.ndarray,
    kernel_muestras: int,
    semilla: int,
) -> tuple[np.ndarray, float, np.ndarray]:
    """Contribuciones por columna, valor base y salida del modelo explicada."""
    import shap

    if explicador is TipoExplicador.LINEAL:
        lineal = shap.LinearExplainer(estimador, fondo)
        valores = lineal.shap_values(explicar)
        base = lineal.expected_value
        salida = estimador.decision_function(explicar)
    elif explicador is TipoExplicador.ARBOLES:
        # Con las coberturas de los árboles (exacto). La variante con muestra de fondo
        # no cumplió la aditividad con algunos Random Forest sintéticos (D-176).
        arboles = shap.TreeExplainer(
            estimador, feature_perturbation="tree_path_dependent", model_output="raw"
        )
        valores = arboles.shap_values(explicar)
        base = arboles.expected_value
        if familia == "rf":
            salida = estimador.predict_proba(explicar)[:, 1]
        elif familia == "xgboost":
            salida = estimador.predict(explicar, output_margin=True)
        else:
            salida = estimador.predict(explicar, raw_score=True)
    else:
        svc = estimador.calibrated_classifiers_[0].estimator
        if not isinstance(svc, SVC):
            raise ConfiguracionInvalida(
                "El modelo SVM congelado no tiene una SVC dentro.",
                "Revise que la configuración congelada y su archivo de modelo correspondan.",
            )
        kernel = shap.KernelExplainer(svc.decision_function, fondo)
        estado = np.random.get_state()
        np.random.seed(semilla)
        try:
            valores = kernel.shap_values(explicar, nsamples=kernel_muestras, silent=True)
        finally:
            np.random.set_state(estado)
        base = kernel.expected_value
        salida = svc.decision_function(explicar)
    matriz = np.asarray(valores, dtype="float64")
    base_arreglo = np.asarray(base, dtype="float64").reshape(-1)
    if matriz.ndim == 3:  # una salida por clase (Random Forest): la positiva
        matriz = matriz[..., 1]
        base_arreglo = base_arreglo[1:]
    return matriz, float(base_arreglo[0]), np.asarray(salida, dtype="float64").reshape(-1)


def _lime(
    estimador: Any,
    fondo: np.ndarray,
    registros: np.ndarray,
    binarias: list[int],
    variables_columna: Sequence[str],
    variables: Sequence[str],
    muestras: int,
    semilla: int,
) -> tuple[tuple[dict[str, float], ...], tuple[float, ...]]:
    from lime.lime_tabular import LimeTabularExplainer

    nombres = [f"c{i}" for i in range(fondo.shape[1])]
    pesos_por_registro = []
    ajustes = []
    for registro in registros:
        explicador = LimeTabularExplainer(
            fondo,
            mode="classification",
            feature_names=nombres,
            categorical_features=binarias,
            discretize_continuous=True,
            random_state=semilla,
        )
        explicacion = explicador.explain_instance(
            registro,
            estimador.predict_proba,
            labels=(1,),
            num_features=fondo.shape[1],
            num_samples=muestras,
        )
        pesos_columna = np.zeros((1, fondo.shape[1]), dtype="float64")
        for columna, peso in explicacion.as_map()[1]:
            pesos_columna[0, int(columna)] = float(peso)
        por_variable = valores_por_variable(pesos_columna, variables_columna, variables)[0]
        pesos_por_registro.append({v: float(por_variable[i]) for i, v in enumerate(variables)})
        ajustes.append(float(explicacion.score))
    return tuple(pesos_por_registro), tuple(ajustes)


def explicar_modelo(
    modelo: Any,
    familia: str,
    variables: Sequence[str],
    fondo: pd.DataFrame,
    explicar: pd.DataFrame,
    locales: Sequence[int],
    kernel_muestras: int,
    lime_muestras: int,
    semilla: int,
) -> ExplicacionModelo:
    """Explicaciones SHAP de ``explicar`` y LIME de sus filas ``locales``.

    Raises:
        ConfiguracionInvalida: si el modelo no tiene la forma esperada o no es de la
            familia declarada.
    """
    explicador, escala = explicador_para(familia)
    pipeline = _pipeline(modelo)
    preprocesador = pipeline.named_steps["preprocesamiento"]
    estimador = pipeline.named_steps["modelo"]
    _comprobar_tipo(estimador, familia)
    variables_columna = variables_de_columnas(preprocesador)
    z_fondo = np.asarray(preprocesador.transform(fondo), dtype="float64")
    z_explicar = np.asarray(preprocesador.transform(explicar), dtype="float64")
    with warnings.catch_warnings():
        # Avisos de las bibliotecas sobre nombres de columnas: las columnas
        # preprocesadas no tienen nombres y el orden es siempre el del ajuste.
        warnings.filterwarnings("ignore", message=".*feature names.*")
        por_columna, base, salida = _shap(
            explicador, familia, estimador, z_fondo, z_explicar, kernel_muestras, semilla
        )
        lime, ajustes = (
            _lime(
                estimador,
                z_fondo,
                z_explicar[list(locales)],
                _binarias(variables_columna, preprocesador),
                variables_columna,
                variables,
                lime_muestras,
                semilla,
            )
            if locales
            else ((), ())
        )
    por_variable = valores_por_variable(por_columna, variables_columna, variables)
    error = float(np.max(np.abs(base + por_columna.sum(axis=1) - salida)))
    return ExplicacionModelo(
        explicador=explicador,
        escala=escala,
        valor_base=base,
        shap=por_variable,
        error_aditividad=error,
        usa_fondo=explicador is not TipoExplicador.ARBOLES,
        lime=lime,
        lime_ajuste=ajustes,
    )
