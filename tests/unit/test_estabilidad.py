"""Estabilidad descriptiva de la selección y de las explicaciones, y R-max (F4.2).

Los resultados por fold son valores escritos a mano (EJEMPLO FICTICIO), no salen de
ningún modelo. El criterio es el del protocolo ficticio de la demostración de F3.4.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
import yaml

from suficiencia.application.demostracion_protocolo import _SinAjusteFicticio
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.evaluacion.comparacion import (
    definicion_comparacion_desde_datos,
    definicion_referencia_desde_datos,
    elegir_r_max,
)
from suficiencia.domain.evaluacion.estabilidad import (
    correlacion_rangos,
    estabilidad_explicaciones,
    estabilidad_seleccion,
    proporciones,
)
from suficiencia.domain.evaluacion.interpretabilidad import (
    definicion_interpretabilidad_desde_datos,
)
from suficiencia.domain.evaluacion.suficiencia import (
    Estimacion,
    ResultadoEscenario,
    criterio_desde_datos,
)

EJEMPLOS = Path("config/ejemplos")
PROCEDIMIENTOS = {"sin_ajuste_ficticio": _SinAjusteFicticio()}


def _criterio(raiz: Path) -> Any:
    """Límite inferior del AUC mayor que 0,5; desempate: ventana más temprana."""
    datos = yaml.safe_load(
        (raiz / EJEMPLOS / "protocolo_evaluacion_final_ficticio.yaml").read_text(encoding="utf-8")
    )
    return criterio_desde_datos(datos["criterio_suficiencia"])


def _resultado(escenario: str, inferior: float | None) -> ResultadoEscenario:
    ventana, conjunto = escenario.split("|")
    metricas = {}
    if inferior is not None:
        metricas = {
            "auc_roc": Estimacion(inferior + 0.1, inferior, inferior + 0.2),
            "brier_escalado": Estimacion(0.1, 0.0, 0.2),
        }
    return ResultadoEscenario(
        escenario, conjunto, int(ventana[1]), len(conjunto.split("+")), metricas, {}
    )


def test_la_regla_se_aplica_en_cada_fold_y_se_cuenta(raiz: Path) -> None:
    por_fold = {
        1: [_resultado("T0|A", 0.55), _resultado("T1|A+F", 0.60)],  # elige T0|A
        2: [_resultado("T0|A", 0.45), _resultado("T1|A+F", 0.58)],  # elige T1|A+F
        3: [_resultado("T0|A", 0.40), _resultado("T1|A+F", 0.30)],  # ninguno
        4: [_resultado("T0|A", None), _resultado("T1|A+F", 0.52)],  # T0|A no evaluable
    }
    frecuencias, reglas = estabilidad_seleccion(_criterio(raiz), por_fold, PROCEDIMIENTOS)
    por_escenario = {f.escenario: f for f in frecuencias}
    t0, t1 = por_escenario["T0|A"], por_escenario["T1|A+F"]
    assert (t0.folds, t0.evaluables, t0.cumple, t0.elegido) == (4, 3, 1, 1)
    assert (t1.folds, t1.evaluables, t1.cumple, t1.elegido) == (4, 4, 3, 2)
    assert [(r.fold, r.escenario) for r in reglas] == [
        (1, "T0|A"),
        (2, "T1|A+F"),
        (3, None),
        (4, "T1|A+F"),
    ]
    assert reglas[2].estado == "ningun_escenario_cumple"


def test_la_estabilidad_exige_folds_con_los_mismos_escenarios(raiz: Path) -> None:
    with pytest.raises(ConfiguracionInvalida, match="No hay folds"):
        estabilidad_seleccion(_criterio(raiz), {}, PROCEDIMIENTOS)
    distintos = {1: [_resultado("T0|A", 0.6)], 2: [_resultado("T1|A", 0.6)]}
    with pytest.raises(ConfiguracionInvalida, match="mismos escenarios"):
        estabilidad_seleccion(_criterio(raiz), distintos, PROCEDIMIENTOS)


def test_correlacion_de_rangos() -> None:
    a = {"x": 3.0, "y": 2.0, "z": 1.0}
    assert correlacion_rangos(a, a) == pytest.approx(1.0)
    assert correlacion_rangos(a, {"x": 1.0, "y": 2.0, "z": 3.0}) == pytest.approx(-1.0)
    # Con empates, rangos promediados: (1, 2.5, 2.5) frente a (3, 2, 1).
    assert correlacion_rangos({"x": 1.0, "y": 2.0, "z": 2.0}, a) == pytest.approx(-math.sqrt(3) / 2)
    # Mismo orden con escalas distintas: Spearman 1 (Pearson no lo sería).
    assert correlacion_rangos({"x": 1.0, "y": 2.0, "z": 10.0}, {"x": 1.0, "y": 3.0, "z": 4.0}) == (
        pytest.approx(1.0)
    )
    assert correlacion_rangos({"x": 1.0}, {"x": 2.0}) is None
    assert correlacion_rangos({"x": 1.0, "y": 1.0}, {"x": 1.0, "y": 2.0}) is None
    with pytest.raises(ConfiguracionInvalida, match="mismas variables"):
        correlacion_rangos({"x": 1.0, "y": 2.0}, {"x": 1.0, "w": 2.0})


def test_proporciones_y_estabilidad_de_las_explicaciones() -> None:
    assert proporciones({"A": 3.0, "B": 1.0}) == {"A": 0.75, "B": 0.25}
    assert proporciones({"A": 0.0, "B": 0.0}) == {"A": 0, "B": 0}
    congelado = {"x": 3.0, "y": 2.0, "z": 1.0}
    resumen = estabilidad_explicaciones(
        congelado,
        {"A": 4.0, "B": 2.0},
        {1: congelado, 2: {"x": 1.0, "y": 2.0, "z": 3.0}},
        {1: {"A": 3.0, "B": 1.0}, 2: {"A": 1.0, "B": 1.0}},
    )
    assert resumen.bloques_congelado == pytest.approx({"A": 2 / 3, "B": 1 / 3})
    assert resumen.rango_bloques == {"A": (0.5, 0.75), "B": (0.25, 0.5)}
    assert resumen.correlaciones == pytest.approx({1: 1.0, 2: -1.0})
    assert resumen.correlacion_media == pytest.approx(0.0)
    assert resumen.correlacion_minima == pytest.approx(-1.0)
    with pytest.raises(ConfiguracionInvalida, match="Faltan las importancias"):
        estabilidad_explicaciones(congelado, {"A": 1.0}, {}, {})


def test_r_max_elige_el_mejor_y_desempata_por_escenario_y_familia() -> None:
    valores = {
        "T0|A": {"lr": 0.70, "rf": 0.72},
        "T1|A+F": {"lr": 0.72, "rf": 0.65},
    }
    orden = ["T0|A", "T1|A+F"]
    # Empate en 0,72: gana el escenario que va antes.
    assert elegir_r_max(valores, orden, ["lr", "rf"], True) == ("T0|A", "rf")
    # Menor es mejor: el 0,65.
    assert elegir_r_max(valores, orden, ["lr", "rf"], False) == ("T1|A+F", "rf")
    # Empate dentro del escenario: la familia que va antes.
    assert elegir_r_max({"T0|A": {"lr": 0.7, "rf": 0.7}}, ["T0|A"], ["rf", "lr"], True) == (
        "T0|A",
        "rf",
    )
    with pytest.raises(ConfiguracionInvalida):
        elegir_r_max({}, orden, ["lr"], True)
    with pytest.raises(ConfiguracionInvalida):
        elegir_r_max({"T0|A": {"lr": float("nan")}}, ["T0|A"], ["lr"], True)


def test_las_funciones_de_f42_estan_apagadas_por_omision(raiz: Path) -> None:
    datos = yaml.safe_load(
        (raiz / EJEMPLOS / "experimentos_ficticio.yaml").read_text(encoding="utf-8")
    )
    ventanas = ["T0", "T1", "T2", "T3"]
    for seccion, campo in (
        ("referencia", "r_max"),
        ("comparacion", "estabilidad"),
        ("interpretabilidad", "estabilidad"),
    ):
        del datos[seccion][campo]
    assert definicion_referencia_desde_datos(datos["referencia"], ventanas).r_max is False
    assert definicion_comparacion_desde_datos(datos["comparacion"]).estabilidad is False
    interpretabilidad = definicion_interpretabilidad_desde_datos(datos["interpretabilidad"])
    assert interpretabilidad.estabilidad_folds is False


def test_las_funciones_de_f42_validan_sus_valores(raiz: Path) -> None:
    datos = yaml.safe_load(
        (raiz / EJEMPLOS / "experimentos_estabilidad_ficticio.yaml").read_text(encoding="utf-8")
    )
    ventanas = ["T0", "T1", "T2", "T3"]
    assert definicion_referencia_desde_datos(datos["referencia"], ventanas).r_max is True
    assert definicion_comparacion_desde_datos(datos["comparacion"]).estabilidad is True
    assert definicion_interpretabilidad_desde_datos(datos["interpretabilidad"]).estabilidad_folds
    with pytest.raises(ConfiguracionInvalida, match="r_max"):
        definicion_referencia_desde_datos({**datos["referencia"], "r_max": "si"}, ventanas)
    with pytest.raises(ConfiguracionInvalida, match="estabilidad"):
        definicion_comparacion_desde_datos({**datos["comparacion"], "estabilidad": 1})
    with pytest.raises(ConfiguracionInvalida, match="estabilidad"):
        definicion_interpretabilidad_desde_datos(
            {**datos["interpretabilidad"], "estabilidad": "semillas"}
        )
    with pytest.raises(ConfiguracionInvalida, match="bloque"):
        definicion_interpretabilidad_desde_datos(
            {
                k: v
                for k, v in {**datos["interpretabilidad"], "niveles": ["global"]}.items()
                if k != "local"
            }
        )
