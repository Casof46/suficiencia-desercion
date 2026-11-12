"""Configuración de experimentos y folds cronológicos (F3.1); modelos y búsqueda (F3.2).

PI-07 (parte de los folds): en cada fold, la cohorte de validación es posterior a
todas las de ajuste y calibración, y ninguna cohorte está en dos papeles. DP-07 y
DP-12 entran como datos obligatorios: un ``null`` detiene el programa con la
decisión pendiente. El ejemplo del repositorio es ficticio.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.experimentos import (
    Calibracion,
    DefinicionBusqueda,
    DefinicionValidacion,
    Desbalance,
    Escalado,
    Esquema,
    Familia,
    ImputacionCategorica,
    ImputacionNumerica,
    MetodoBusqueda,
    MetricaBusqueda,
    ModeloFamilia,
    combinaciones_a_evaluar,
    configuracion_experimentos_desde_datos,
    construir_folds,
)
from suficiencia.persistence.experimentos_yaml import cargar_configuracion_experimentos

EJEMPLO = Path(__file__).resolve().parents[2] / "config" / "ejemplos" / "experimentos_ficticio.yaml"
DESARROLLO = tuple(f"{a}-{s}" for a in range(2010, 2014) for s in (1, 2))


def _datos() -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load(EJEMPLO.read_text(encoding="utf-8"))
    return datos


def test_el_ejemplo_es_ficticio_y_se_lee_completo() -> None:
    texto = EJEMPLO.read_text(encoding="utf-8")
    assert "EJEMPLO FICTICIO" in texto
    configuracion = cargar_configuracion_experimentos(EJEMPLO)
    assert configuracion.ficticio
    assert configuracion.validacion == DefinicionValidacion(Esquema.EXPANSIVO, 2, True, None)
    assert set(configuracion.perfiles) == {"lineal", "arboles"}
    lineal = configuracion.perfiles["lineal"]
    assert lineal.imputacion_numerica is ImputacionNumerica.MEDIANA
    assert lineal.escalado is Escalado.ESTANDAR
    assert lineal.imputacion_categorica is ImputacionCategorica.CATEGORIA_FALTANTE
    assert configuracion.perfiles["arboles"].escalado is Escalado.NINGUNO


def test_sin_el_archivo_del_proyecto_se_detiene_con_dp07(tmp_path: Path) -> None:
    with pytest.raises(DecisionPendiente, match="DP-07"):
        cargar_configuracion_experimentos(tmp_path / "config" / "experimentos.yaml")


def test_folds_del_ejemplo_como_en_el_informe_del_oe3() -> None:
    folds = construir_folds(DESARROLLO, DefinicionValidacion(Esquema.EXPANSIVO, 2, True, None))
    assert len(folds) == 6
    assert folds[0].ajuste == ("2010-1",)
    assert folds[0].calibracion == ("2010-2",)
    assert folds[0].validacion == "2011-1"
    assert folds[-1].ajuste == DESARROLLO[:6]
    assert folds[-1].calibracion == ("2013-1",)
    assert folds[-1].validacion == "2013-2"


def test_deslizante_usa_solo_las_ultimas_cohortes_de_ajuste() -> None:
    folds = construir_folds(DESARROLLO, DefinicionValidacion(Esquema.DESLIZANTE, 3, False, 2))
    assert [f.ajuste for f in folds[:2]] == [("2010-2", "2011-1"), ("2011-1", "2011-2")]
    assert all(f.calibracion == () for f in folds)
    assert [f.validacion for f in folds] == list(DESARROLLO[3:])


@given(
    cantidad=st.integers(min_value=2, max_value=14),
    iniciales=st.integers(min_value=1, max_value=6),
    calibracion=st.booleans(),
    deslizante=st.booleans(),
    ancho=st.integers(min_value=1, max_value=5),
    desordenar=st.randoms(use_true_random=False),
)
def test_pi07_validacion_siempre_posterior_y_papeles_disjuntos(
    cantidad: int,
    iniciales: int,
    calibracion: bool,
    deslizante: bool,
    ancho: int,
    desordenar: Any,
) -> None:
    cohortes = [f"{2000 + i // 2}-{i % 2 + 1}" for i in range(cantidad)]
    try:
        definicion = DefinicionValidacion(
            Esquema.DESLIZANTE if deslizante else Esquema.EXPANSIVO,
            iniciales,
            calibracion,
            ancho if deslizante else None,
        )
        entrada = list(cohortes)
        desordenar.shuffle(entrada)
        folds = construir_folds(entrada, definicion)
    except ConfiguracionInvalida:
        return  # combinación no válida: se rechaza, nunca produce folds con fuga
    assert [f.validacion for f in folds] == cohortes[iniciales:]
    assert [f.numero for f in folds] == list(range(1, len(folds) + 1))
    for fold in folds:
        anteriores = (*fold.ajuste, *fold.calibracion)
        assert fold.ajuste
        assert all(c < fold.validacion for c in anteriores)
        assert set(fold.ajuste).isdisjoint(fold.calibracion)
        assert fold.validacion not in anteriores
        if calibracion:
            assert all(c < fold.calibracion[0] for c in fold.ajuste)
        if deslizante:
            assert len(fold.ajuste) == ancho


def test_configuraciones_de_validacion_imposibles_se_rechazan() -> None:
    with pytest.raises(ConfiguracionInvalida):
        DefinicionValidacion(Esquema.EXPANSIVO, 1, True, None)  # sin cohorte de ajuste
    with pytest.raises(ConfiguracionInvalida):
        DefinicionValidacion(Esquema.EXPANSIVO, 2, False, 1)
    with pytest.raises(ConfiguracionInvalida):
        DefinicionValidacion(Esquema.DESLIZANTE, 2, False, None)
    with pytest.raises(ConfiguracionInvalida):
        DefinicionValidacion(Esquema.DESLIZANTE, 2, True, 2)
    with pytest.raises(ConfiguracionInvalida, match="ninguna cohorte de validación"):
        construir_folds(DESARROLLO[:2], DefinicionValidacion(Esquema.EXPANSIVO, 2, True, None))


@pytest.mark.parametrize(
    ("ruta", "decision"),
    [
        (("validacion",), "DP-07"),
        (("validacion", "esquema"), "DP-07"),
        (("validacion", "cohortes_iniciales"), "DP-07"),
        (("validacion", "cohorte_calibracion"), "DP-07"),
        (("matrices",), "DP-03"),
        (("preprocesamiento",), "DP-12"),
        (("preprocesamiento", "perfiles", "lineal"), "DP-12"),
        (("preprocesamiento", "perfiles", "lineal", "escalado"), "DP-12"),
        (("preprocesamiento", "perfiles", "arboles", "indicador_faltante"), "DP-12"),
        (("interpretabilidad",), "DP-11"),
        (("interpretabilidad", "alcance"), "DP-11"),
        (("interpretabilidad", "local", "lime_muestras"), "DP-11"),
    ],
)
def test_un_null_detiene_con_la_decision_pendiente(ruta: tuple[str, ...], decision: str) -> None:
    datos = copy.deepcopy(_datos())
    destino = datos
    for clave in ruta[:-1]:
        destino = destino[clave]
    destino[ruta[-1]] = None
    with pytest.raises(DecisionPendiente, match=decision):
        configuracion_experimentos_desde_datos(datos)


@pytest.mark.parametrize(
    "cambio",
    [
        lambda d: d.update(extra=1),
        lambda d: d.update(version_experimentos=2),
        lambda d: d.pop("nombre"),
        lambda d: d["validacion"].update(esquema="aleatorio"),
        lambda d: d["validacion"].update(cohortes_iniciales=True),
        lambda d: d["validacion"].update(ancho=2),  # el expansivo no lleva ancho
        lambda d: d["preprocesamiento"]["perfiles"]["lineal"].update(escalado="robusto"),
        lambda d: d["preprocesamiento"]["perfiles"]["lineal"].update(otro=1),
        lambda d: d["preprocesamiento"].update(perfiles={}),
    ],
)
def test_estructuras_invalidas_se_rechazan(cambio: Any) -> None:
    datos = copy.deepcopy(_datos())
    cambio(datos)
    with pytest.raises(ConfiguracionInvalida):
        configuracion_experimentos_desde_datos(datos)


# --- F3.2: modelos, búsqueda, desbalance, calibración y semilla ---------------------


def test_el_ejemplo_declara_las_cinco_familias_y_lo_demas_de_f32() -> None:
    configuracion = cargar_configuracion_experimentos(EJEMPLO)
    assert list(configuracion.modelos) == list(Familia)
    assert configuracion.busqueda == DefinicionBusqueda(
        MetodoBusqueda.MALLA, MetricaBusqueda.AUC_ROC, None
    )
    assert configuracion.desbalance is Desbalance.PESOS_CLASE
    assert configuracion.calibracion is Calibracion.PLATT
    assert configuracion.semilla == 20261111
    assert configuracion.modelos[Familia.LR].perfil == "lineal"
    assert configuracion.modelos[Familia.RF].perfil == "arboles"


def test_pi08_las_combinaciones_dependen_solo_de_familia_busqueda_y_semilla() -> None:
    espacio: dict[str, tuple[Any, ...]] = {"max_depth": (2, 4, 8), "n_estimators": (50, 100)}
    modelo = ModeloFamilia(Familia.RF, "arboles", espacio)
    malla = modelo.malla()
    assert len(malla) == 6
    assert malla[0] == {"max_depth": 2, "n_estimators": 50}
    en_malla = DefinicionBusqueda(MetodoBusqueda.MALLA, MetricaBusqueda.AUC_ROC, None)
    assert combinaciones_a_evaluar(modelo, en_malla, 1) == malla
    aleatoria = DefinicionBusqueda(MetodoBusqueda.ALEATORIA, MetricaBusqueda.AUC_ROC, 3)
    elegidas = combinaciones_a_evaluar(modelo, aleatoria, 7)
    assert len(elegidas) == 3
    assert set(map(repr, elegidas)) <= set(map(repr, malla))
    # Misma semilla, mismas combinaciones: no hay nada por escenario ni por fold.
    assert combinaciones_a_evaluar(modelo, aleatoria, 7) == elegidas
    todas = DefinicionBusqueda(MetodoBusqueda.ALEATORIA, MetricaBusqueda.AUC_ROC, 99)
    assert combinaciones_a_evaluar(modelo, todas, 7) == malla


@pytest.mark.parametrize(
    ("ruta", "decision"),
    [
        (("busqueda",), "DP-07"),
        (("busqueda", "metodo"), "DP-07"),
        (("modelos",), "DP-07"),
        (("modelos", "svm"), "DP-07"),
        (("modelos", "lr", "espacio"), "DP-07"),
        (("modelos", "lr", "perfil"), "DP-12"),
        (("modelos", "rf", "espacio", "max_depth"), "DP-07"),
        (("desbalance",), "DP-06"),
        (("calibracion",), "DP-09"),
    ],
)
def test_f32_un_null_detiene_con_la_decision_pendiente(
    ruta: tuple[str, ...], decision: str
) -> None:
    datos = copy.deepcopy(_datos())
    destino = datos
    for clave in ruta[:-1]:
        destino = destino[clave]
    destino[ruta[-1]] = None
    with pytest.raises(DecisionPendiente, match=decision):
        configuracion_experimentos_desde_datos(datos)


def test_f32_un_valor_null_dentro_del_espacio_tambien_detiene() -> None:
    datos = copy.deepcopy(_datos())
    datos["modelos"]["rf"]["espacio"]["max_depth"] = [4, None]
    with pytest.raises(DecisionPendiente, match="DP-07"):
        configuracion_experimentos_desde_datos(datos)


@pytest.mark.parametrize(
    "cambio",
    [
        lambda d: d["modelos"].pop("svm"),  # faltan familias (RF-M3-01)
        lambda d: d["modelos"].update(knn={"perfil": "lineal", "espacio": {"k": [3]}}),
        lambda d: d["modelos"]["lr"]["espacio"].update(random_state=[1]),  # reservado
        lambda d: d["modelos"]["xgboost"]["espacio"].update(scale_pos_weight=[2.0]),
        lambda d: d["modelos"]["lr"].update(perfil="inexistente"),
        lambda d: d["modelos"]["lr"]["espacio"].update(C=[]),
        lambda d: d["modelos"]["lr"]["espacio"].update(C=[1.0, 1.0]),
        lambda d: d["modelos"]["lr"]["espacio"].update(C=[{"a": 1}]),
        lambda d: d["busqueda"].update(intentos=3),  # la malla no lleva intentos
        lambda d: d["busqueda"].update(metodo="aleatoria"),  # sin intentos
        lambda d: d["busqueda"].update(metrica="precision"),
        lambda d: d.update(desbalance="sobremuestreo"),
        lambda d: d.update(calibracion="beta"),
        lambda d: d.update(semilla=-1),
        lambda d: d.update(semilla=True),
        lambda d: d.pop("semilla"),
        # Sin cohorte de calibración no se puede buscar ni calibrar.
        lambda d: d["validacion"].update(cohorte_calibracion=False),
    ],
)
def test_f32_estructuras_invalidas_se_rechazan(cambio: Any) -> None:
    datos = copy.deepcopy(_datos())
    cambio(datos)
    with pytest.raises(ConfiguracionInvalida):
        configuracion_experimentos_desde_datos(datos)


def test_sin_cohorte_de_calibracion_vale_con_una_combinacion_y_sin_calibrar() -> None:
    datos = copy.deepcopy(_datos())
    datos["validacion"]["cohorte_calibracion"] = False
    datos["calibracion"] = "ninguna"
    for bloque in datos["modelos"].values():
        bloque["espacio"] = {n: v[:1] for n, v in bloque["espacio"].items()}
    configuracion = configuracion_experimentos_desde_datos(datos)
    assert not configuracion.validacion.cohorte_calibracion


def test_f33_el_ejemplo_declara_metricas_e_intervalos_y_un_null_detiene() -> None:
    configuracion = cargar_configuracion_experimentos(EJEMPLO)
    assert [m.value for m in configuracion.metricas.metricas] == [
        "auc_roc",
        "brier",
        "brier_escalado",
        "recall_q",
    ]
    assert configuracion.metricas.q == 0.2
    for clave, decision in (("metricas", "DP-08a"), ("intervalos", "DP-08e")):
        datos = copy.deepcopy(_datos())
        datos[clave] = None
        with pytest.raises(DecisionPendiente, match=decision):
            configuracion_experimentos_desde_datos(datos)
