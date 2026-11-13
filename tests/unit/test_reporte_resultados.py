"""Rótulo de datos sintéticos y reporte de resultados (F3.7).

PI-16: un reporte generado con datos sintéticos lleva el rótulo en los gráficos y las
exportaciones, y la exportación sin rótulo se rechaza (RNF-19). El reporte comparativo
tiene lo que pide RF-M6-07 y no contiene seudónimos (RF-M6-04). Los resultados son
escritos a mano (EJEMPLO FICTICIO).
"""

from __future__ import annotations

from typing import Any

import pytest

from fixtures import resultados_ficticios as ficticios
from suficiencia.application.contratos import ReporteResultados, TablaReporte
from suficiencia.application.reporte_resultados import (
    LIMITACIONES,
    LIMITACIONES_VALIDACION,
    construir_reporte,
    construir_reporte_validacion,
    exigir_rotulos,
)
from suficiencia.domain.trazabilidad.rotulo import (
    CAMPO_ORIGEN,
    LEYENDA_SINTETICA,
    ROTULO_SINTETICO,
    OrigenDatos,
    RotuloFaltante,
    exigir_rotulo_tabla,
    exigir_rotulo_texto,
    origen_de_registro,
)
from suficiencia.ui import graficos


def _reporte(origen: str = "sintetico") -> ReporteResultados:
    return construir_reporte(
        ficticios.evaluacion(origen), ficticios.comparacion(origen), ficticios.explicacion(origen)
    )


# --- Regla del rótulo (dominio) -------------------------------------------------------


def test_un_registro_sin_origen_declarado_se_trata_como_sintetico() -> None:
    assert origen_de_registro({}) is OrigenDatos.SINTETICO
    assert origen_de_registro({CAMPO_ORIGEN: "sintetico"}) is OrigenDatos.SINTETICO
    assert origen_de_registro({CAMPO_ORIGEN: "real"}) is OrigenDatos.REAL


@pytest.mark.parametrize(
    ("columnas", "valores"),
    [(["a"], []), (["a", CAMPO_ORIGEN], [ROTULO_SINTETICO, ""]), (["a", CAMPO_ORIGEN], ["real"])],
)
def test_pi16_tabla_sintetica_sin_rotulo_se_rechaza(
    columnas: list[str], valores: list[Any]
) -> None:
    with pytest.raises(RotuloFaltante):
        exigir_rotulo_tabla("t", columnas, valores, OrigenDatos.SINTETICO)


def test_pi16_texto_sintetico_debe_empezar_con_la_leyenda() -> None:
    exigir_rotulo_texto("r", f"\n> **{LEYENDA_SINTETICA}**\n# Título", OrigenDatos.SINTETICO)
    with pytest.raises(RotuloFaltante):
        exigir_rotulo_texto("r", f"# Título\n{LEYENDA_SINTETICA}", OrigenDatos.SINTETICO)
    exigir_rotulo_texto("r", "# Título", OrigenDatos.REAL)
    exigir_rotulo_tabla("t", ["a"], [], OrigenDatos.REAL)


# --- Reporte (RF-M6-07, RF-M6-04, PI-16) ---------------------------------------------


def test_pi16_el_reporte_sintetico_lleva_la_leyenda_y_el_rotulo_en_cada_fila() -> None:
    reporte = _reporte()
    assert reporte.origen_datos == "sintetico" and reporte.leyenda == LEYENDA_SINTETICA
    assert reporte.texto.lstrip().startswith(f"> **{LEYENDA_SINTETICA}**")
    nombres = [t.nombre for t in reporte.tablas]
    assert nombres == [
        "metricas_prueba",
        "no_inferioridad",
        "controles",
        "importancia_bloques",
        "importancia_variables",
    ]
    for tabla in reporte.tablas:
        assert tabla.columnas[-1] == CAMPO_ORIGEN
        assert tabla.filas and all(fila[-1] == ROTULO_SINTETICO for fila in tabla.filas)
    exigir_rotulos(reporte)


def test_rf_m6_07_el_reporte_comparativo_tiene_sus_partes_y_ningun_seudonimo() -> None:
    texto = _reporte().texto
    for parte in (
        "Referencia R0: R0 (T3|A+F+S+B)",
        "R-ven-T1 (T1|A+F+S+B, lr)",
        "[-0.050; +0.150]",
        "Anticipación: 2 ventanas, 2 ciclos",
        "Bloques evitados: B, S",
        "C3_no_inferioridad_no_demostrada",
        "No se declara superioridad",
        "## Limitaciones",
        "## Interpretabilidad",
    ):
        assert parte in texto, parte
    assert all(limitacion in texto for limitacion in LIMITACIONES)
    columnas = {c for t in _reporte().tablas for c in t.columnas}
    assert not columnas & {"unidad", "seudonimo", "codigo_estudiante"}


def test_si_alguna_parte_es_sintetica_el_reporte_es_sintetico() -> None:
    mezcla = construir_reporte(
        ficticios.evaluacion("real"), ficticios.comparacion("sintetico"), None
    )
    assert mezcla.origen_datos == "sintetico"
    assert [t.nombre for t in mezcla.tablas] == ["metricas_prueba", "no_inferioridad", "controles"]
    real = _reporte("real")
    assert real.leyenda == "" and LEYENDA_SINTETICA not in real.texto


