"""Objetivo y estados de etiqueta (H2.4): PU-09, PU-12 y definición incompleta.

Todos los historiales son ficticios y se escriben a mano. Las definiciones parten
del ejemplo ficticio ``config/ejemplos/objetivo_ficticio.yaml`` y cambian un
parámetro a la vez: ninguna es la definición de deserción del proyecto.
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

from fixtures.generador_sintetico import generar_historial
from suficiencia.domain.datos.objetivo import (
    COLUMNA_ESTADO,
    COLUMNA_MOTIVO,
    ColumnasHistorial,
    DefinicionObjetivo,
    EstadoEtiqueta,
    Etiqueta,
    Motivo,
    construir_objetivo,
    etiquetar_unidad,
    para_modelado,
    resumir_no_etiquetables,
)
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.persistence.objetivo_yaml import (
    ARCHIVO_DEL_PROYECTO,
    cargar_definicion_objetivo,
    definicion_desde_datos,
)

EJEMPLO = Path(__file__).resolve().parents[2] / "config" / "ejemplos" / "objetivo_ficticio.yaml"
CODIGOS = {
    "M": "matriculado",
    "A": "no_matriculado",
    "P": "reserva",
    "R": "retiro_total",
    "T": "traslado",
    "I": "traslado_interno",
    "X": "fallecimiento",
    "F": "retiro_formal",
}
CATALOGO_AMPLIADO = {
    "matriculado": "matricula",
    "no_matriculado": "ausencia",
    "reserva": "pausa",
    "retiro_total": "retiro_en_periodo",
    "traslado": "traslado_externo",
    "traslado_interno": "traslado_interno",
    "fallecimiento": "desenlace_excluido",
    "retiro_formal": "evento_formal",
}
POS, NEG, NE = EstadoEtiqueta.POSITIVO, EstadoEtiqueta.NEGATIVO, EstadoEtiqueta.NO_ETIQUETABLE
SI, RNO, DES = (
    Motivo.SEGUIMIENTO_INCOMPLETO,
    Motivo.RESULTADO_NO_OBSERVABLE,
    Motivo.DESENLACE_EXCLUIDO,
)


def _datos_ejemplo() -> dict[str, Any]:
    datos = yaml.safe_load(EJEMPLO.read_text(encoding="utf-8"))
    datos["catalogo_estados"] = dict(CATALOGO_AMPLIADO)
    assert isinstance(datos, dict)
    return datos


def _definicion(**cambios: Any) -> DefinicionObjetivo:
    """El ejemplo ficticio con algunos campos cambiados ("seccion.campo": valor)."""
    datos = copy.deepcopy(_datos_ejemplo())
    for ruta, valor in cambios.items():
        partes = ruta.split("__")
        destino = datos
        for parte in partes[:-1]:
            destino = destino[parte]
        destino[partes[-1]] = valor
    return definicion_desde_datos(EJEMPLO, datos)


def _etiquetar(
    secuencia: str, observable: int | None = None, desde: int = 0, **cambios: Any
) -> Etiqueta:
    estados = {
        periodo: CODIGOS[letra] for periodo, letra in enumerate(secuencia, start=1) if letra != "-"
    }
    limite = observable if observable is not None else len(secuencia)
    return etiquetar_unidad(estados, limite, _definicion(**cambios), desde)


# PU-09: cada situación del desglose de DP-01 produce el estado que indican las reglas.
# Ejemplo: 2 periodos sin matrícula, horizonte de 6, fechado en el primer periodo sin
# matrícula, pausa neutral hasta 2 periodos, reingreso que anula y confirmación exigida.
CASOS_PU09 = [
    ("siempre matriculado", "MMMMMMMM", {}, NEG, None, None),
    ("deja de matricularse", "MMAAAAAA", {}, POS, None, 3),
    ("fechado en la confirmación", "MMAAAAAA", {"fechado_evento": "confirmacion"}, POS, None, 4),
    ("una sola ausencia", "MMAMMMMM", {}, NEG, None, None),
    ("pausa breve y vuelve", "MPMMMMMM", {}, NEG, None, None),
    ("pausa larga", "MPPPAAAA", {}, POS, None, 4),
    ("pausa sin límite", "MPPPPPPP", {"pausas__limite_periodos": "sin_limite"}, NEG, None, None),
    (
        "pausa como ausencia",
        "MPMMMMMM",
        {"pausas": {"tratamiento": "ausencia"}},
        NEG,
        None,
        None,
    ),
    (
        "pausa doble como ausencia",
        "MPPMMMMM",
        {"pausas": {"tratamiento": "ausencia"}, "reingreso": "no_anula"},
        POS,
        None,
        2,
    ),
    (
        "pausa no observable",
        "MPMMMMMM",
        {"pausas": {"tratamiento": "no_observable"}},
        NE,
        RNO,
        None,
    ),
    ("reingreso que anula", "MAAMMMMM", {}, NEG, None, None),
    (
        "pausa doble anulada por el reingreso",
        "MPPMMMMM",
        {"pausas": {"tratamiento": "ausencia"}},
        NEG,
        None,
        None,
    ),
    ("reingreso que no anula", "MAAMMMMM", {"reingreso": "no_anula"}, POS, None, 2),
    ("reingreso después del horizonte", "MMMMAAMM", {}, POS, None, 5),
    ("retiro en el periodo como ausencia", "MRAAAAAA", {}, POS, None, 2),
    (
        "retiro en el periodo como evento",
        "MMRMMMMM",
        {"retiro_en_periodo": "evento"},
        NEG,
        None,
        None,
    ),
    (
        "retiro como evento sin reingreso",
        "MMRAAAAA",
        {"retiro_en_periodo": "evento", "reingreso": "no_anula"},
        POS,
        None,
        3,
    ),
    ("retiro como matrícula", "MRRMMMMM", {"retiro_en_periodo": "matricula"}, NEG, None, None),
    ("traslado externo no observable", "MMT", {}, NE, RNO, None),
    ("traslado externo como evento", "MMT", {"traslados__externo": "evento"}, POS, None, 3),
    (
        "traslado externo excluido",
        "MMT",
        {"traslados__externo": "desenlace_excluido"},
        NE,
        DES,
        None,
    ),
    ("traslado interno continúa", "MIMMMMMM", {}, NEG, None, None),
    ("traslado interno como evento", "MI", {"traslados__interno": "evento"}, POS, None, 2),
    ("desenlace excluido", "MMX", {}, NE, DES, None),
    ("desenlace como no evento", "MMX", {"desenlaces_excluidos": "no_evento"}, NEG, None, None),
    ("desenlace como evento", "MMX", {"desenlaces_excluidos": "evento"}, POS, None, 3),
    ("evento formal", "MMFAAAAA", {}, POS, None, 3),
    ("evento formal y reingreso", "MMFMMMMM", {}, NEG, None, None),
    ("seguimiento incompleto", "MMMM", {}, NE, SI, None),
    ("evento antes del corte con reingreso posible", "MAAM", {}, NE, SI, None),
    ("evento antes del corte sin reingreso", "MAA", {"reingreso": "no_anula"}, POS, None, 2),
    ("ausencia al final sin confirmar", "MMMMMA", {}, NE, SI, None),
    ("ausencia al final confirmada", "MMMMMAA", {}, POS, None, 6),
    (
        "ausencia al final, solo el horizonte",
        "MMMMMA",
        {"seguimiento__exigir": "fin_horizonte"},
        NEG,
        None,
        None,
    ),
    ("periodo sin registro no observable", "MM-MMMMM", {}, NE, RNO, None),
    (
        "periodo sin registro como ausencia",
        "MM--MMMM",
        {"seguimiento__periodo_sin_registro": "ausencia", "reingreso": "no_anula"},
        POS,
        None,
        3,
    ),
    (
        "periodo extraordinario ignorado",
        "MMAMMMMMM",
        {"periodos_extraordinarios__periodos": [3]},
        NEG,
        None,
        None,
    ),
    (
        "periodo extraordinario contado",
        "MMAAMMMMM",
        {"periodos_extraordinarios__tratamiento": "contar", "reingreso": "no_anula"},
        POS,
        None,
        3,
    ),
]


@pytest.mark.parametrize(
    ("secuencia", "cambios", "estado", "motivo", "evento"),
    [pytest.param(*caso[1:], id=caso[0]) for caso in CASOS_PU09],
)
def test_pu09_cada_situacion_produce_el_estado_de_las_reglas(
    secuencia: str,
    cambios: dict[str, Any],
    estado: EstadoEtiqueta,
    motivo: Motivo | None,
    evento: int | None,
) -> None:
    etiqueta = _etiquetar(secuencia, **cambios)
    assert (etiqueta.estado, etiqueta.motivo, etiqueta.periodo_evento) == (estado, motivo, evento)


def test_pu09_el_ultimo_periodo_observado_es_el_ultimo_con_registro() -> None:
    assert _etiquetar("MMT", observable=8).ultimo_periodo_observado == 3
    assert _etiquetar("MMMMMMMM").ultimo_periodo_observado == 8


def test_pu09_horizonte_relativo_a_la_fecha_indice() -> None:
    # Horizonte de 3 periodos contado desde el periodo que indique cada ventana (H2.5).
    cambios: dict[str, Any] = {"horizonte": {"periodos": 3, "desde": "fecha_indice"}}
    # Desde el ingreso: el evento del periodo 2 se confirma y el reingreso del 4
    # queda fuera del horizonte de 3 periodos, así que no lo anula.
    assert _etiquetar("MAAMMMMM", desde=0, **cambios).periodo_evento == 2
    etiqueta = _etiquetar("MMMMAAAA", desde=2, **cambios)
    assert (etiqueta.estado, etiqueta.periodo_evento) == (POS, 5)
    # Desde el periodo 1, el horizonte (2 a 4) termina antes de la primera ausencia.
    assert _etiquetar("MMMMAAAA", desde=1, **cambios).estado is NEG


# Propiedades del constructor sobre historiales arbitrarios.
historiales = st.text(alphabet="MAPRTX-", min_size=1, max_size=10)


@given(secuencia=historiales, extra=st.integers(min_value=0, max_value=3))
def test_propiedades_de_cualquier_etiqueta(secuencia: str, extra: int) -> None:
    observable = len(secuencia) + extra
    etiqueta = _etiquetar(secuencia, observable=observable)
    assert (etiqueta.estado is POS) == (etiqueta.periodo_evento is not None)
    assert (etiqueta.estado is NE) == (etiqueta.motivo is not None)
    if etiqueta.periodo_evento is not None:
        assert 1 <= etiqueta.periodo_evento <= 6  # dentro del horizonte
    registrados = [p for p, letra in enumerate(secuencia, start=1) if letra != "-"]
    assert etiqueta.ultimo_periodo_observado == (max(registrados) if registrados else None)


@given(prefijo=st.text(alphabet="MAPR", min_size=7, max_size=7), cola=historiales)
def test_lo_posterior_al_horizonte_y_la_confirmacion_no_cambia_la_etiqueta(
    prefijo: str, cola: str
) -> None:
    # Horizonte de 6 y un periodo de confirmación: nada después del periodo 7 cuenta.
    corto = _etiquetar(prefijo, observable=12)
    largo = _etiquetar(prefijo + cola, observable=12)
    assert (corto.estado, corto.motivo, corto.periodo_evento) == (
        largo.estado,
        largo.motivo,
        largo.periodo_evento,
    )


# construir_objetivo sobre una tabla.
COLUMNAS = ColumnasHistorial(("seudonimo",), "cohorte", "ciclo", "estado")


def _tabla(historiales_por_unidad: dict[str, tuple[str, str]]) -> pd.DataFrame:
    filas = [
        {"seudonimo": unidad, "cohorte": cohorte, "ciclo": periodo, "estado": CODIGOS[letra]}
        for unidad, (cohorte, secuencia) in historiales_por_unidad.items()
        for periodo, letra in enumerate(secuencia, start=1)
        if letra != "-"
    ]
    return pd.DataFrame(filas)


def test_construir_usa_el_ultimo_periodo_observable_de_cada_cohorte() -> None:
    tabla = _tabla(
        {
            "a": ("2014-1", "MMMMMMMM"),
            "b": ("2014-1", "MMT"),
            "c": ("2017-1", "MMMM"),
            "d": ("2017-1", "MMMA"),
        }
    )
    resultado = construir_objetivo(tabla, COLUMNAS, _definicion())
    estados = dict(
        zip(resultado.registros["seudonimo"], resultado.registros[COLUMNA_ESTADO], strict=True)
    )
    assert estados == {
        "a": "negativo",
        "b": "no_etiquetable",
        "c": "no_etiquetable",
        "d": "no_etiquetable",
    }


def test_construir_aplica_la_poblacion_inicial_y_las_cohortes() -> None:
    tabla = _tabla(
        {
            "a": ("2014-1", "MMMMMMMM"),
            "b": ("2014-1", "AMMMMMMM"),
            "c": ("2015-1", "MMMMMMMM"),
        }
    )
    resultado = construir_objetivo(tabla, COLUMNAS, _definicion())
    assert (len(resultado.registros), resultado.fuera_de_poblacion) == (2, 1)
    admitidos = construir_objetivo(tabla, COLUMNAS, _definicion(poblacion__inicial="admitidos"))
    assert (len(admitidos.registros), admitidos.fuera_de_poblacion) == (3, 0)
    solo_2014 = construir_objetivo(tabla, COLUMNAS, _definicion(poblacion__cohortes=["2014-1"]))
    assert list(solo_2014.registros["seudonimo"]) == ["a"]
    assert solo_2014.fuera_de_cohortes == 1


def test_construir_por_estudiante_y_carrera() -> None:
    tabla = _tabla({"a": ("2014-1", "MMMMMMMM")})
    otra = tabla.copy()
    otra["estado"] = ["matriculado", "matriculado"] + ["no_matriculado"] * 6
    tabla["carrera"], otra["carrera"] = "C1", "C2"
    ambas = pd.concat([tabla, otra], ignore_index=True)
    with pytest.raises(ConfiguracionInvalida, match="más de un estado en el mismo periodo"):
        construir_objetivo(ambas, COLUMNAS, _definicion())
    definicion = _definicion(unidad={"tipo": "estudiante_carrera", "columna_carrera": "carrera"})
    columnas = ColumnasHistorial(("seudonimo", "carrera"), "cohorte", "ciclo", "estado")
    resultado = construir_objetivo(ambas, columnas, definicion)
    assert list(resultado.registros[COLUMNA_ESTADO]) == ["negativo", "positivo"]


def test_construir_rechaza_codigos_sin_categoria_y_unidades_en_dos_cohortes() -> None:
    tabla = _tabla({"a": ("2014-1", "MMMMMMMM")})
    tabla.loc[3, "estado"] = "codigo_nuevo"
    with pytest.raises(ConfiguracionInvalida, match="codigo_nuevo"):
        construir_objetivo(tabla, COLUMNAS, _definicion())
    tabla = _tabla({"a": ("2014-1", "MMMMMMMM")})
    tabla.loc[3, "cohorte"] = "2014-2"
    with pytest.raises(ConfiguracionInvalida, match="cohortes"):
        construir_objetivo(tabla, COLUMNAS, _definicion())


def test_el_horizonte_relativo_exige_el_periodo_de_inicio() -> None:
    tabla = _tabla({"a": ("2014-1", "MMMMMMMM")})
    relativo = _definicion(horizonte={"periodos": 3, "desde": "fecha_indice"})
    with pytest.raises(ConfiguracionInvalida, match="cada ventana"):
        construir_objetivo(tabla, COLUMNAS, relativo)
    assert len(construir_objetivo(tabla, COLUMNAS, relativo, desde=2).registros) == 1
    with pytest.raises(ConfiguracionInvalida, match="no depende de la ventana"):
        construir_objetivo(tabla, COLUMNAS, _definicion(), desde=2)


# PU-12 (con el cambio CP-08).
def _registros_con_no_etiquetables() -> pd.DataFrame:
    tabla = _tabla(
        {
            "a": ("2014-1", "MMMMMMMM"),
            "b": ("2014-1", "MMAAAAAA"),
            "c": ("2014-1", "MMT"),
            "d": ("2014-1", "MM-MMMMM"),
            "e": ("2014-2", "MMMMMMMM"),
            "f": ("2014-2", "MMMMMMMX"),
        }
    )
    return construir_objetivo(tabla, COLUMNAS, _definicion()).registros


def test_pu12_los_no_etiquetables_nunca_llegan_al_modelado() -> None:
    registros = _registros_con_no_etiquetables()
    modelado = para_modelado(registros)
    assert set(modelado["seudonimo"]) == {"a", "b", "e", "f"}
    assert "no_etiquetable" not in set(modelado[COLUMNA_ESTADO])


def test_pu12_se_cuentan_por_cohorte_y_motivo_y_se_marca_el_analisis_de_sensibilidad() -> None:
    resumen = resumir_no_etiquetables(_registros_con_no_etiquetables(), "cohorte", nivel=0.2)
    primera, segunda = resumen
    assert (primera.cohorte, primera.unidades, primera.no_etiquetables) == ("2014-1", 4, 2)
    assert dict(primera.por_motivo) == {"resultado_no_observable": 2}
    assert primera.proporcion == pytest.approx(0.5)
    assert primera.requiere_analisis_sensibilidad
    assert (segunda.no_etiquetables, segunda.requiere_analisis_sensibilidad) == (0, False)


@given(
    estados=st.lists(st.sampled_from(["positivo", "negativo", "no_etiquetable"]), min_size=1),
    nivel=st.floats(min_value=0.01, max_value=1.0),
)
def test_pu12_la_marca_coincide_con_superar_el_nivel(estados: list[str], nivel: float) -> None:
    registros = pd.DataFrame(
        {
            "cohorte": "2014-1",
            COLUMNA_ESTADO: estados,
            COLUMNA_MOTIVO: [
                "seguimiento_incompleto" if e == "no_etiquetable" else None for e in estados
            ],
        }
    )
    (resumen,) = resumir_no_etiquetables(registros, "cohorte", nivel)
    proporcion = estados.count("no_etiquetable") / len(estados)
    assert resumen.proporcion == pytest.approx(proporcion)
    assert resumen.requiere_analisis_sensibilidad == (proporcion > nivel)


def test_el_historial_sintetico_se_etiqueta_completo() -> None:
    historial = generar_historial(120, semilla=4)
    columnas = ColumnasHistorial(("codigo_estudiante",), "cohorte", "ciclo", "estado_matricula")
    resultado = construir_objetivo(historial, columnas, _definicion())
    assert len(resultado.registros) == historial["codigo_estudiante"].nunique()
    assert set(resultado.registros[COLUMNA_ESTADO]) <= {e.value for e in EstadoEtiqueta}


# Una definición incompleta no se construye.
SECCIONES = {
    "evento": "DP-01a",
    "unidad": "DP-01b",
    "poblacion": "DP-01c",
    "horizonte": "DP-01e",
    "fechado_evento": "DP-01f",
    "pausas": "DP-01g",
    "retiro_en_periodo": "DP-01h",
    "traslados": "DP-01i",
    "reingreso": "DP-01j",
    "periodos_extraordinarios": "DP-01k",
    "desenlaces_excluidos": "DP-01l",
    "seguimiento": "DP-01m",
    "catalogo_estados": "DP-01",
    "no_etiquetables": "DP-18",
}


@pytest.mark.parametrize("seccion", sorted(SECCIONES))
def test_sin_una_seccion_la_definicion_se_rechaza(seccion: str) -> None:
    datos = _datos_ejemplo()
    del datos[seccion]
    with pytest.raises(ConfiguracionInvalida, match=f"falta la sección '{seccion}'"):
        definicion_desde_datos(EJEMPLO, datos)


@pytest.mark.parametrize(("seccion", "decision"), sorted(SECCIONES.items()))
def test_una_seccion_nula_detiene_el_programa_nombrando_su_decision(
    seccion: str, decision: str
) -> None:
    datos = _datos_ejemplo()
    datos[seccion] = None
    with pytest.raises(DecisionPendiente) as error:
        definicion_desde_datos(EJEMPLO, datos)
    assert error.value.decision == decision


@pytest.mark.parametrize(
    ("seccion", "campo", "decision"),
    [
        ("evento", "periodos_sin_matricula", "DP-01a"),
        ("horizonte", "periodos", "DP-01e"),
        ("traslados", "externo", "DP-01i"),
        ("seguimiento", "periodo_sin_registro", "DP-01m"),
        ("no_etiquetables", "nivel_analisis_sensibilidad", "DP-18"),
    ],
)
def test_un_campo_nulo_o_ausente_no_toma_un_valor_por_omision(
    seccion: str, campo: str, decision: str
) -> None:
    datos = _datos_ejemplo()
    datos[seccion][campo] = None
    with pytest.raises(DecisionPendiente) as error:
        definicion_desde_datos(EJEMPLO, datos)
    assert error.value.decision == decision
    del datos[seccion][campo]
    with pytest.raises(ConfiguracionInvalida, match=f"le falta '{campo}'"):
        definicion_desde_datos(EJEMPLO, datos)


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"evento__periodos_sin_matricula": 0}, "mayor o igual a 1"),
        ({"horizonte__desde": "graduacion"}, "no es válido"),
        ({"pausas": {"tratamiento": "ausencia", "limite_periodos": 2}}, "solo se usa con"),
        ({"pausas": {"tratamiento": "neutral"}}, "le falta 'limite_periodos'"),
        ({"retiro_en_periodo": "no_observable"}, "no es válido"),
        ({"traslados__externo": "matricula"}, "no es válido"),
        ({"unidad__tipo": "estudiante_carrera"}, "columna_carrera"),
        ({"poblacion__cohortes": []}, "lista no vacía"),
        ({"catalogo_estados": {"matriculado": "otra"}}, "no es válido"),
        ({"catalogo_estados": {"no_matriculado": "ausencia"}}, "categoría 'matricula'"),
        ({"no_etiquetables__tratamiento": "supervivencia"}, "solo admite"),
        ({"no_etiquetables__nivel_analisis_sensibilidad": 1.5}, r"\(0, 1\]"),
        ({"version_objetivo": 2}, "version_objetivo"),
        ({"clave_extra": 1}, "claves desconocidas"),
    ],
)
def test_una_definicion_mal_formada_se_rechaza(cambios: dict[str, Any], mensaje: str) -> None:
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        _definicion(**cambios)


def test_la_definicion_del_proyecto_no_existe_mientras_dp01_siga_abierta(tmp_path: Path) -> None:
    with pytest.raises(DecisionPendiente) as error:
        cargar_definicion_objetivo(tmp_path / ARCHIVO_DEL_PROYECTO)
    assert error.value.decision == "DP-01"


def test_el_ejemplo_esta_rotulado_como_ficticio() -> None:
    definicion = cargar_definicion_objetivo(EJEMPLO)
    assert definicion.ficticio
    assert "EJEMPLO FICTICIO" in EJEMPLO.read_text(encoding="utf-8")
