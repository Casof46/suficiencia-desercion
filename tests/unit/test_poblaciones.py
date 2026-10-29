"""Poblaciones D1, D2 y D3, partición cronológica y sello (H2.5).

PU-10, PU-11, prueba de cobertura D3, PU-13, PI-07 (parte de la partición) y el
sello de PI-02. Los historiales son ficticios y se escriben a mano; las
definiciones y configuraciones parten de los ejemplos ficticios.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from suficiencia.domain.datos.objetivo import COLUMNA_ESTADO, ColumnasHistorial
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.particion import (
    OPERACION_EVALUACION_FINAL,
    AccesoPruebaDenegado,
    DefinicionParticion,
    SelloPrueba,
    dividir,
    sellar,
)
from suficiencia.domain.escenarios.poblaciones import (
    COLUMNA_DETECTABLE,
    EXCLUSION_EVENTO_PREVIO,
    Diseno,
    PeriodosIndice,
    construir_poblaciones,
    contar_exclusiones,
    describir,
    seguimiento_por_cohorte,
)
from suficiencia.domain.trazabilidad.registros import RegistroAcceso
from suficiencia.persistence.objetivo_yaml import definicion_desde_datos
from suficiencia.persistence.poblaciones_yaml import (
    ARCHIVO_DEL_PROYECTO,
    cargar_configuracion_poblaciones,
    configuracion_desde_datos,
)

EJEMPLOS = Path(__file__).resolve().parents[2] / "config" / "ejemplos"
OBJETIVO = EJEMPLOS / "objetivo_ficticio.yaml"
POBLACIONES = EJEMPLOS / "poblaciones_ficticio.yaml"
CODIGOS = {"M": "matriculado", "A": "no_matriculado", "T": "traslado"}
COLUMNAS = ColumnasHistorial(("seudonimo",), "cohorte", "ciclo", "estado")
INDICES = PeriodosIndice({"T0": 0, "T1": 1, "T2": 2, "T3": 3})


def _definicion(**cambios: Any) -> Any:
    datos = yaml.safe_load(OBJETIVO.read_text(encoding="utf-8"))
    datos.update(cambios)
    return definicion_desde_datos(OBJETIVO, datos)


def _tabla(historiales: dict[str, tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"seudonimo": u, "cohorte": c, "ciclo": p, "estado": CODIGOS[letra]}
            for u, (c, secuencia) in historiales.items()
            for p, letra in enumerate(secuencia, start=1)
        ]
    )


HISTORIALES = {
    "siempre": ("2014-1", "MMMMMMMM"),
    "deserta_en_2": ("2014-1", "MAAAAAAA"),  # evento después de T1 y antes de T2
    "deserta_en_5": ("2014-1", "MMMMAAAA"),  # evento después de T3
    "traslado": ("2014-1", "MMT"),
}


def _miembros(poblaciones: Any, diseno: Diseno, ventana: str) -> set[str]:
    return set(poblaciones.miembros[(diseno, ventana)]["seudonimo"])


def test_pu10_d1_excluye_a_quien_deserto_antes_de_la_fecha_indice() -> None:
    poblaciones = construir_poblaciones(_tabla(HISTORIALES), COLUMNAS, _definicion(), INDICES)
    for ventana in ("T0", "T1"):
        d1 = poblaciones.miembros[(Diseno.D1, ventana)].set_index("seudonimo")
        assert d1.loc["deserta_en_2", COLUMNA_ESTADO] == "positivo"
    for ventana in ("T2", "T3"):
        assert "deserta_en_2" not in _miembros(poblaciones, Diseno.D1, ventana)
        excluidas = poblaciones.exclusiones[ventana].set_index("seudonimo")
        assert excluidas.loc["deserta_en_2", "motivo_exclusion"] == EXCLUSION_EVENTO_PREVIO
    assert _miembros(poblaciones, Diseno.D1, "T3") == {"siempre", "deserta_en_5"}
    # El no etiquetable nunca entra y se cuenta por su motivo.
    assert all("traslado" not in _miembros(poblaciones, Diseno.D1, v) for v in INDICES.periodos)
    assert set(poblaciones.exclusiones["T0"]["motivo_exclusion"]) == {"resultado_no_observable"}


def test_pu11_d2_es_la_poblacion_en_riesgo_en_la_ultima_ventana_en_todas() -> None:
    poblaciones = construir_poblaciones(_tabla(HISTORIALES), COLUMNAS, _definicion(), INDICES)
    comun = _miembros(poblaciones, Diseno.D1, "T3")
    for ventana in INDICES.periodos:
        assert _miembros(poblaciones, Diseno.D2, ventana) == comun
        pd.testing.assert_frame_equal(
            poblaciones.miembros[(Diseno.D2, ventana)], poblaciones.miembros[(Diseno.D2, "T3")]
        )


def test_d3_cuenta_como_no_detectable_el_evento_previo_a_la_fecha_indice() -> None:
    poblaciones = construir_poblaciones(_tabla(HISTORIALES), COLUMNAS, _definicion(), INDICES)
    for ventana in INDICES.periodos:
        d3 = poblaciones.miembros[(Diseno.D3, ventana)].set_index("seudonimo")
        assert set(d3.index) == {"siempre", "deserta_en_2", "deserta_en_5"}
        esperado = ventana in ("T0", "T1")
        assert bool(d3.loc["deserta_en_2", COLUMNA_DETECTABLE]) is esperado
        assert bool(d3.loc["deserta_en_5", COLUMNA_DETECTABLE])
    descripcion = {
        (d.diseno, d.ventana): d for d in describir(poblaciones, "cohorte", frozenset({"2014-1"}))
    }
    assert descripcion[(Diseno.D3, "T3")].eventos == 2
    assert descripcion[(Diseno.D3, "T3")].eventos_detectables == 1


def test_con_horizonte_relativo_d1_se_etiqueta_desde_cada_fecha_indice_y_no_hay_d3() -> None:
    definicion = _definicion(horizonte={"periodos": 2, "desde": "fecha_indice"})
    tabla = _tabla({"u": ("2014-1", "MMMAAAAA")})
    poblaciones = construir_poblaciones(tabla, COLUMNAS, definicion, INDICES)
    estados = {
        v: poblaciones.miembros[(Diseno.D1, v)][COLUMNA_ESTADO].tolist() for v in INDICES.periodos
    }
    # Evento en el periodo 4: fuera del horizonte de 2 periodos contado desde T0 (1 y 2)
    # y desde T1 (2 y 3); dentro del contado desde T2 (3 y 4) y desde T3 (4 y 5).
    assert estados == {
        "T0": ["negativo"],
        "T1": ["negativo"],
        "T2": ["positivo"],
        "T3": ["positivo"],
    }
    assert all((Diseno.D3, v) not in poblaciones.miembros for v in INDICES.periodos)


@given(eventos_prueba=st.lists(st.sampled_from(["MMMMMMMM", "MAAAAAAA", "MMMAAAAA"]), max_size=6))
def test_pu13_los_descriptivos_solo_usan_las_cohortes_de_desarrollo(
    eventos_prueba: list[str],
) -> None:
    desarrollo = {"d1": ("2014-1", "MMMMMMMM"), "d2": ("2014-1", "MAAAAAAA")}
    prueba = {f"p{i}": ("2015-1", s) for i, s in enumerate(eventos_prueba)}
    definicion = _definicion()
    solo = construir_poblaciones(_tabla(desarrollo), COLUMNAS, definicion, INDICES)
    todas = construir_poblaciones(_tabla({**desarrollo, **prueba}), COLUMNAS, definicion, INDICES)
    cohortes = frozenset({"2014-1"})
    assert describir(solo, "cohorte", cohortes) == describir(todas, "cohorte", cohortes)
    assert contar_exclusiones(solo, "cohorte", cohortes) == contar_exclusiones(
        todas, "cohorte", cohortes
    )


@pytest.mark.parametrize(
    ("periodos", "mensaje"),
    [
        ({"T0": 0, "T1": 1, "T2": 1, "T3": 3}, "crecer"),
        ({"T0": -1, "T1": 1, "T2": 2, "T3": 3}, "mayor o igual a 0"),
        ({"T0": 0, "T1": 1, "T2": 2}, "T0, T1, T2 y T3"),
    ],
)
def test_periodos_indice_invalidos(periodos: dict[str, int], mensaje: str) -> None:
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        PeriodosIndice(periodos)


def test_seguimiento_por_cohorte_sin_usar_el_resultado() -> None:
    tabla = _tabla({"a": ("2014-1", "MMMMMMMM"), "b": ("2016-1", "MMMM")})
    seguimiento = seguimiento_por_cohorte(tabla, COLUMNAS, _definicion(), INDICES)
    resumen = {
        s.cohorte: (s.unidades, s.ultimo_periodo_observable, s.completo) for s in seguimiento
    }
    # Horizonte de 6 más un periodo para confirmar el evento: hacen falta 7.
    assert resumen == {"2014-1": (1, 8, True), "2016-1": (1, 4, False)}
    assert {s.periodo_necesario for s in seguimiento} == {7}


# Partición (PI-07, parte de la partición) y sello (PI-02).
def _particion(**cambios: Any) -> DefinicionParticion:
    base: dict[str, Any] = {
        "desarrollo": frozenset({"2014-2", "2015-1"}),
        "prueba": frozenset({"2015-2"}),
        "piloto": frozenset({"2014-1"}),
        "excluidas": frozenset(),
        "plan_contingencia": "plan ficticio",
    }
    base.update(cambios)
    return DefinicionParticion(**base)


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"prueba": frozenset({"2015-1"})}, "están en desarrollo y en prueba"),
        ({"prueba": frozenset({"2014-2"}), "desarrollo": frozenset({"2015-1"})}, "posterior"),
        ({"piloto": frozenset({"2016-1"})}, "posterior"),
        ({"prueba": frozenset()}, "al menos una cohorte"),
        ({"plan_contingencia": " "}, "plan_contingencia"),
    ],
)
def test_una_particion_invalida_se_rechaza(cambios: dict[str, Any], mensaje: str) -> None:
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        _particion(**cambios)


cohortes = st.lists(
    st.sampled_from([f"{a}-{s}" for a in range(2010, 2020) for s in (1, 2)]),
    min_size=2,
    max_size=8,
    unique=True,
)


@given(cohortes=cohortes, corte=st.integers(min_value=1, max_value=7))
def test_pi07_toda_cohorte_de_prueba_es_posterior_a_las_de_desarrollo(
    cohortes: list[str], corte: int
) -> None:
    ordenadas = sorted(cohortes)
    corte = min(corte, len(ordenadas) - 1)
    definicion = _particion(
        desarrollo=frozenset(ordenadas[:corte]),
        prueba=frozenset(ordenadas[corte:]),
        piloto=frozenset(),
    )
    assert max(definicion.desarrollo) < min(definicion.prueba)
    with pytest.raises(ConfiguracionInvalida):
        _particion(
            desarrollo=frozenset(ordenadas[corte:]),
            prueba=frozenset(ordenadas[:corte]),
            piloto=frozenset(),
        )


def test_dividir_exige_asignar_cada_cohorte() -> None:
    unidades = pd.DataFrame(
        {"seudonimo": ["a", "b", "c"], "cohorte": ["2014-2", "2015-2", "2016-1"]}
    )
    with pytest.raises(ConfiguracionInvalida, match="2016-1 no están asignadas"):
        dividir(unidades, "cohorte", _particion())
    definicion = _particion(excluidas=frozenset({"2016-1"}))
    with pytest.raises(ConfiguracionInvalida, match="no tienen unidades"):
        dividir(unidades, "cohorte", definicion)


def test_pi02_el_sello_solo_entrega_la_prueba_a_la_evaluacion_final() -> None:
    unidades = pd.DataFrame(
        {
            "seudonimo": ["a", "b", "c", "d"],
            "cohorte": ["2014-1", "2014-2", "2015-1", "2015-2"],
        }
    )
    division = dividir(unidades, "cohorte", _particion())
    registros: list[RegistroAcceso] = []
    particion = sellar(
        division, _particion(), SelloPrueba(lambda: division.prueba, registros.append)
    )
    assert particion.tamano_prueba == 1
    assert set(particion.desarrollo["seudonimo"]) == {"b", "c"}
    assert not hasattr(particion, "prueba")
    with pytest.raises(AccesoPruebaDenegado):
        particion.sello.leer("entrenamiento", "intento de prueba")
    assert registros[-1] == RegistroAcceso("entrenamiento", "intento de prueba", False)
    prueba = particion.sello.leer(OPERACION_EVALUACION_FINAL, "evaluación final simulada")
    assert list(prueba["seudonimo"]) == ["d"]
    assert registros[-1].permitido
    assert len(registros) == 2


# Configuración de poblaciones y partición.
def _datos_poblaciones() -> dict[str, Any]:
    datos = yaml.safe_load(POBLACIONES.read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


@pytest.mark.parametrize(
    ("ruta", "decision"),
    [
        (("periodo_indice",), "DP-01d"),
        (("periodo_indice", "T2"), "DP-01d"),
        (("diseno_principal",), "DP-04"),
        (("analisis_complementarios",), "DP-17"),
        (("particion",), "DP-05"),
        (("particion", "cohortes_prueba"), "DP-05"),
        (("particion", "cohortes_piloto"), "DP-05"),
        (("particion", "plan_contingencia"), "DP-05"),
    ],
)
def test_un_valor_nulo_detiene_el_programa_nombrando_su_decision(
    ruta: tuple[str, ...], decision: str
) -> None:
    datos = copy.deepcopy(_datos_poblaciones())
    destino = datos
    for parte in ruta[:-1]:
        destino = destino[parte]
    destino[ruta[-1]] = None
    with pytest.raises(DecisionPendiente) as error:
        configuracion_desde_datos(POBLACIONES, datos)
    assert error.value.decision == decision


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"diseno_principal": "D4"}, "no es válido"),
        ({"analisis_complementarios": ["D1"]}, "a la vez"),
        ({"version_poblaciones": 2}, "version_poblaciones"),
        ({"extra": 1}, "claves desconocidas"),
    ],
)
def test_una_configuracion_mal_formada_se_rechaza(cambios: dict[str, Any], mensaje: str) -> None:
    datos = {**_datos_poblaciones(), **cambios}
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        configuracion_desde_datos(POBLACIONES, datos)


def test_la_configuracion_del_proyecto_no_existe_mientras_dp04_siga_abierta(
    tmp_path: Path,
) -> None:
    with pytest.raises(DecisionPendiente) as error:
        cargar_configuracion_poblaciones(tmp_path / ARCHIVO_DEL_PROYECTO)
    assert error.value.decision == "DP-04"


def test_el_ejemplo_esta_rotulado_como_ficticio() -> None:
    configuracion = cargar_configuracion_poblaciones(POBLACIONES)
    assert configuracion.ficticio
    assert configuracion.particion.piloto  # DP-08h: el equipo permitió el piloto
    assert "EJEMPLO FICTICIO" in POBLACIONES.read_text(encoding="utf-8")