@pytest.mark.parametrize(
    "alterar",
    [
        lambda r: r.model_copy(update={"texto": r.texto.split("\n", 2)[2]}),
        lambda r: r.model_copy(
            update={
                "tablas": (
                    TablaReporte(nombre="sin_rotulo", titulo="t", columnas=("a",), filas=((1,),)),
                )
            }
        ),
        lambda r: r.model_copy(
            update={
                "tablas": (
                    r.tablas[0].model_copy(update={"filas": (r.tablas[0].filas[0][:-1] + ("",),)}),
                )
            }
        ),
    ],
)
def test_pi16_un_reporte_alterado_sin_rotulo_se_rechaza(alterar: Any) -> None:
    with pytest.raises(RotuloFaltante):
        exigir_rotulos(alterar(_reporte()))


# --- Gráficos (RF-UI-03, PI-16) -------------------------------------------------------


def _figuras(origen: str) -> list[Any]:
    return [
        graficos.figura_metricas(ficticios.evaluacion(origen), "auc_roc"),
        graficos.figura_no_inferioridad(ficticios.comparacion(origen)),
        graficos.figura_bloques(ficticios.explicacion(origen)),
    ]


def test_pi16_cada_grafico_sintetico_lleva_el_rotulo() -> None:
    for figura in _figuras("sintetico"):
        assert figura.layout.title.text.startswith("DATOS SINTÉTICOS · ")
        assert any(a.text == LEYENDA_SINTETICA for a in figura.layout.annotations)
    for figura in _figuras("real"):
        assert "SINTÉTICOS" not in figura.layout.title.text
        assert not figura.layout.annotations


def test_los_graficos_dibujan_lo_que_devolvieron_los_servicios() -> None:
    metricas, comparacion, bloques = _figuras("sintetico")
    assert list(metricas.data[0].y) == [0.7, 0.65, 0.72]
    assert list(metricas.data[0].error_y.array) == pytest.approx([0.05, 0.05, 0.05])
    assert comparacion.data[0].x == (0.05,)
    assert comparacion.layout.shapes[0].x0 == -0.05  # el margen −δ
    # Proporción de cada bloque en la importancia de su configuración.
    assert [t.name for t in bloques.data] == ["A", "F"]
    assert bloques.data[0].y == pytest.approx((0.75,))


# --- F4.1: reporte sin comparación y escenarios en validación ---------------------------


def test_reporte_sin_comparacion_lo_dice_y_no_tiene_sus_tablas() -> None:
    reporte = construir_reporte(ficticios.evaluacion(), None, None)
    assert "No hay una evaluación comparativa registrada" in reporte.texto
    assert [t.nombre for t in reporte.tablas] == ["metricas_prueba"]
    exigir_rotulos(reporte)


def test_rf_m4_10_y_14_reporte_de_validacion_por_ventana_y_conjunto() -> None:
    reporte = construir_reporte_validacion(ficticios.metricas())
    exigir_rotulos(reporte)  # PI-16
    assert reporte.texto.lstrip().startswith(f"> **{LEYENDA_SINTETICA}**")
    assert "## auc_roc por ventana y conjunto" in reporte.texto
    # Matriz de lr: T0 solo tiene A; T1 tiene A y A+F. svm solo existe en T1|A.
    assert "| Ventana | A | A+F |" in reporte.texto
    assert "| T0 | 0.550 | · |" in reporte.texto
    assert "| T1 | 0.620 | 0.640 |" in reporte.texto
    assert "| T0 | · | · |" in reporte.texto.split("**svm**")[1]
    assert all(limitacion in reporte.texto for limitacion in LIMITACIONES_VALIDACION)
    (tabla,) = reporte.tablas
    assert tabla.nombre == "validacion_escenarios"
    familias = {(f[0], f[3]) for f in tabla.filas}
    assert len(familias) == 13  # cinco familias en T1|A y cuatro en los otros dos
    assert len(tabla.filas) == 13 * 2  # dos métricas por corrida
    assert all(f[-1] == ROTULO_SINTETICO for f in tabla.filas)


def test_pi16_graficos_de_validacion_rotulados_con_los_valores_registrados() -> None:
    metricas = ficticios.metricas()
    matriz = graficos.figura_matriz_escenarios(metricas, "auc_roc", "rf")
    assert matriz.layout.title.text.startswith("DATOS SINTÉTICOS · ")
    assert list(matriz.data[0].y) == ["T0", "T1"] and list(matriz.data[0].x) == ["A", "A+F"]
    assert matriz.data[0].z[0][0] == pytest.approx(0.56) and matriz.data[0].z[0][1] is None
    familias = graficos.figura_familias(metricas, "T1|A", "auc_roc")
    assert list(familias.data[0].x) == ["lr", "rf", "xgboost", "lightgbm", "svm"]
    assert familias.data[0].y == pytest.approx((0.62, 0.63, 0.64, 0.65, 0.66))
    assert any(a.text == LEYENDA_SINTETICA for a in familias.layout.annotations)
    real = graficos.figura_familias(ficticios.metricas("real"), "T1|A", "auc_roc")
    assert "SINTÉTICOS" not in real.layout.title.text
