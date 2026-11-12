"""Matrices por escenario con corte en el periodo índice (F3.1).

Fuga temporal en la construcción de matrices (nada posterior al periodo índice),
PU-12 (los no etiquetables nunca entran) y DP-03 como dato obligatorio. Los
historiales son ficticios y se escriben a mano.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from suficiencia.domain.datos.objetivo import COLUMNA_ESTADO, ColumnasHistorial, EstadoEtiqueta
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.construccion import FugaTemporal
from suficiencia.domain.escenarios.matrices import (
    Agregacion,
    DefinicionMatrices,
    construir_matriz,
    definicion_matrices_desde_datos,
)
from suficiencia.domain.escenarios.modelo import (
    Bloque,
    ConjuntoInformacion,
    Escenario,
    Variable,
    Ventana,
)
from suficiencia.domain.escenarios.poblaciones import Diseno, PeriodosIndice, construir_poblaciones
from suficiencia.persistence.objetivo_yaml import definicion_desde_datos

OBJETIVO = Path(__file__).resolve().parents[2] / "config" / "ejemplos" / "objetivo_ficticio.yaml"
CODIGOS = {"M": "matriculado", "A": "no_matriculado", "T": "traslado"}
COLUMNAS = ColumnasHistorial(("seudonimo",), "cohorte", "ciclo", "estado")
INDICES = PeriodosIndice({"T0": 0, "T1": 1, "T2": 2, "T3": 3})
VARIABLES = (
    Variable("puntaje", Bloque.ACADEMICO, "T0"),
    Variable("promedio", Bloque.ACADEMICO, "T1"),
    Variable("deuda", Bloque.FINANCIERO, "T1"),
)
LECTURAS = DefinicionMatrices(
    {
        "puntaje": Agregacion.PRIMER_REGISTRO,
        "promedio": Agregacion.ULTIMO_CICLO,
        "deuda": Agregacion.ULTIMO_CICLO,
    }
)
HISTORIALES = {
    "siempre": ("2014-1", "MMMMMMMM"),
    "deserta_en_3": ("2014-1", "MMAAAAAA"),
    "pausa_en_2": ("2014-2", "MAMMMMMM"),  # sin registro de matrícula en el periodo 2
    "traslado": ("2014-1", "MMT"),  # no etiquetable
}


def _definicion() -> Any:
    datos = yaml.safe_load(OBJETIVO.read_text(encoding="utf-8"))
    # Un periodo sin registro cuenta como ausencia (y el reingreso la anula), para que
    # "pausa_en_2" siga en la población sin registro en el periodo 2.
    datos["seguimiento"]["periodo_sin_registro"] = "ausencia"
    return definicion_desde_datos(OBJETIVO, datos)


def _tabla(historiales: dict[str, tuple[str, str]]) -> pd.DataFrame:
    filas = []
    for unidad, (cohorte, secuencia) in historiales.items():
        for periodo, letra in enumerate(secuencia, start=1):
            if unidad == "pausa_en_2" and periodo == 2:
                continue  # el periodo 2 no tiene registro
            filas.append(
                {
                    "seudonimo": unidad,
                    "cohorte": cohorte,
                    "ciclo": periodo,
                    "estado": CODIGOS[letra],
                    "puntaje": 500.0 + len(unidad),
                    "promedio": 10.0 + periodo,  # el valor delata el periodo leído
                    "deuda": periodo % 2 == 0,
                }
            )
    return pd.DataFrame(filas)


def _escenario(ventana: str, bloques: set[Bloque], variables: tuple[str, ...]) -> Escenario:
    return Escenario(
        Ventana(ventana, "ficticia"), ConjuntoInformacion(frozenset(bloques)), variables, ()
    )


def _matriz(tabla: pd.DataFrame, ventana: str, variables: tuple[str, ...]) -> Any:
    poblaciones = construir_poblaciones(tabla, COLUMNAS, _definicion(), INDICES)
    bloques = {v.bloque for v in VARIABLES if v.nombre in variables} | {Bloque.ACADEMICO}
    return construir_matriz(
        tabla,
        COLUMNAS,
        _escenario(ventana, bloques, variables),
        VARIABLES,
        poblaciones.miembros[(Diseno.D1, ventana)],
        INDICES.periodos[ventana],
        LECTURAS,
    )


def test_ultimo_ciclo_lee_el_periodo_indice_y_primer_registro_la_admision() -> None:
    tabla = _tabla(HISTORIALES)
    for ventana, periodo in (("T1", 1), ("T2", 2), ("T3", 3)):
        matriz = _matriz(tabla, ventana, ("puntaje", "promedio"))
        assert set(matriz.predictores.loc[["siempre"], "promedio"]) == {10.0 + periodo}
        assert matriz.predictores.loc["siempre", "puntaje"] == 500.0 + len("siempre")


def test_sin_registro_en_el_periodo_indice_queda_faltante_y_no_se_toma_uno_posterior() -> None:
    matriz = _matriz(_tabla(HISTORIALES), "T2", ("puntaje", "promedio"))
    assert pd.isna(matriz.predictores.loc["pausa_en_2", "promedio"])


def test_pu12_los_no_etiquetables_nunca_entran_y_el_objetivo_es_la_etiqueta() -> None:
    for ventana in ("T0", "T1"):
        variables = ("puntaje",) if ventana == "T0" else ("puntaje", "promedio")
        matriz = _matriz(_tabla(HISTORIALES), ventana, variables)
        assert "traslado" not in matriz.predictores.index
        assert matriz.objetivo.to_dict() == {"siempre": 0, "deserta_en_3": 1, "pausa_en_2": 0}
        assert matriz.cohorte.to_dict() == {
            "siempre": "2014-1",
            "deserta_en_3": "2014-1",
            "pausa_en_2": "2014-2",
        }


def test_pu12_un_no_etiquetable_en_los_miembros_tampoco_entra() -> None:
    """Defensa adicional: aunque una población trajera un no etiquetable, se descarta."""
    tabla = _tabla(HISTORIALES)
    poblaciones = construir_poblaciones(tabla, COLUMNAS, _definicion(), INDICES)
    miembros = poblaciones.miembros[(Diseno.D1, "T0")]
    intruso = miembros.iloc[[0]].assign(
        seudonimo="traslado", **{COLUMNA_ESTADO: EstadoEtiqueta.NO_ETIQUETABLE.value}
    )
    matriz = construir_matriz(
        tabla,
        COLUMNAS,
        _escenario("T0", {Bloque.ACADEMICO}, ("puntaje",)),
        VARIABLES,
        pd.concat([miembros, intruso], ignore_index=True),
        0,
        LECTURAS,
    )
    assert "traslado" not in matriz.predictores.index
    assert len(matriz.objetivo) == len(miembros)


@settings(max_examples=25, deadline=None)
@given(
    ventana=st.sampled_from(["T1", "T2", "T3"]),
    nuevo=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False),
)
def test_cambiar_cualquier_valor_posterior_al_periodo_indice_no_cambia_la_matriz(
    ventana: str, nuevo: float
) -> None:
    tabla = _tabla(HISTORIALES)
    original = _matriz(tabla, ventana, ("puntaje", "promedio"))
    alterada = tabla.copy()
    posteriores = alterada["ciclo"] > INDICES.periodos[ventana]
    alterada.loc[posteriores, ["promedio", "puntaje"]] = nuevo
    alterada.loc[posteriores, "deuda"] = True
    # Las etiquetas sí dependen del futuro (es el resultado); los predictores no.
    pd.testing.assert_frame_equal(
        _matriz(alterada, ventana, ("puntaje", "promedio")).predictores, original.predictores
    )


def test_una_variable_posterior_a_la_ventana_se_rechaza_como_fuga() -> None:
    with pytest.raises(FugaTemporal):
        _matriz(_tabla(HISTORIALES), "T0", ("puntaje", "promedio"))


def test_primer_registro_solo_para_variables_disponibles_desde_t0() -> None:
    lecturas = DefinicionMatrices({"promedio": Agregacion.PRIMER_REGISTRO})
    tabla = _tabla(HISTORIALES)
    poblaciones = construir_poblaciones(tabla, COLUMNAS, _definicion(), INDICES)
    with pytest.raises(ConfiguracionInvalida, match="primer_registro"):
        construir_matriz(
            tabla,
            COLUMNAS,
            _escenario("T1", {Bloque.ACADEMICO}, ("promedio",)),
            VARIABLES,
            poblaciones.miembros[(Diseno.D1, "T1")],
            1,
            lecturas,
        )


def test_un_escenario_no_factible_no_se_construye() -> None:
    no_factible = Escenario(
        Ventana("T0", "ficticia"),
        ConjuntoInformacion(frozenset({Bloque.ACADEMICO, Bloque.CONDUCTUAL})),
        ("puntaje",),
        (Bloque.CONDUCTUAL,),
    )
    tabla = _tabla(HISTORIALES)
    poblaciones = construir_poblaciones(tabla, COLUMNAS, _definicion(), INDICES)
    with pytest.raises(ConfiguracionInvalida, match="no es factible"):
        construir_matriz(
            tabla,
            COLUMNAS,
            no_factible,
            VARIABLES,
            poblaciones.miembros[(Diseno.D1, "T0")],
            0,
            LECTURAS,
        )


def test_dp03_la_lectura_de_cada_variable_es_obligatoria() -> None:
    with pytest.raises(DecisionPendiente, match="DP-03"):
        definicion_matrices_desde_datos(None)
    with pytest.raises(DecisionPendiente, match="DP-03"):
        definicion_matrices_desde_datos({"agregacion": {"puntaje": None}})
    with pytest.raises(DecisionPendiente, match="DP-03"):
        DefinicionMatrices({}).de("puntaje")
    with pytest.raises(ConfiguracionInvalida):
        definicion_matrices_desde_datos({"agregacion": {"puntaje": "promedio_movil"}})
    with pytest.raises(ConfiguracionInvalida):
        definicion_matrices_desde_datos({"agregacion": {"puntaje": "ultimo_ciclo"}, "extra": 1})
