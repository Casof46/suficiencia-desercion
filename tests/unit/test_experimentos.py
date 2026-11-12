"""Configuración de experimentos y folds cronológicos (F3.1).

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
    DefinicionValidacion,
    Escalado,
    Esquema,
    ImputacionCategorica,
    ImputacionNumerica,
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
