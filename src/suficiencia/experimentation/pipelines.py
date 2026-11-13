"""Preprocesamiento dentro de cada fold (M3; RF-M3-02, RF-M3-10; PI-01; F3.1).

Construye, a partir de un perfil de preprocesamiento (datos de DP-12), un
estimador de scikit-learn que se ajusta **solo** con las filas de ajuste de un
fold y después transforma calibración y validación sin volver a ajustarse. Así la
mediana del imputador o la media del escalador nunca ven filas de validación,
calibración ni prueba (PI-01).

Los tipos salen de la matriz: columnas de texto son categóricas; numéricas y
lógicas son numéricas (las lógicas valen 0 o 1).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import MissingIndicator, SimpleImputer
from sklearn.pipeline import FunctionTransformer, Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.experimentos import (
    Escalado,
    ImputacionCategorica,
    ImputacionNumerica,
    PerfilPreprocesamiento,
)

CATEGORIA_FALTANTE = "__faltante__"


@dataclass(frozen=True)
class TiposColumnas:
    numericas: tuple[str, ...]
    categoricas: tuple[str, ...]


def tipos_de_columnas(predictores: pd.DataFrame) -> TiposColumnas:
    """Separa las columnas por tipo según su tipo de pandas."""
    numericas, categoricas = [], []
    for columna in predictores.columns:
        tipo = predictores[columna].dtype
        if pd.api.types.is_bool_dtype(tipo) or pd.api.types.is_numeric_dtype(tipo):
            numericas.append(str(columna))
        else:
            categoricas.append(str(columna))
    return TiposColumnas(tuple(numericas), tuple(categoricas))


@dataclass(frozen=True)
class _ATiposSklearn:
    """Convierte los tipos de pandas con faltantes (pd.NA) a los que entiende scikit-learn.

    Es una clase del módulo, y no una función interna, para que el modelo ajustado
    se pueda guardar con joblib (F3.2).
    """

    tipos: TiposColumnas

    def __call__(self, tabla: pd.DataFrame) -> pd.DataFrame:
        # Las columnas salen en el orden de entrada: el nombre de cada salida es el de
        # su entrada ("one-to-one") y scikit-learn exige que coincidan (F4.3, D-203).
        numericas = set(self.tipos.numericas)
        categoricas = set(self.tipos.categoricas)
        columnas: dict[str, object] = {}
        for columna in tabla.columns:
            if columna in numericas:
                columnas[columna] = pd.to_numeric(
                    tabla[columna].astype("Float64"), errors="raise"
                ).to_numpy(dtype="float64", na_value=np.nan)
            elif columna in categoricas:
                columnas[columna] = (
                    tabla[columna].astype("object").where(tabla[columna].notna(), np.nan)
                )
        return pd.DataFrame(columnas, index=tabla.index)


def _a_tipos_sklearn(tipos: TiposColumnas) -> FunctionTransformer:
    return FunctionTransformer(
        _ATiposSklearn(tipos), validate=False, feature_names_out="one-to-one"
    )


def construir_preprocesador(perfil: PerfilPreprocesamiento, tipos: TiposColumnas) -> Pipeline:
    """Estimador de preprocesamiento sin ajustar, para un perfil y unas columnas."""
    transformadores: list[tuple[str, object, list[str]]] = []
    if tipos.numericas:
        pasos: list[tuple[str, object]] = [
            (
                "imputacion",
                SimpleImputer(
                    strategy="median"
                    if perfil.imputacion_numerica is ImputacionNumerica.MEDIANA
                    else "mean"
                ),
            )
        ]
        if perfil.escalado is Escalado.ESTANDAR:
            pasos.append(("escalado", StandardScaler()))
        transformadores.append(("numericas", Pipeline(pasos), list(tipos.numericas)))
        if perfil.indicador_faltante:
            transformadores.append(
                (
                    "indicadores",
                    MissingIndicator(features="missing-only", error_on_new=False),
                    list(tipos.numericas),
                )
            )
    if tipos.categoricas:
        imputador = (
            SimpleImputer(strategy="most_frequent")
            if perfil.imputacion_categorica is ImputacionCategorica.MAS_FRECUENTE
            else SimpleImputer(strategy="constant", fill_value=CATEGORIA_FALTANTE)
        )
        transformadores.append(
            (
                "categoricas",
                Pipeline(
                    [
                        ("imputacion", imputador),
                        (
                            "codificacion",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                list(tipos.categoricas),
            )
        )
    return Pipeline(
        [
            ("tipos", _a_tipos_sklearn(tipos)),
            ("columnas", ColumnTransformer(transformadores, remainder="drop")),
        ]
    )


def columnas_tras_preprocesar(
    perfil: PerfilPreprocesamiento, ajuste: pd.DataFrame, otras: Sequence[pd.DataFrame]
) -> int:
    """Ajusta el preprocesamiento solo con ``ajuste`` y transforma ``otras`` sin reajustar.

    Devuelve cuántas columnas produce. Comprueba que calibración y validación salgan
    con las mismas columnas que el ajuste (una categoría nueva no agrega columnas).

    Raises:
        ConfiguracionInvalida: si el ajuste no tiene filas o las salidas no coinciden.
    """
    if ajuste.empty:
        raise ConfiguracionInvalida(
            "Un fold no tiene filas de ajuste para el preprocesamiento.",
            "Revise las cohortes de desarrollo y la validación (DP-05, DP-07).",
        )
    preprocesador = construir_preprocesador(perfil, tipos_de_columnas(ajuste))
    ancho = int(preprocesador.fit_transform(ajuste).shape[1])
    for tabla in otras:
        if tabla.empty:
            continue
        salida = preprocesador.transform(tabla)
        if salida.shape[1] != ancho:
            raise ConfiguracionInvalida(
                "El preprocesamiento produjo columnas distintas fuera del ajuste.",
                "Es un defecto del programa; informe el caso.",
            )
    return ancho
