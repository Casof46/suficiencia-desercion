"""Ventanas, conjuntos, escenarios y verificador de fuga (H2.2).

PU-01, PU-02, PU-03, PU-18 y PU-19 de la especificación, con variables
ficticias construidas en la propia prueba. Ninguna representa un dato real.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.construccion import (
    FugaTemporal,
    construir_escenarios,
    detectar_fugas,
    verificar_sin_fuga,
)
from suficiencia.domain.escenarios.modelo import (
    CODIGOS_VENTANA,
    Bloque,
    CatalogoVentanas,
    ConjuntoInformacion,
    Variable,
    Ventana,
    generar_conjuntos,
    orden_ventana,
    validar_variables,
)

FECHAS_FICTICIAS = {codigo: f"FICTICIA {codigo}" for codigo in CODIGOS_VENTANA}


def _catalogo() -> CatalogoVentanas:
    return CatalogoVentanas.desde_fechas_indice(dict(FECHAS_FICTICIAS))


def _v(nombre: str, bloque: str, ventana: str) -> Variable:
    return Variable(nombre, Bloque.desde_codigo(bloque), ventana)


VARIABLES_COMPLETAS = (
    _v("a0", "A", "T0"),
    _v("f0", "F", "T0"),
    _v("s0", "S", "T0"),
    _v("b0", "B", "T0"),
)


# PU-01 ----------------------------------------------------------------------


def test_pu01_se_generan_exactamente_los_8_conjuntos_y_todos_incluyen_a() -> None:
    conjuntos = generar_conjuntos()
    assert [c.codigo for c in conjuntos] == [
        "A",
        "A+F",
        "A+S",
        "A+B",
        "A+F+S",
        "A+F+B",
        "A+S+B",
        "A+F+S+B",
    ]
    assert all(Bloque.ACADEMICO in c.bloques for c in conjuntos)
    assert len({c.bloques for c in conjuntos}) == 8


def test_un_conjunto_sin_bloque_academico_se_rechaza() -> None:
    with pytest.raises(ConfiguracionInvalida, match="académico"):
        ConjuntoInformacion(frozenset({Bloque.FINANCIERO}))


# PU-18 ----------------------------------------------------------------------


def test_pu18_el_catalogo_genera_t0_a_t3_en_orden_con_su_fecha_indice() -> None:
    catalogo = _catalogo()
    assert [v.codigo for v in catalogo.ventanas] == ["T0", "T1", "T2", "T3"]
    assert [v.orden for v in catalogo.ventanas] == [0, 1, 2, 3]
    assert all(v.fecha_indice == f"FICTICIA {v.codigo}" for v in catalogo.ventanas)


@pytest.mark.parametrize("ventana_sin_fecha", CODIGOS_VENTANA)
def test_pu18_una_configuracion_sin_fecha_indice_se_rechaza(ventana_sin_fecha: str) -> None:
    fechas: dict[str, str | None] = dict(FECHAS_FICTICIAS)
    fechas[ventana_sin_fecha] = None
    with pytest.raises(DecisionPendiente) as error:
        CatalogoVentanas.desde_fechas_indice(fechas)
    assert error.value.decision == "DP-01d"
    assert ventana_sin_fecha in str(error.value)


def test_una_fecha_indice_vacia_tambien_es_una_decision_pendiente() -> None:
    with pytest.raises(DecisionPendiente, match="DP-01d"):
        Ventana("T1", "   ")


@pytest.mark.parametrize(
    "codigos",
    [("T0", "T1", "T2"), ("T1", "T0", "T2", "T3"), ("T0", "T1", "T2", "T3", "T3"), ()],
)
def test_un_catalogo_incompleto_o_desordenado_se_rechaza(codigos: tuple[str, ...]) -> None:
    with pytest.raises(ConfiguracionInvalida, match="T0, T1, T2 y T3"):
        CatalogoVentanas(tuple(Ventana(c, "FICTICIA") for c in codigos))


@pytest.mark.parametrize("codigo", ["T4", "t0", "", "T-1"])
def test_una_ventana_inexistente_se_rechaza(codigo: str) -> None:
    with pytest.raises(ConfiguracionInvalida, match="no existe"):
        orden_ventana(codigo)


# Matriz y PU-19 -------------------------------------------------------------


def test_la_matriz_tiene_32_escenarios_unicos() -> None:
    escenarios = construir_escenarios(_catalogo(), VARIABLES_COMPLETAS)
    assert len(escenarios) == 32
    assert len({e.codigo for e in escenarios}) == 32
    assert all(e.factible for e in escenarios)


def test_pu19_un_bloque_sin_variables_en_la_ventana_vuelve_no_factible_el_escenario() -> None:
    variables = (_v("a0", "A", "T0"), _v("f0", "F", "T0"), _v("b1", "B", "T1"))
    escenarios = {e.codigo: e for e in construir_escenarios(_catalogo(), variables)}
    assert not escenarios["T0|A+B"].factible
    assert escenarios["T0|A+B"].bloques_sin_variables == (Bloque.CONDUCTUAL,)
    assert escenarios["T1|A+B"].factible
    assert escenarios["T0|A+F"].factible
    # S no tiene ninguna variable: todo conjunto con S es no factible en todas las ventanas.
    con_s = [e for e in escenarios.values() if Bloque.SOCIOECONOMICO in e.conjunto.bloques]
    assert len(con_s) == 16
    assert not any(e.factible for e in con_s)


def test_cada_escenario_recibe_exactamente_las_variables_de_sus_bloques_disponibles() -> None:
    variables = (_v("a0", "A", "T0"), _v("a2", "A", "T2"), _v("f1", "F", "T1"))
    escenarios = {e.codigo: e for e in construir_escenarios(_catalogo(), variables)}
    assert escenarios["T0|A"].variables == ("a0",)
    assert escenarios["T0|A+F"].variables == ("a0",)
    assert escenarios["T1|A+F"].variables == ("a0", "f1")
    assert escenarios["T2|A"].variables == ("a0", "a2")
    assert escenarios["T3|A+F"].variables == ("a0", "a2", "f1")


def test_variables_repetidas_se_rechazan() -> None:
    with pytest.raises(ConfiguracionInvalida, match="repetidas: a0"):
        validar_variables((_v("a0", "A", "T0"), _v("a0", "F", "T1")))


# PU-02: prueba basada en propiedades ----------------------------------------

_variables = st.lists(
    st.builds(
        Variable,
        nombre=st.text(alphabet="abcdefghij_", min_size=1, max_size=8),
        bloque=st.sampled_from(list(Bloque)),
        ventana_minima=st.sampled_from(CODIGOS_VENTANA),
    ),
    max_size=25,
    unique_by=lambda v: v.nombre,
)


@given(_variables)
def test_pu02_ninguna_variable_aparece_antes_de_su_ventana_minima(
    variables: list[Variable],
) -> None:
    """Para cualquier conjunto de variables: k > j implica que no aparece en Tj."""
    escenarios = construir_escenarios(_catalogo(), variables)
    minima = {v.nombre: orden_ventana(v.ventana_minima) for v in variables}
    for escenario in escenarios:
        for nombre in escenario.variables:
            assert minima[nombre] <= escenario.ventana.orden
    assert detectar_fugas(escenarios, variables) == ()


@given(_variables)
def test_pu02_ninguna_variable_disponible_se_pierde(variables: list[Variable]) -> None:
    """La otra mitad de la propiedad: lo disponible y del conjunto siempre entra."""
    for escenario in construir_escenarios(_catalogo(), variables):
        esperadas = {
            v.nombre
            for v in variables
            if v.bloque in escenario.conjunto.bloques
            and orden_ventana(v.ventana_minima) <= escenario.ventana.orden
        }
        assert set(escenario.variables) == esperadas
        assert escenario.factible == all(
            any(v.bloque is b and v.nombre in esperadas for v in variables)
            for b in escenario.conjunto.bloques
        )


def test_pu02_variable_de_t2_nunca_en_t0_ni_t1() -> None:
    """El caso del criterio de aceptación de CU-04 (sección 9.3)."""
    variables = (*VARIABLES_COMPLETAS, _v("nota_t2", "A", "T2"))
    for escenario in construir_escenarios(_catalogo(), variables):
        assert ("nota_t2" in escenario.variables) == (escenario.ventana.codigo in {"T2", "T3"})


# PU-03: canario -------------------------------------------------------------


def test_pu03_el_canario_derivado_del_objetivo_solo_aparece_en_t3() -> None:
    """Una variable que contiene el resultado, marcada T3, nunca entra en T0 a T2."""
    variables = (*VARIABLES_COMPLETAS, _v("canario_objetivo", "A", "T3"))
    escenarios = construir_escenarios(_catalogo(), variables)
    for escenario in escenarios:
        assert ("canario_objetivo" in escenario.variables) == (escenario.ventana.codigo == "T3")
    verificar_sin_fuga(escenarios, variables)


def test_pu03_el_verificador_detecta_el_canario_insertado_en_un_escenario_temprano() -> None:
    """El verificador no confía en el constructor: revisa cada escenario."""
    variables = (*VARIABLES_COMPLETAS, _v("canario_objetivo", "A", "T3"))
    escenarios = list(construir_escenarios(_catalogo(), variables))
    t1_a = next(i for i, e in enumerate(escenarios) if e.codigo == "T1|A")
    escenarios[t1_a] = replace(
        escenarios[t1_a], variables=(*escenarios[t1_a].variables, "canario_objetivo")
    )
    with pytest.raises(FugaTemporal) as error:
        verificar_sin_fuga(escenarios, variables)
    assert [(f.escenario, f.variable) for f in error.value.fugas] == [("T1|A", "canario_objetivo")]
    assert "Acción sugerida" in str(error.value)


def test_el_verificador_rechaza_variables_desconocidas() -> None:
    escenarios = list(construir_escenarios(_catalogo(), VARIABLES_COMPLETAS))
    escenarios[0] = replace(escenarios[0], variables=("sin_definicion",))
    fugas = detectar_fugas(escenarios, VARIABLES_COMPLETAS)
    assert [(f.variable, f.ventana_minima) for f in fugas] == [("sin_definicion", "desconocida")]
