"""Estabilidad de la selección y de las explicaciones, y R-max, en la demostración (F4.2).

Con ``experimentos_estabilidad_ficticio.yaml``, que enciende las tres funciones
opcionales, la demostración construye R-max, describe en cuántos folds de desarrollo
cada escenario cumple el criterio y las métricas de prueba por cohorte (CMP-5), y
compara la importancia de los modelos de cada fold con la del congelado (RF-M5-06). Nada
de eso abre otra vez la prueba. Datos sintéticos y configuración ficticia.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from fixtures.generador_sintetico import COHORTES_AMPLIADAS, generar_historial
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    ResultadoDemostracionFinal,
    SolicitudDemostracionFinal,
    SolicitudEstabilidad,
)
from suficiencia.cli import SALIDA_ERROR, main
from suficiencia.domain.errores import ConfiguracionInvalida

EJEMPLOS = Path("config/ejemplos")
ESPACIOS_RAPIDOS = {
    "lr": {"C": [1.0], "max_iter": [1000]},
    "rf": {"n_estimators": [30], "max_depth": [4]},
    "xgboost": {"n_estimators": [30], "max_depth": [2]},
    "lightgbm": {"n_estimators": [30], "num_leaves": [7], "min_child_samples": [10]},
    "svm": {"C": [1.0]},
}
COHORTES_PRUEBA = {"2014-1", "2014-2"}


def _experimentos(raiz: Path, archivo: str) -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load((raiz / EJEMPLOS / archivo).read_text(encoding="utf-8"))
    for familia, espacio in ESPACIOS_RAPIDOS.items():
        datos["modelos"][familia]["espacio"] = copy.deepcopy(espacio)
    datos["intervalos"]["replicas"] = 200
    datos["interpretabilidad"].update(muestra_fondo=20, muestra_explicar=30, kernel_muestras=40)
    return datos


@pytest.fixture(scope="module")
def proyecto(tmp_path_factory: pytest.TempPathFactory) -> Path:
    raiz = Path(__file__).resolve().parents[2]
    destino = tmp_path_factory.mktemp("estabilidad")
    (destino / EJEMPLOS).mkdir(parents=True)
    for archivo in (raiz / EJEMPLOS).glob("*.yaml"):
        (destino / EJEMPLOS / archivo.name).write_bytes(archivo.read_bytes())
    (destino / "config" / "proyecto.yaml").write_bytes((raiz / "config/proyecto.yaml").read_bytes())
    for nombre in ("experimentos_ficticio.yaml", "experimentos_estabilidad_ficticio.yaml"):
        (destino / "config" / nombre).write_text(
            yaml.safe_dump(_experimentos(raiz, nombre), allow_unicode=True), encoding="utf-8"
        )
    datos = destino / "data" / "sintetico" / "ampliado.csv"
    datos.parent.mkdir(parents=True)
    generar_historial(700, semilla=11, cohortes=COHORTES_AMPLIADAS).to_csv(datos, index=False)
    return destino


@pytest.fixture(scope="module")
def demostracion(proyecto: Path) -> ResultadoDemostracionFinal:
    return crear_servicios(proyecto).evaluacion_final.demostracion(
        SolicitudDemostracionFinal(
            archivo=proyecto / "data" / "sintetico" / "ampliado.csv",
            diccionario=proyecto / EJEMPLOS / "diccionario_sintetico.yaml",
            definicion=proyecto / EJEMPLOS / "objetivo_ficticio.yaml",
            poblaciones=proyecto / EJEMPLOS / "poblaciones_ampliado_ficticio.yaml",
            escenarios=proyecto / EJEMPLOS / "escenarios_ficticio.yaml",
            experimentos=proyecto / "config" / "experimentos_estabilidad_ficticio.yaml",
            protocolo=proyecto / EJEMPLOS / "protocolo_evaluacion_final_ficticio.yaml",
            seleccion_escenarios=("T1|A", "T0|A"),
        )
    )


def test_r_max_se_construye_congela_y_evalua_en_el_mismo_acceso(
    demostracion: ResultadoDemostracionFinal,
) -> None:
    configuraciones = {c.identificador: c for c in demostracion.evaluacion.configuraciones}
    assert "R-max" in configuraciones
    r_max = configuraciones["R-max"]
    assert r_max.rol == "control"
    # R-max sale de los escenarios pedidos (DP-19d).
    assert r_max.escenario in {"T1|A", "T0|A"}
    assert demostracion.evaluacion.accesos_a_la_prueba == 1
    assert "R-max" in {c.codigo for c in demostracion.comparacion.controles}


def test_estabilidad_de_la_seleccion_por_fold_sin_abrir_la_prueba(
    demostracion: ResultadoDemostracionFinal,
) -> None:
    estabilidad = demostracion.estabilidad
    assert estabilidad is not None
    assert estabilidad.accesos_a_la_prueba == 1
    assert estabilidad.ficticio and estabilidad.origen_datos == "sintetico"
    frecuencias = {f.escenario: f for f in estabilidad.frecuencias}
    assert set(frecuencias) == {"T1|A", "T0|A"}
    folds = {f.folds for f in estabilidad.frecuencias}
    assert folds == {len(estabilidad.reglas)} == {6}
    for f in estabilidad.frecuencias:
        assert 0 <= f.elegido <= f.cumple <= f.evaluables <= f.folds
    # La regla elige a lo sumo un escenario por fold.
    elegidos = sum(f.elegido for f in estabilidad.frecuencias)
    assert elegidos == sum(r.escenario is not None for r in estabilidad.reglas)
    # Cada fold valida una sola cohorte de desarrollo, nunca una de prueba.
    cohortes_folds = {r.cohorte for r in estabilidad.reglas}
    assert len(cohortes_folds) == 6 and not cohortes_folds & COHORTES_PRUEBA
    # Métricas de prueba por cohorte, de todas las configuraciones evaluadas.
    assert {c.cohorte for c in estabilidad.por_cohorte} == COHORTES_PRUEBA
    identificadores = {c.identificador for c in demostracion.evaluacion.configuraciones}
    assert {c.identificador for c in estabilidad.por_cohorte} == identificadores
    for configuracion in demostracion.evaluacion.configuraciones:
        filas = [
            c for c in estabilidad.por_cohorte if c.identificador == configuracion.identificador
        ]
        assert sum(c.filas for c in filas) == configuracion.filas
        assert sum(c.eventos for c in filas) == configuracion.eventos


def test_estabilidad_de_las_explicaciones_entre_folds(
    demostracion: ResultadoDemostracionFinal,
) -> None:
    for configuracion in demostracion.explicacion.configuraciones:
        estabilidad = configuracion.estabilidad
        assert estabilidad is not None
        assert estabilidad.folds == len(estabilidad.bloques_por_fold) == 6
        for bloques in [*estabilidad.bloques_por_fold.values(), estabilidad.bloques_congelado]:
            assert sum(bloques.values()) == pytest.approx(1.0)
        definidas = [c for c in estabilidad.correlaciones.values() if c is not None]
        assert all(-1 <= c <= 1 for c in definidas)
        if definidas:
            assert estabilidad.correlacion_minima == pytest.approx(min(definidas))


def test_el_reporte_incluye_la_estabilidad(demostracion: ResultadoDemostracionFinal) -> None:
    from suficiencia.application.reporte_resultados import construir_reporte

    reporte = construir_reporte(
        demostracion.evaluacion,
        demostracion.comparacion,
        demostracion.explicacion,
        demostracion.estabilidad,
    )
    assert reporte.texto.startswith("> **")
    assert "## Estabilidad de la selección (CMP-5)" in reporte.texto
    assert "sin inferencia entre cohortes" in reporte.texto
    nombres = {t.nombre for t in reporte.tablas}
    assert {"estabilidad_seleccion", "regla_por_fold", "metricas_por_cohorte"} <= nombres
    assert "estabilidad_explicaciones" in nombres
    for tabla in reporte.tablas:
        assert "origen_datos" in tabla.columnas


def test_la_estabilidad_apagada_se_rechaza(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    servicios = crear_servicios(proyecto)
    with pytest.raises(ConfiguracionInvalida, match="no está habilitada"):
        servicios.evaluacion_final.estabilidad(
            SolicitudEstabilidad(
                evaluacion="EXP-inexistente",
                experimentos=proyecto / "config" / "experimentos_ficticio.yaml",
            )
        )
    argumentos = ["--raiz", str(proyecto), "evaluacion", "estabilidad", "--evaluacion", "x"]
    argumentos += ["--experimentos", str(proyecto / "config" / "experimentos_ficticio.yaml")]
    assert main(argumentos) == SALIDA_ERROR
    assert "comparacion.estabilidad" in capsys.readouterr().err
