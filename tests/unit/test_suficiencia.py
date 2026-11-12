"""Motor de la regla de suficiencia (H2.6): PU-04 y lectura del criterio.

Todos los criterios, límites y resultados de este archivo son EJEMPLOS FICTICIOS
inventados para probar el motor. DP-08 sigue abierta.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fixtures.protocolo_de_prueba import (
    PROCEDIMIENTO_FICTICIO,
    PROCEDIMIENTOS_FICTICIOS,
    datos_protocolo_ficticio,
)
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.suficiencia import (
    PROCEDIMIENTOS_IMPLEMENTADOS,
    CriterioSuficiencia,
    EstadoEscenario,
    EstadoSuficiencia,
    Estimacion,
    EvaluacionEscenario,
    ProcedimientoInvalido,
    ResultadoEscenario,
    aplicar_regla,
    criterio_desde_datos,
    evaluar_escenario,
)


def _datos_criterio() -> dict[str, Any]:
    datos = datos_protocolo_ficticio()["criterio_suficiencia"]
    assert isinstance(datos, dict)
    return copy.deepcopy(datos)


def _criterio(**cambios: Any) -> CriterioSuficiencia:
    datos = _datos_criterio()
    datos.update(cambios)
    return criterio_desde_datos(datos)


def _e(puntual: float, inferior: float | None, superior: float | None) -> Estimacion:
    return Estimacion(puntual, inferior, superior)


def _resultado(
    escenario: str,
    ventana: int,
    bloques: int,
    a_inferior: float | None,
    diferencia_inferior: float | None,
) -> ResultadoEscenario:
    """Resultado ficticio: métrica_a con su límite inferior y la diferencia frente al comparador."""
    metricas = {}
    if a_inferior is not None:
        metricas["metrica_a"] = _e(a_inferior + 0.05, a_inferior, a_inferior + 0.1)
    diferencias = {}
    if diferencia_inferior is not None:
        diferencias[("metrica_a", "comparador_ficticio")] = {
            "referencia": _e(
                diferencia_inferior + 0.02, diferencia_inferior, diferencia_inferior + 0.04
            )
        }
    conjunto = escenario.split("-", 1)[-1]
    return ResultadoEscenario(escenario, conjunto, ventana, bloques, metricas, diferencias)


# El criterio ficticio exige: límite inferior de metrica_a >= 0.7 y límite inferior
# de la diferencia frente al comparador > -0.05. Desempate: ventana más temprana y
# luego menos bloques.
CUMPLE = (0.75, -0.01)
FALLA_UMBRAL = (0.65, -0.01)
FALLA_NO_INFERIORIDAD = (0.75, -0.08)


# PU-04 -------------------------------------------------------------------------


def test_pu04_devuelve_el_escenario_esperado() -> None:
    resultados = [
        _resultado("T0-A", 0, 1, *FALLA_UMBRAL),
        _resultado("T1-AF", 1, 2, *CUMPLE),
        _resultado("T1-A", 1, 1, *CUMPLE),
        _resultado("T2-A", 2, 1, *CUMPLE),
    ]
    resultado = aplicar_regla(_criterio(), resultados, PROCEDIMIENTOS_FICTICIOS)
    # Ventana más temprana: T1-AF y T1-A; menos bloques: T1-A.
    assert resultado.estado is EstadoSuficiencia.ESCENARIO_SUFICIENTE
    assert resultado.escenario == "T1-A"
    assert resultado.cumplen == ("T1-A", "T1-AF", "T2-A")


def test_pu04_devuelve_ningun_escenario_cumple() -> None:
    resultados = [
        _resultado("T0-A", 0, 1, *FALLA_UMBRAL),
        _resultado("T1-A", 1, 1, *FALLA_NO_INFERIORIDAD),
        _resultado("T2-A", 2, 1, *FALLA_UMBRAL),
    ]
    resultado = aplicar_regla(_criterio(), resultados, PROCEDIMIENTOS_FICTICIOS)
    assert resultado.estado is EstadoSuficiencia.NINGUNO_CUMPLE
    assert resultado.escenario is None
    assert resultado.cumplen == ()
    assert all(e.estado is EstadoEscenario.NO_CUMPLE for e in resultado.evaluaciones)


def test_un_empate_que_el_desempate_no_resuelve_no_se_fuerza() -> None:
    resultados = [_resultado("T1-AF", 1, 2, *CUMPLE), _resultado("T1-AS", 1, 2, *CUMPLE)]
    resultado = aplicar_regla(_criterio(), resultados, PROCEDIMIENTOS_FICTICIOS)
    assert resultado.estado is EstadoSuficiencia.EMPATE_SIN_RESOLVER
    assert resultado.escenario is None
    assert resultado.empatados == ("T1-AF", "T1-AS")


def test_el_orden_del_desempate_lo_fija_el_criterio() -> None:
    resultados = [_resultado("T1-AF", 1, 2, *CUMPLE), _resultado("T2-A", 2, 1, *CUMPLE)]
    temprana = aplicar_regla(_criterio(), resultados, PROCEDIMIENTOS_FICTICIOS)
    bloques = aplicar_regla(
        _criterio(desempate=["menos_bloques", "ventana_mas_temprana"]),
        resultados,
        PROCEDIMIENTOS_FICTICIOS,
    )
    assert temprana.escenario == "T1-AF"
    assert bloques.escenario == "T2-A"


def test_desempate_por_metrica_respeta_su_sentido() -> None:
    criterio = _criterio(desempate=["mejor_metrica:metrica_a"])
    resultados = [_resultado("T1-A", 1, 1, 0.80, -0.01), _resultado("T2-A", 2, 1, 0.75, -0.01)]
    assert aplicar_regla(criterio, resultados, PROCEDIMIENTOS_FICTICIOS).escenario == "T1-A"


def test_cada_condicion_puede_hacer_fallar_al_escenario() -> None:
    criterio = _criterio()
    assert evaluar_escenario(criterio, _resultado("x", 1, 1, *CUMPLE)).estado is (
        EstadoEscenario.CUMPLE
    )
    for valores in (FALLA_UMBRAL, FALLA_NO_INFERIORIDAD):
        evaluacion = evaluar_escenario(criterio, _resultado("x", 1, 1, *valores))
        assert evaluacion.estado is EstadoEscenario.NO_CUMPLE
        assert [c.cumple for c in evaluacion.condiciones].count(False) == 1


def test_un_valor_faltante_nunca_cuenta_como_cumple() -> None:
    criterio = _criterio()
    sin_diferencia = evaluar_escenario(criterio, _resultado("x", 1, 1, 0.75, None))
    assert sin_diferencia.estado is EstadoEscenario.NO_EVALUABLE
    assert "falta" in sin_diferencia.condiciones[1].motivo
    sin_limite = ResultadoEscenario("x", "A", 1, 1, {"metrica_a": _e(0.8, None, None)}, {})
    assert evaluar_escenario(criterio, sin_limite).estado is EstadoEscenario.NO_EVALUABLE
    # Si otra condición falla, el escenario no cumple aunque falte un valor.
    assert (
        evaluar_escenario(criterio, _resultado("x", 1, 1, 0.65, None)).estado
        is EstadoEscenario.NO_CUMPLE
    )


@pytest.mark.parametrize(
    ("inclusivo", "esperado"), [(True, EstadoEscenario.CUMPLE), (False, EstadoEscenario.NO_CUMPLE)]
)
def test_igualar_el_limite_depende_de_inclusivo(inclusivo: bool, esperado: EstadoEscenario) -> None:
    datos = _datos_criterio()
    datos["condiciones"] = [datos["condiciones"][0]]
    datos["condiciones"][0]["inclusivo"] = inclusivo
    criterio = criterio_desde_datos(datos)
    exacto = ResultadoEscenario("x", "A", 1, 1, {"metrica_a": _e(0.75, 0.7, 0.8)}, {})
    assert evaluar_escenario(criterio, exacto).estado is esperado


def test_metrica_donde_menor_es_mejor() -> None:
    datos = _datos_criterio()
    datos["condiciones"] = [
        {
            "tipo": "umbral",
            "metrica": "metrica_b",
            "estadistico": "limite_superior",
            "limite": 0.2,
            "inclusivo": True,
            "comparador": None,
        },
        {
            "tipo": "no_inferioridad",
            "metrica": "metrica_b",
            "estadistico": "limite_superior",
            "limite": 0.03,
            "inclusivo": False,
            "comparador": "comparador_ficticio",
        },
    ]
    criterio = criterio_desde_datos(datos)

    def con(superior: float, diferencia_superior: float) -> ResultadoEscenario:
        return ResultadoEscenario(
            "x",
            "A",
            1,
            1,
            {"metrica_b": _e(superior - 0.01, None, superior)},
            {
                ("metrica_b", "comparador_ficticio"): {
                    "referencia": _e(diferencia_superior - 0.01, None, diferencia_superior)
                }
            },
        )

    assert evaluar_escenario(criterio, con(0.18, 0.02)).estado is EstadoEscenario.CUMPLE
    assert evaluar_escenario(criterio, con(0.25, 0.02)).estado is EstadoEscenario.NO_CUMPLE
    assert evaluar_escenario(criterio, con(0.18, 0.04)).estado is EstadoEscenario.NO_CUMPLE


# Grupos de comparadores y desempate por orden de conjuntos (ajuste de H2.6) ----------


def _con_comparadores(
    escenario: str, ventana: int, diferencias: dict[str, float | None]
) -> ResultadoEscenario:
    """Escenario que cumple el umbral, con una diferencia por cada comparador del grupo."""
    grupo = {
        comparador: _e(0.0 if inferior is None else inferior + 0.02, inferior, None)
        for comparador, inferior in diferencias.items()
    }
    return ResultadoEscenario(
        escenario,
        escenario.split("-", 1)[-1],
        ventana,
        1,
        {"metrica_a": _e(0.8, 0.75, 0.85)},
        {("metrica_a", "comparador_ficticio"): grupo},
    )


def test_la_no_inferioridad_se_exige_frente_a_todos_los_comparadores_del_grupo() -> None:
    criterio = _criterio()
    todos = _con_comparadores("T0-A", 0, {"s+T0": -0.01, "s+T1": -0.02, "s+T2": -0.03})
    assert evaluar_escenario(criterio, todos).estado is EstadoEscenario.CUMPLE
    uno_falla = _con_comparadores("T0-A", 0, {"s+T0": -0.01, "s+T1": -0.08, "s+T2": -0.03})
    evaluacion = evaluar_escenario(criterio, uno_falla)
    assert evaluacion.estado is EstadoEscenario.NO_CUMPLE
    assert evaluacion.condiciones[1].valor == pytest.approx(-0.08)
    assert "peor: s+T1" in evaluacion.condiciones[1].motivo


def test_un_grupo_vacio_o_incompleto_nunca_cumple() -> None:
    criterio = _criterio()
    vacio = _con_comparadores("T1-A", 1, {})
    assert evaluar_escenario(criterio, vacio).estado is EstadoEscenario.NO_EVALUABLE
    sin_limite = _con_comparadores("T1-A", 1, {"s+T1": -0.01, "s+T2": None})
    evaluacion = evaluar_escenario(criterio, sin_limite)
    assert evaluacion.estado is EstadoEscenario.NO_EVALUABLE
    assert "s+T2" in evaluacion.condiciones[1].motivo


def test_cada_escenario_puede_tener_distinto_numero_de_comparadores() -> None:
    # Como en el manuscrito: el conjunto más completo de su ventana y de las posteriores.
    resultados = [
        _con_comparadores("T0-A", 0, {"s+T0": -0.01, "s+T1": -0.01, "s+T2": -0.01}),
        _con_comparadores("T2-A", 2, {"s+T2": -0.01}),
    ]
    resultado = aplicar_regla(_criterio(), resultados, PROCEDIMIENTOS_FICTICIOS)
    assert resultado.cumplen == ("T0-A", "T2-A")
    assert resultado.escenario == "T0-A"


def test_desempate_por_un_orden_explicito_de_conjuntos() -> None:
    resultados = [
        _resultado("T1-A+S", 1, 2, *CUMPLE),
        _resultado("T1-A+B", 1, 2, *CUMPLE),
        _resultado("T1-A+F", 1, 2, *CUMPLE),
    ]
    sin_orden = aplicar_regla(_criterio(), resultados, PROCEDIMIENTOS_FICTICIOS)
    assert sin_orden.estado is EstadoSuficiencia.EMPATE_SIN_RESOLVER
    orden = "orden_de_conjuntos:A,A+F,A+B,A+S"
    con_orden = aplicar_regla(
        _criterio(desempate=["ventana_mas_temprana", "menos_bloques", orden]),
        resultados,
        PROCEDIMIENTOS_FICTICIOS,
    )
    assert con_orden.escenario == "T1-A+F"
    # Un conjunto fuera de la lista no se desempata con esa clave: el empate sigue.
    incompleto = aplicar_regla(
        _criterio(desempate=["orden_de_conjuntos:A,A+B"]), resultados, PROCEDIMIENTOS_FICTICIOS
    )
    assert incompleto.estado is EstadoSuficiencia.EMPATE_SIN_RESOLVER


@pytest.mark.parametrize(
    ("clave", "mensaje"),
    [
        ("orden_de_conjuntos:", "separados por comas"),
        ("orden_de_conjuntos:A,,A+F", "separados por comas"),
        ("orden_de_conjuntos:A,A+F,A", "repite un conjunto"),
    ],
)
def test_ordenes_de_conjuntos_mal_formados(clave: str, mensaje: str) -> None:
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        _criterio(desempate=[clave])


# Multiplicidad -----------------------------------------------------------------


def test_el_proyecto_no_implementa_ningun_procedimiento_de_multiplicidad() -> None:
    assert dict(PROCEDIMIENTOS_IMPLEMENTADOS) == {}
    with pytest.raises(DecisionPendiente) as error:
        aplicar_regla(
            _criterio(), [_resultado("T1-A", 1, 1, *CUMPLE)], PROCEDIMIENTOS_IMPLEMENTADOS
        )
    assert error.value.decision == "DP-08f"


class _QuitaTodo:
    def confirmar(
        self, evaluaciones: tuple[EvaluacionEscenario, ...], resultados: Mapping[str, Any]
    ) -> frozenset[str]:
        return frozenset()


class _Inventa:
    def confirmar(
        self, evaluaciones: tuple[EvaluacionEscenario, ...], resultados: Mapping[str, Any]
    ) -> frozenset[str]:
        return frozenset(e.escenario for e in evaluaciones)


def test_un_procedimiento_puede_quitar_escenarios_pero_no_agregarlos() -> None:
    resultados = [_resultado("T1-A", 1, 1, *CUMPLE), _resultado("T0-A", 0, 1, *FALLA_UMBRAL)]
    quitado = aplicar_regla(_criterio(), resultados, {PROCEDIMIENTO_FICTICIO: _QuitaTodo()})
    assert quitado.estado is EstadoSuficiencia.NINGUNO_CUMPLE
    assert quitado.cumplen == ("T1-A",)
    assert quitado.confirmados == ()
    with pytest.raises(ProcedimientoInvalido, match="T0-A"):
        aplicar_regla(_criterio(), resultados, {PROCEDIMIENTO_FICTICIO: _Inventa()})


@given(
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=3),
            st.integers(min_value=1, max_value=4),
            st.booleans(),
            st.booleans(),
        ),
        min_size=1,
        max_size=8,
    )
)
def test_pu04_propiedad_el_suficiente_siempre_cumple(
    escenarios: list[tuple[int, int, bool, bool]],
) -> None:
    resultados = [
        _resultado(
            f"E{i}",
            ventana,
            bloques,
            0.75 if umbral else 0.65,
            -0.01 if no_inferior else -0.08,
        )
        for i, (ventana, bloques, umbral, no_inferior) in enumerate(escenarios)
    ]
    resultado = aplicar_regla(_criterio(), resultados, PROCEDIMIENTOS_FICTICIOS)
    cumplen = {f"E{i}" for i, (_, _, u, n) in enumerate(escenarios) if u and n}
    assert set(resultado.cumplen) == cumplen
    if not cumplen:
        assert resultado.estado is EstadoSuficiencia.NINGUNO_CUMPLE
    elif resultado.estado is EstadoSuficiencia.ESCENARIO_SUFICIENTE:
        assert resultado.escenario in cumplen
        elegido = next(r for r in resultados if r.escenario == resultado.escenario)
        assert elegido.orden_ventana == min(
            r.orden_ventana for r in resultados if r.escenario in cumplen
        )
    else:
        assert resultado.estado is EstadoSuficiencia.EMPATE_SIN_RESOLVER
        assert set(resultado.empatados) <= cumplen


def test_resultados_vacios_o_repetidos_se_rechazan() -> None:
    with pytest.raises(ConfiguracionInvalida, match="No hay resultados"):
        aplicar_regla(_criterio(), [], PROCEDIMIENTOS_FICTICIOS)
    uno = _resultado("T1-A", 1, 1, *CUMPLE)
    with pytest.raises(ConfiguracionInvalida, match="dos veces"):
        aplicar_regla(_criterio(), [uno, uno], PROCEDIMIENTOS_FICTICIOS)


def test_una_estimacion_incoherente_se_rechaza() -> None:
    with pytest.raises(ConfiguracionInvalida, match="fuera de su intervalo"):
        Estimacion(0.5, 0.6, 0.7)
    with pytest.raises(ConfiguracionInvalida, match="no finito"):
        Estimacion(float("nan"), None, None)


# Lectura del criterio: nada tiene valor por omisión ---------------------------------


@pytest.mark.parametrize(
    ("ruta", "decision"),
    [
        (("metricas",), "DP-08a"),
        (("condiciones",), "DP-08b"),
        (("multiplicidad",), "DP-08f"),
        (("desempate",), "DP-08g"),
        (("condiciones", 0, "limite"), "DP-08c"),
        (("condiciones", 0, "inclusivo"), "DP-08c"),
        (("condiciones", 0, "estadistico"), "DP-08e"),
        (("condiciones", 1, "comparador"), "DP-08d"),
        (("metricas", 0, "sentido"), "DP-08a"),
    ],
)
def test_un_valor_nulo_nombra_la_decision_pendiente(ruta: tuple[Any, ...], decision: str) -> None:
    datos = _datos_criterio()
    destino: Any = datos
    for paso in ruta[:-1]:
        destino = destino[paso]
    destino[ruta[-1]] = None
    with pytest.raises(DecisionPendiente) as error:
        criterio_desde_datos(datos)
    assert error.value.decision == decision


@pytest.mark.parametrize("campo", ["metricas", "condiciones", "multiplicidad", "desempate"])
def test_un_campo_ausente_no_toma_un_valor_por_omision(campo: str) -> None:
    datos = _datos_criterio()
    del datos[campo]
    with pytest.raises(ConfiguracionInvalida, match=campo):
        criterio_desde_datos(datos)


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        ({"metricas": []}, "ninguna métrica"),
        ({"condiciones": []}, "ninguna condición"),
        ({"desempate": []}, "desempate"),
        ({"desempate": ["al_azar"]}, "desconocida"),
        ({"desempate": ["mejor_metrica:otra"]}, "no declarada"),
        ({"desempate": ["menos_bloques", "menos_bloques"]}, "repite"),
        ({"multiplicidad": " "}, "multiplicidad"),
        ({"extra": 1}, "desconocidos"),
    ],
)
def test_criterios_mal_formados(cambio: dict[str, Any], mensaje: str) -> None:
    datos = _datos_criterio()
    datos.update(cambio)
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        criterio_desde_datos(datos)


def test_condiciones_mal_formadas() -> None:
    datos = _datos_criterio()
    datos["condiciones"][0]["metrica"] = "no_declarada"
    with pytest.raises(ConfiguracionInvalida, match="no declarada"):
        criterio_desde_datos(datos)
    datos = _datos_criterio()
    datos["condiciones"][0]["comparador"] = "x"
    with pytest.raises(ConfiguracionInvalida, match="no lleva comparador"):
        criterio_desde_datos(datos)
    datos = _datos_criterio()
    datos["condiciones"][1]["limite"] = -0.1
    with pytest.raises(ConfiguracionInvalida, match="negativo"):
        criterio_desde_datos(datos)
    datos = _datos_criterio()
    datos["condiciones"][0]["tipo"] = "superioridad"
    with pytest.raises(ConfiguracionInvalida, match="Opciones"):
        criterio_desde_datos(datos)


def test_el_criterio_vuelve_a_sus_datos_sin_perder_nada() -> None:
    criterio = _criterio()
    assert criterio_desde_datos(criterio.a_datos()) == criterio
