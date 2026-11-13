"""Funciones del visor según las decisiones abiertas y comparación del historial (F4.4).

Los registros comparados son diccionarios escritos a mano (EJEMPLO FICTICIO).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from suficiencia.application.contratos import (
    DiferenciaCampoResumen,
    FuncionDisponibilidadResumen,
    ResultadoComparacionExperimentos,
    ResultadoDisponibilidadFunciones,
)
from suficiencia.domain.trazabilidad.historial import (
    FUNCIONES_VISOR,
    aplanar,
    comparar_registros,
    disponibilidad,
)
from suficiencia.ui import presentacion


def test_las_funciones_del_visor_nombran_decisiones_del_catalogo(raiz: Path) -> None:
    catalogo = yaml.safe_load(
        (raiz / "config" / "decisiones_metodologicas.yaml").read_text(encoding="utf-8")
    )
    codigos = {d["codigo"] for d in catalogo["decisiones"]}
    assert len({f.codigo for f in FUNCIONES_VISOR}) == len(FUNCIONES_VISOR)
    for funcion in FUNCIONES_VISOR:
        assert funcion.decisiones, funcion.codigo
        for codigo in funcion.decisiones:
            assert re.fullmatch(r"DP-\d{2}", codigo) and codigo in codigos


def test_una_funcion_solo_queda_disponible_con_todas_sus_decisiones_registradas() -> None:
    sin_registros = disponibilidad(FUNCIONES_VISOR, {})
    assert all(d.abiertas == d.funcion.decisiones for d in sin_registros)
    assert not any(d.con_datos_del_proyecto for d in sin_registros)
    objetivo = next(f for f in FUNCIONES_VISOR if f.codigo == "objetivo")
    (parcial,) = disponibilidad([objetivo], {"DP-01": True, "DP-18": False})
    assert parcial.abiertas == ("DP-18",) and not parcial.con_datos_del_proyecto
    (completa,) = disponibilidad([objetivo], {"DP-01": True, "DP-18": True})
    assert completa.abiertas == () and completa.con_datos_del_proyecto


def test_aplanar_y_comparar_registros() -> None:
    a: dict[str, Any] = {
        "estado": "exitosa",
        "modo": "exploratorio",
        "configuracion": {"escenario": "T1|A", "familia": "lr", "folds": [1, 2]},
        "error": None,
        "entorno": {"python": "3.11"},
    }
    b: dict[str, Any] = {
        "estado": "fallida",
        "modo": "exploratorio",
        "configuracion": {"escenario": "T1|A", "familia": "rf"},
        "error": "ValueError",
    }
    assert aplanar(a["configuracion"]) == {
        "escenario": "T1|A",
        "familia": "lr",
        "folds": "[1, 2]",
    }
    campos = comparar_registros(a, b)
    por_campo = {c.campo: c for c in campos}
    assert [c.campo for c in campos] == sorted(por_campo)
    assert "entorno.python" not in por_campo  # el entorno no se compara
    assert por_campo["configuracion.escenario"].igual
    assert not por_campo["configuracion.familia"].igual
    assert (por_campo["configuracion.folds"].valor_a, por_campo["configuracion.folds"].valor_b) == (
        "[1, 2]",
        "—",
    )
    assert (por_campo["error"].valor_a, por_campo["error"].valor_b) == ("—", "ValueError")
    assert por_campo["modo"].igual and not por_campo["estado"].igual


def test_tablas_del_visor() -> None:
    funciones = ResultadoDisponibilidadFunciones(
        funciones=(
            FuncionDisponibilidadResumen(
                codigo="objetivo",
                nombre="Construir el objetivo",
                decisiones=("DP-01", "DP-18"),
                abiertas=("DP-18",),
                con_datos_del_proyecto=False,
            ),
        )
    )
    tabla = presentacion.tabla_funciones(funciones)
    assert tabla.iloc[0]["Con datos del proyecto"] == "DESACTIVADA"
    assert tabla.iloc[0]["Abiertas"] == "DP-18"
    comparacion = ResultadoComparacionExperimentos(
        a="EXP-1",
        b="EXP-1",
        campos=(
            DiferenciaCampoResumen(campo="estado", valor_a="x", valor_b="x", igual=True),
            DiferenciaCampoResumen(campo="modo", valor_a="x", valor_b="y", igual=False),
        ),
        diferentes=1,
    )
    solo = presentacion.tabla_comparacion_experimentos(comparacion, solo_diferencias=True)
    assert list(solo["Campo"]) == ["modo"]
    todas = presentacion.tabla_comparacion_experimentos(comparacion, solo_diferencias=False)
    assert len(todas) == 2
    assert list(todas.columns) == ["Campo", "A (EXP-1)", "B (EXP-1)", "Igual"]
