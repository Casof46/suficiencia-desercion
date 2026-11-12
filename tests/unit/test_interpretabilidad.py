"""Alcance de la interpretabilidad (DP-11) y agregación de las explicaciones (F3.6).

PU-21: con importancias sintéticas conocidas, la importancia de cada bloque es la
suma exacta de las de sus variables, y el explicador elegido corresponde al tipo de
modelo. Todos los valores son inventados.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.interpretabilidad import (
    AlcanceInterpretabilidad,
    Escala,
    NivelExplicacion,
    ParticionExplicacion,
    TipoExplicador,
    definicion_interpretabilidad_desde_datos,
    elegir_muestras,
    explicador_para,
    importancia_global,
    importancia_por_bloque,
    principales,
    valores_por_variable,
)

EJEMPLO = Path(__file__).resolve().parents[2] / "config/ejemplos/experimentos_ficticio.yaml"
BASE: dict[str, Any] = {
    "alcance": "todas_congeladas",
    "niveles": ["global", "bloque", "local"],
    "particion": "desarrollo",
    "muestra_fondo": 20,
    "muestra_explicar": 40,
    "kernel_muestras": 50,
    "local": {"registros": 2, "variables": 3, "lime_muestras": 100},
}
ORDEN = ["A", "F", "S", "B"]


# --- DP-11 ---------------------------------------------------------------------------


def test_lectura_del_ejemplo_y_de_una_definicion_completa() -> None:
    datos = yaml.safe_load(EJEMPLO.read_text(encoding="utf-8"))["interpretabilidad"]
    ejemplo = definicion_interpretabilidad_desde_datos(datos)
    assert ejemplo.particion is ParticionExplicacion.DESARROLLO
    definicion = definicion_interpretabilidad_desde_datos(BASE)
    assert definicion.alcance is AlcanceInterpretabilidad.TODAS_CONGELADAS
    assert definicion.niveles == (
        NivelExplicacion.GLOBAL,
        NivelExplicacion.BLOQUE,
        NivelExplicacion.LOCAL,
    )
    assert definicion.local is not None and definicion.local.lime_muestras == 100
    sin_local = {k: v for k, v in BASE.items() if k != "local"}
    solo_global = definicion_interpretabilidad_desde_datos({**sin_local, "niveles": ["global"]})
    assert solo_global.local is None


@pytest.mark.parametrize(
    "datos",
    [
        None,
        {**BASE, "alcance": None},
        {**BASE, "niveles": None},
        {**BASE, "particion": None},
        {**BASE, "muestra_fondo": None},
        {**BASE, "local": None},
        {**BASE, "local": {**BASE["local"], "registros": None}},
    ],
)
def test_un_null_detiene_con_dp_11(datos: Any) -> None:
    with pytest.raises(DecisionPendiente, match="DP-11"):
        definicion_interpretabilidad_desde_datos(datos)


@pytest.mark.parametrize(
    "datos",
    [
        [],
        {**BASE, "extra": 1},
        {**BASE, "alcance": "algunas"},
        {**BASE, "particion": "prueba"},  # sería otro acceso a la prueba
        {**BASE, "niveles": []},
        {**BASE, "niveles": ["global", "global"]},
        {**BASE, "niveles": ["bloque"]},  # el bloque sale de la importancia global
        {**BASE, "niveles": ["causal"]},
        {k: v for k, v in BASE.items() if k != "local"},
        {**BASE, "niveles": ["global"]},  # 'local' sin el nivel local
        {**BASE, "local": {**BASE["local"], "otro": 1}},
        {**BASE, "local": {**BASE["local"], "registros": 41}},
        {**BASE, "muestra_fondo": 0},
        {**BASE, "muestra_explicar": True},
        {**BASE, "kernel_muestras": 2.5},
        {k: v for k, v in BASE.items() if k != "kernel_muestras"},
    ],
)
def test_definiciones_invalidas(datos: Any) -> None:
    with pytest.raises(ConfiguracionInvalida):
        definicion_interpretabilidad_desde_datos(datos)


# --- PU-21: explicador según el modelo -----------------------------------------------


@pytest.mark.parametrize(
    ("familia", "explicador", "escala"),
    [
        ("lr", TipoExplicador.LINEAL, Escala.LOG_ODDS),
        ("rf", TipoExplicador.ARBOLES, Escala.PROBABILIDAD),
        ("xgboost", TipoExplicador.ARBOLES, Escala.LOG_ODDS),
        ("lightgbm", TipoExplicador.ARBOLES, Escala.LOG_ODDS),
        ("svm", TipoExplicador.KERNEL, Escala.MARGEN),
    ],
)
def test_pu21_el_explicador_corresponde_al_tipo_de_modelo(
    familia: str, explicador: TipoExplicador, escala: Escala
) -> None:
    assert explicador_para(familia) == (explicador, escala)


def test_familia_sin_explicador_se_rechaza() -> None:
    with pytest.raises(ConfiguracionInvalida):
        explicador_para("knn")


# --- PU-21: importancia por bloque ---------------------------------------------------


def test_pu21_bloque_es_la_suma_exacta_de_sus_variables_en_un_caso_conocido() -> None:
    importancias = {"a1": 0.25, "a2": 0.5, "f1": 0.125, "b1": 1.0}
    bloques = {"a1": "A", "a2": "A", "f1": "F", "b1": "B"}
    assert importancia_por_bloque(importancias, bloques, ORDEN) == {
        "A": 0.75,
        "F": 0.125,
        "B": 1.0,
    }


@given(
    st.lists(
        st.tuples(
            st.sampled_from(ORDEN),
            st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=30,
    )
)
def test_pu21_propiedad_suma_exacta(variables: list[tuple[str, float]]) -> None:
    importancias = {f"v{i}": valor for i, (_, valor) in enumerate(variables)}
    bloques = {f"v{i}": bloque for i, (bloque, _) in enumerate(variables)}
    resultado = importancia_por_bloque(importancias, bloques, ORDEN)
    for bloque, suma in resultado.items():
        esperado = sum(importancias[v] for v in importancias if bloques[v] == bloque)
        assert suma == esperado
    assert list(resultado) == [b for b in ORDEN if b in set(bloques.values())]


def test_variable_sin_bloque_o_bloque_desconocido_se_rechaza() -> None:
    with pytest.raises(ConfiguracionInvalida, match="sin bloque"):
        importancia_por_bloque({"a": 1.0}, {}, ORDEN)
    with pytest.raises(ConfiguracionInvalida, match="desconocidos"):
        importancia_por_bloque({"a": 1.0}, {"a": "Z"}, ORDEN)


def test_columnas_de_una_variable_se_suman_y_la_importancia_es_el_promedio_absoluto() -> None:
    # Columnas: x, indicador de x, categoría c=u, categoría c=v; y fue descartada.
    valores = np.array([[1.0, 0.5, -2.0, 1.0], [-1.0, 0.0, 0.0, -3.0]])
    por_variable = valores_por_variable(valores, ["x", "x", "c", "c"], ["x", "y", "c"])
    np.testing.assert_array_equal(por_variable, [[1.5, 0.0, -1.0], [-1.0, 0.0, -3.0]])
    assert importancia_global(por_variable, ["x", "y", "c"]) == {"x": 1.25, "y": 0.0, "c": 2.0}


def test_agregacion_con_dimensiones_o_variables_que_no_corresponden() -> None:
    with pytest.raises(ConfiguracionInvalida):
        valores_por_variable(np.zeros((2, 3)), ["x", "x"], ["x"])
    with pytest.raises(ConfiguracionInvalida, match="desconocidas"):
        valores_por_variable(np.zeros((2, 2)), ["x", "z"], ["x"])
    with pytest.raises(ConfiguracionInvalida):
        importancia_global(np.zeros((0, 1)), ["x"])


def test_principales_por_valor_absoluto_con_empates_en_orden() -> None:
    contribuciones = {"a": 0.1, "b": -0.5, "c": 0.5, "d": 0.0}
    assert principales(contribuciones, 3) == (("b", -0.5), ("c", 0.5), ("a", 0.1))


# --- RF-M5-05: muestras con semilla ---------------------------------------------------


def test_muestras_reproducibles_sin_repeticion_y_dentro_de_la_particion() -> None:
    primera = elegir_muestras(100, 20, 30, 4, semilla=7)
    assert primera == elegir_muestras(100, 20, 30, 4, semilla=7)
    assert primera != elegir_muestras(100, 20, 30, 4, semilla=8)
    assert len(set(primera.fondo)) == 20 and len(set(primera.explicar)) == 30
    assert list(primera.explicar) == sorted(primera.explicar)
    assert all(0 <= i < 100 for i in (*primera.fondo, *primera.explicar))
    assert len(primera.locales) == 4 and all(0 <= i < 30 for i in primera.locales)


def test_muestras_mayores_que_la_particion_usan_todas_las_filas() -> None:
    muestras = elegir_muestras(5, 50, 50, 10, semilla=1)
    assert muestras.fondo == muestras.explicar == (0, 1, 2, 3, 4)
    assert len(muestras.locales) == 5
    with pytest.raises(ConfiguracionInvalida):
        elegir_muestras(0, 1, 1, 0, semilla=1)
