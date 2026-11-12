"""Entrenamiento de las cinco familias dentro de cada fold (M3; RF-M3-01, 04, 05, 06, 09; F3.2).

Para cada fold, con el perfil de preprocesamiento de la familia:

1. **Búsqueda** (DP-07): cada combinación de hiperparámetros se ajusta con las filas
   de ajuste y se compara en la cohorte de calibración con la métrica declarada.
   Las combinaciones son las mismas en todos los escenarios (``combinaciones_a_evaluar``).
2. **Probabilidades de SVM**: Platt por validación cruzada interna sobre el ajuste.
3. **Desbalance** (DP-06): con ``pesos_clase``, los pesos se calculan solo con las
   filas de ajuste (``class_weight="balanced"``; en XGBoost, ``scale_pos_weight``).
4. **Calibración** (DP-09): Platt o isotónica, ajustada con la cohorte de
   calibración sobre el modelo ya ajustado, que no se vuelve a ajustar.
5. **Predicción** de las filas de validación: probabilidades fuera de fold.

Todo componente aleatorio usa la semilla de la configuración y un solo hilo, para
que dos ejecuciones iguales den las mismas probabilidades (RF-M3-06, PI-11).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from xgboost import XGBClassifier

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.experimentos import (
    Calibracion,
    DefinicionBusqueda,
    Desbalance,
    Familia,
    FilasFold,
    MetricaBusqueda,
    PerfilPreprocesamiento,
    ResultadoFold,
    Valor,
)
from suficiencia.experimentation.pipelines import construir_preprocesador, tipos_de_columnas

_CLASES: dict[Familia, Any] = {
    Familia.LR: LogisticRegression,
    Familia.RF: RandomForestClassifier,
    Familia.XGBOOST: XGBClassifier,
    Familia.LIGHTGBM: LGBMClassifier,
    Familia.SVM: SVC,
}


def _fijos(familia: Familia, desbalance: Desbalance, semilla: int, y: np.ndarray) -> dict[str, Any]:
    """Parámetros que fija el programa: semilla, un hilo, probabilidades y desbalance."""
    pesos = desbalance is Desbalance.PESOS_CLASE
    if familia is Familia.LR:
        return {"random_state": semilla, "class_weight": "balanced" if pesos else None}
    if familia is Familia.RF:
        return {
            "random_state": semilla,
            "n_jobs": 1,
            "class_weight": "balanced" if pesos else None,
        }
    if familia is Familia.XGBOOST:
        positivos = int(y.sum())
        negativos = len(y) - positivos
        escala = negativos / positivos if pesos and positivos > 0 else 1.0
        return {"random_state": semilla, "n_jobs": 1, "scale_pos_weight": escala}
    if familia is Familia.LIGHTGBM:
        return {
            "random_state": semilla,
            "n_jobs": 1,
            "deterministic": True,
            "force_row_wise": True,
            "verbose": -1,
            "class_weight": "balanced" if pesos else None,
        }
    return {"random_state": semilla, "class_weight": "balanced" if pesos else None}


def estimador(
    familia: Familia,
    parametros: Mapping[str, Valor],
    desbalance: Desbalance,
    semilla: int,
    y_ajuste: np.ndarray,
) -> Any:
    """Estimador sin ajustar de una familia con sus hiperparámetros.

    Raises:
        ConfiguracionInvalida: si un hiperparámetro no existe en esa familia.
    """
    clase = _CLASES[familia]
    validos = set(clase().get_params())
    desconocidos = sorted(set(parametros) - validos)
    if desconocidos:
        raise ConfiguracionInvalida(
            f"La familia '{familia.value}' no tiene los hiperparámetros: "
            f"{', '.join(desconocidos)}.",
            "Use los nombres de la biblioteca correspondiente en 'modelos.<familia>.espacio'.",
        )
    base = clase(**dict(parametros), **_fijos(familia, desbalance, semilla, y_ajuste))
    if familia is Familia.SVM:
        # SVC no da probabilidades por sí mismo: se obtienen con Platt por validación
        # cruzada interna sobre las filas de ajuste, sin promediar modelos. Es lo que
        # hacía ``SVC(probability=True)``, obsoleto desde scikit-learn 1.9 (D-139).
        return CalibratedClassifierCV(base, method="sigmoid", ensemble=False)
    return base


def _puntaje(metrica: MetricaBusqueda, y: np.ndarray, p: np.ndarray) -> float:
    """Puntaje de búsqueda en la cohorte de calibración; mayor es mejor."""
    if metrica is MetricaBusqueda.AUC_ROC:
        return float(roc_auc_score(y, p))
    return -float(log_loss(y, p, labels=[0, 1]))


def _positivas(modelo: Any, x: pd.DataFrame) -> np.ndarray:
    return np.asarray(modelo.predict_proba(x)[:, 1], dtype="float64")


def _ajustar(
    familia: Familia,
    perfil: PerfilPreprocesamiento,
    tipos: Any,
    combinaciones: Sequence[Mapping[str, Valor]],
    busqueda: DefinicionBusqueda,
    desbalance: Desbalance,
    calibracion: Calibracion,
    semilla: int,
    x_aj: pd.DataFrame,
    y_aj: np.ndarray,
    x_cal: pd.DataFrame,
    y_cal: np.ndarray,
) -> tuple[float | None, Mapping[str, Valor], Any]:
    """Búsqueda en la cohorte de calibración y, si corresponde, calibración del elegido."""
    mejor: tuple[float | None, Mapping[str, Valor], Any] | None = None
    for combinacion in combinaciones:
        modelo = Pipeline(
            [
                ("preprocesamiento", construir_preprocesador(perfil, tipos)),
                ("modelo", estimador(familia, combinacion, desbalance, semilla, y_aj)),
            ]
        )
        modelo.fit(x_aj, y_aj)
        puntaje = (
            _puntaje(busqueda.metrica, y_cal, _positivas(modelo, x_cal))
            if len(combinaciones) > 1
            else None
        )
        # Empates: gana la primera combinación en el orden de la malla.
        if mejor is None or (puntaje is not None and mejor[0] is not None and puntaje > mejor[0]):
            mejor = (puntaje, combinacion, modelo)
    assert mejor is not None
    puntaje, combinacion, modelo = mejor
    if calibracion is not Calibracion.NINGUNA:
        metodo = "sigmoid" if calibracion is Calibracion.PLATT else "isotonic"
        modelo = CalibratedClassifierCV(FrozenEstimator(modelo), method=metodo).fit(x_cal, y_cal)
    return puntaje, combinacion, modelo


def _necesita_calibracion(
    combinaciones: Sequence[Mapping[str, Valor]], calibracion: Calibracion
) -> bool:
    return len(combinaciones) > 1 or calibracion is not Calibracion.NINGUNA


def entrenar_en_folds(
    familia: Familia,
    perfil: PerfilPreprocesamiento,
    combinaciones: Sequence[Mapping[str, Valor]],
    busqueda: DefinicionBusqueda,
    desbalance: Desbalance,
    calibracion: Calibracion,
    semilla: int,
    predictores: pd.DataFrame,
    objetivo: pd.Series,
    folds: Sequence[FilasFold],
) -> list[ResultadoFold]:
    """Entrena una familia en cada fold; ver el docstring del módulo.

    Raises:
        ConfiguracionInvalida: si falta la cohorte de calibración cuando se necesita,
            o un fold no tiene filas de ajuste o de validación.
    """
    y_total = objetivo.to_numpy(dtype="int64")
    tipos = tipos_de_columnas(predictores)
    resultados = []
    for fold in folds:
        if not fold.ajuste or not fold.validacion:
            raise ConfiguracionInvalida(
                f"El fold {fold.numero} no tiene filas de ajuste o de validación.",
                "Revise las cohortes de desarrollo y la validación (DP-05, DP-07).",
            )
        if _necesita_calibracion(combinaciones, calibracion) and not fold.calibracion:
            raise ConfiguracionInvalida(
                f"El fold {fold.numero} no tiene filas en la cohorte de calibración.",
                "La búsqueda y la calibración la necesitan (DP-07, DP-09).",
            )
        x_aj, y_aj = predictores.iloc[list(fold.ajuste)], y_total[list(fold.ajuste)]
        x_cal, y_cal = predictores.iloc[list(fold.calibracion)], y_total[list(fold.calibracion)]
        x_val = predictores.iloc[list(fold.validacion)]
        puntaje, combinacion, modelo = _ajustar(
            familia,
            perfil,
            tipos,
            combinaciones,
            busqueda,
            desbalance,
            calibracion,
            semilla,
            x_aj,
            y_aj,
            x_cal,
            y_cal,
        )
        resultados.append(
            ResultadoFold(
                numero=fold.numero,
                combinacion=dict(combinacion),
                puntaje_busqueda=puntaje,
                configuraciones_evaluadas=len(combinaciones),
                probabilidades=tuple(float(p) for p in _positivas(modelo, x_val)),
                modelo=modelo,
            )
        )
    return resultados


def ajustar_final(
    familia: Familia,
    perfil: PerfilPreprocesamiento,
    combinaciones: Sequence[Mapping[str, Valor]],
    busqueda: DefinicionBusqueda,
    desbalance: Desbalance,
    calibracion: Calibracion,
    semilla: int,
    predictores: pd.DataFrame,
    objetivo: pd.Series,
    ajuste: Sequence[int],
    calibracion_filas: Sequence[int],
) -> ResultadoFold:
    """Ajuste final con todo el desarrollo (DP-10, ``todo_desarrollo``; F3.4).

    Mismo procedimiento que en cada fold, sin filas de validación: las filas de
    ``calibracion_filas`` (la última cohorte de desarrollo) sirven para la búsqueda y
    la calibración; si no hacen falta, se ajusta con todas las filas.
    """
    y_total = objetivo.to_numpy(dtype="int64")
    filas_ajuste = list(ajuste)
    if not _necesita_calibracion(combinaciones, calibracion):
        filas_ajuste = sorted({*ajuste, *calibracion_filas})
    elif not calibracion_filas:
        raise ConfiguracionInvalida(
            "El ajuste final no tiene filas para la búsqueda o la calibración.",
            "La búsqueda y la calibración necesitan la última cohorte de desarrollo.",
        )
    puntaje, combinacion, modelo = _ajustar(
        familia,
        perfil,
        tipos_de_columnas(predictores),
        combinaciones,
        busqueda,
        desbalance,
        calibracion,
        semilla,
        predictores.iloc[filas_ajuste],
        y_total[filas_ajuste],
        predictores.iloc[list(calibracion_filas)],
        y_total[list(calibracion_filas)],
    )
    return ResultadoFold(
        numero=0,
        combinacion=dict(combinacion),
        puntaje_busqueda=puntaje,
        configuraciones_evaluadas=len(combinaciones),
        probabilidades=(),
        modelo=modelo,
    )


def predecir(modelo: Any, predictores: pd.DataFrame) -> np.ndarray:
    """Probabilidad de la clase positiva con un modelo ya ajustado (evaluación final)."""
    return _positivas(modelo, predictores)
