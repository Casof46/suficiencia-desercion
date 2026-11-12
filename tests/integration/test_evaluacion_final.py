"""Selección, congelamiento y evaluación final con el historial sintético ampliado (F3.4).

- RF-M4-07 y RF-M4-08: modelo y umbral se eligen con las probabilidades de
  validación, según las reglas declaradas (DP-10, DP-06).
- PI-10: seleccionar no accede a la prueba (registro de accesos vacío).
- PU-05: sin protocolo aprobado, la evaluación final se rechaza sin abrir la prueba.
- PI-09: una configuración distinta de la congelada, o un modelo cambiado, se rechazan.
- PI-15 y RF-M4-09: la prueba se abre una sola vez para todas las configuraciones;
  repetir exige justificación, que queda registrada.
- Demostración completa en un proyecto temporal, sin tocar el registro del proyecto.

Todo es sintético y ficticio: ningún resultado es una conclusión sobre el método.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import secrets
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml
from sklearn.metrics import roc_auc_score

from fixtures.generador_sintetico import COHORTES_AMPLIADAS, generar_historial
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    SolicitudConstruirPoblaciones,
    SolicitudDemostracionFinal,
    SolicitudEntrenar,
    SolicitudEvaluacionFinal,
    SolicitudSeleccionar,
)
from suficiencia.application.demostracion_protocolo import _SinAjusteFicticio
from suficiencia.application.servicio_evaluacion_final import EvaluacionFinalRepetida
from suficiencia.application.servicio_experimentos import configuraciones_congeladas
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.cli import SALIDA_CORRECTA, main
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.particion import OPERACION_EVALUACION_FINAL
from suficiencia.domain.evaluacion.congelamiento import (
    ConfiguracionCongelable,
    HuellaNoCoincide,
    RolConfiguracion,
    configuracion_desde_datos,
    congelar,
    preparar_evaluacion_final,
)
from suficiencia.domain.evaluacion.protocolo import (
    SinProtocoloVigente,
    aprobar,
    contenido_desde_datos,
    guardar_borrador,
)
from suficiencia.domain.trazabilidad.registros import TipoRegistro

EJEMPLOS = Path("config/ejemplos")
ESCENARIOS = ("T1|A+F", "T2|A+F+S+B")
ESPACIOS_RAPIDOS = {
    "lr": {"C": [0.1, 1.0], "max_iter": [1000]},
    "rf": {"n_estimators": [30], "max_depth": [4]},
    "xgboost": {"n_estimators": [30], "max_depth": [2]},
    "lightgbm": {"n_estimators": [30], "num_leaves": [7], "min_child_samples": [10]},
    "svm": {"C": [1.0]},
}


def _experimentos(raiz: Path, **cambios: Any) -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load(
        (raiz / EJEMPLOS / "experimentos_ficticio.yaml").read_text(encoding="utf-8")
    )
    for familia, espacio in ESPACIOS_RAPIDOS.items():
        datos["modelos"][familia]["espacio"] = copy.deepcopy(espacio)
    datos["intervalos"]["replicas"] = 200
    datos.update(cambios)
    return datos


def _crear_proyecto(destino: Path) -> Path:
    raiz = Path(__file__).resolve().parents[2]
    (destino / EJEMPLOS).mkdir(parents=True)
    for archivo in (raiz / EJEMPLOS).iterdir():
        (destino / EJEMPLOS / archivo.name).write_bytes(archivo.read_bytes())
    (destino / "config" / "proyecto.yaml").write_bytes((raiz / "config/proyecto.yaml").read_bytes())
    (destino / "config" / "experimentos_rapido.yaml").write_text(
        yaml.safe_dump(_experimentos(raiz), allow_unicode=True), encoding="utf-8"
    )
    datos = destino / "data" / "sintetico" / "ampliado.csv"
    datos.parent.mkdir(parents=True)
    generar_historial(700, semilla=11, cohortes=COHORTES_AMPLIADAS).to_csv(datos, index=False)
    return destino


def _comunes(proyecto: Path, experimentos: str = "experimentos_rapido.yaml") -> dict[str, Any]:
    return {
        "archivo": proyecto / "data" / "sintetico" / "ampliado.csv",
        "diccionario": proyecto / EJEMPLOS / "diccionario_sintetico.yaml",
        "definicion": proyecto / EJEMPLOS / "objetivo_ficticio.yaml",
        "poblaciones": proyecto / EJEMPLOS / "poblaciones_ampliado_ficticio.yaml",
        "escenarios": proyecto / EJEMPLOS / "escenarios_ficticio.yaml",
        "experimentos": proyecto / "config" / experimentos,
        "clave_efimera": True,
    }


@pytest.fixture(scope="module")
def proyecto(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _crear_proyecto(tmp_path_factory.mktemp("proyecto"))


@pytest.fixture(scope="module")
def entrenado(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Any, str]:
    """Proyecto con clave de sesión: partición construida y cinco familias entrenadas."""
    proyecto = _crear_proyecto(tmp_path_factory.mktemp("entrenado"))
    servicios = crear_servicios(proyecto, secrets.token_bytes(32))
    poblaciones = servicios.escenarios.construir_poblaciones(
        SolicitudConstruirPoblaciones(
            archivo=_comunes(proyecto)["archivo"],
            diccionario=_comunes(proyecto)["diccionario"],
            definicion=_comunes(proyecto)["definicion"],
            configuracion=_comunes(proyecto)["poblaciones"],
            clave_efimera=True,
        )
    )
    servicios.experimentos.entrenar(
        SolicitudEntrenar(**_comunes(proyecto), seleccion_escenarios=ESCENARIOS)
    )
    return proyecto, servicios, poblaciones.carpeta_particion


def test_seleccion_con_validacion_segun_las_reglas_y_sin_tocar_la_prueba(
    entrenado: tuple[Path, Any, str],
) -> None:
    proyecto, servicios, _ = entrenado
    resultado = servicios.experimentos.seleccionar(
        SolicitudSeleccionar(**_comunes(proyecto), seleccion_escenarios=ESCENARIOS)
    )
    repositorio = servicios.reportes.repositorio()
    assert repositorio.listar(TipoRegistro.ACCESO) == []  # PI-10
    corridas = {
        (r.contenido["configuracion"]["escenario"], r.contenido["configuracion"]["familia"]): r
        for r in repositorio.listar(TipoRegistro.EXPERIMENTO)
        if r.contenido["configuracion"].get("tipo") == "entrenamiento_desarrollo"
    }
    for elegido in resultado.escenarios:
        valores = {}
        predicciones = {}
        for familia in ("lr", "rf", "xgboost", "lightgbm", "svm"):
            contenido = corridas[(elegido.escenario, familia)].contenido
            tabla = pd.read_csv(proyecto / contenido["resultados"]["carpeta"] / "predicciones.csv")
            predicciones[familia] = tabla
            valores[familia] = roc_auc_score(tabla["objetivo"], tabla["probabilidad"])
        assert elegido.valores == pytest.approx(valores)
        mejor = max(valores.values())
        esperado = next(f for f in valores if valores[f] >= mejor - 0.01)  # margen del ejemplo
        assert elegido.familia == esperado
        # Umbral: cuantil 1 − q de las probabilidades de validación de la elegida.
        p = predicciones[elegido.familia]["probabilidad"].to_numpy()
        assert elegido.umbral == pytest.approx(float(np.quantile(p, 1 - 0.2)))
        candidata = elegido.configuracion_candidata
        assert candidata["algoritmo"] == elegido.familia
        assert candidata["umbral"] == elegido.umbral
        assert (proyecto / elegido.carpeta / "modelo_final.joblib").exists()
    registro = next(
        r.contenido
        for r in repositorio.listar(TipoRegistro.EXPERIMENTO)
        if r.contenido["identificador"] == resultado.identificador_registro
    )
    assert registro["configuracion"]["tipo"] == "seleccion_desarrollo"
    assert registro["modo"] == "exploratorio"


def test_seleccion_exige_las_cinco_familias(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    servicios.experimentos.entrenar(
        SolicitudEntrenar(
            **_comunes(proyecto), seleccion_escenarios=("T0|A",), seleccion_familias=("lr",)
        )
    )
    with pytest.raises(ConfiguracionInvalida, match="faltan corridas"):
        servicios.experimentos.seleccionar(
            SolicitudSeleccionar(**_comunes(proyecto), seleccion_escenarios=("T0|A",))
        )


def test_reentrenamiento_ultimo_fold_usa_el_modelo_del_ultimo_fold(
    entrenado: tuple[Path, Any, str],
) -> None:
    proyecto, servicios, _ = entrenado
    datos = _experimentos(Path(__file__).resolve().parents[2])
    datos["seleccion"]["reentrenamiento"] = "ultimo_fold"
    (proyecto / "config" / "experimentos_rapido.yaml").write_text(
        yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8"
    )
    try:
        resultado = servicios.experimentos.seleccionar(
            SolicitudSeleccionar(**_comunes(proyecto), seleccion_escenarios=("T1|A+F",))
        )
    finally:
        (proyecto / "config" / "experimentos_rapido.yaml").write_text(
            yaml.safe_dump(_experimentos(Path(__file__).resolve().parents[2])),
            encoding="utf-8",
        )
    elegido = resultado.escenarios[0]
    assert elegido.reentrenamiento == "ultimo_fold"
    assert "2013-2" not in elegido.configuracion_candidata["datos_reentrenamiento"]


def _congelar_seleccion(servicios: Any, proyecto: Path) -> tuple[str, ...]:
    """Aprueba el protocolo ficticio en este registro de prueba y congela la selección."""
    resultado = servicios.experimentos.seleccionar(
        SolicitudSeleccionar(**_comunes(proyecto), seleccion_escenarios=ESCENARIOS)
    )
    repositorio = servicios.reportes.repositorio()
    contenido = contenido_desde_datos(
        yaml.safe_load(
            (proyecto / EJEMPLOS / "protocolo_evaluacion_final_ficticio.yaml").read_text(
                encoding="utf-8"
            )
        )
    )
    borrador = guardar_borrador(historial_protocolo(repositorio), contenido, None)
    repositorio.agregar(borrador)
    repositorio.agregar(
        aprobar(historial_protocolo(repositorio), 1, borrador.huella, "prueba", [], None).aprobacion
    )
    identificadores = []
    for elegido in resultado.escenarios:
        configuracion = ConfiguracionCongelable(
            identificador=f"SEL-{elegido.escenario}",
            rol=RolConfiguracion.SELECCIONADA,
            version_protocolo=1,
            ficticio=True,
            **{
                **elegido.configuracion_candidata,
                "variables": tuple(elegido.configuracion_candidata["variables"]),
            },
        )
        repositorio.agregar(
            congelar(
                configuracion,
                historial_protocolo(repositorio),
                configuraciones_congeladas(repositorio),
            )
        )
        identificadores.append(configuracion.identificador)
    return tuple(identificadores)


def test_evaluacion_final_unica_con_huellas_y_repeticion_justificada(
    entrenado: tuple[Path, Any, str],
) -> None:
    proyecto, servicios, particion = entrenado
    repositorio = servicios.reportes.repositorio()

    def solicitud(ids: tuple[str, ...], justificacion: str | None = None) -> Any:
        return SolicitudEvaluacionFinal(
            **_comunes(proyecto),
            particion=Path(particion),
            configuraciones=ids,
            version_protocolo=1,
            justificacion_repeticion=justificacion,
        )

    with pytest.raises(SinProtocoloVigente):  # PU-05
        servicios.evaluacion_final.evaluar(solicitud(("SEL-T1|A+F",)))
    assert repositorio.listar(TipoRegistro.ACCESO) == []
    identificadores = _congelar_seleccion(servicios, proyecto)
    # PI-09: una configuración distinta de la congelada se rechaza.
    congelada = next(
        g.contenido["configuracion"] for g in repositorio.listar(TipoRegistro.CONGELAMIENTO)
    )
    modificada = dataclasses.replace(configuracion_desde_datos(congelada), semilla=1)
    with pytest.raises(HuellaNoCoincide):
        preparar_evaluacion_final(
            historial_protocolo(repositorio), [modificada], configuraciones_congeladas(repositorio)
        )
    procedimientos = {"sin_ajuste_ficticio": _SinAjusteFicticio()}
    resultado = servicios.evaluacion_final.evaluar(solicitud(identificadores), procedimientos)
    assert resultado.accesos_a_la_prueba == 1  # PI-15: una apertura para todas
    assert [c.identificador for c in resultado.configuraciones] == list(identificadores)
    assert resultado.estado_regla in {
        "escenario_suficiente",
        "ningun_escenario_cumple",
        "empate_sin_resolver",
    }
    for c in resultado.configuraciones:
        assert c.filas > 0 and 0 < c.prevalencia < 1
        auc = c.metricas["auc_roc"]
        assert auc.puntual is not None and auc.limite_inferior is not None
        assert auc.limite_superior is not None
        assert auc.limite_inferior <= auc.puntual <= auc.limite_superior
        assert set(c.con_umbral) == {"accuracy", "precision", "recall", "f1"}
    registro = next(
        r.contenido
        for r in repositorio.listar(TipoRegistro.EXPERIMENTO)
        if r.contenido["identificador"] == resultado.identificador_registro
    )
    assert registro["modo"] == "confirmatorio"
    assert registro["version_protocolo"] == "1"
    # RF-M4-09: repetir sin justificación se rechaza antes de abrir la prueba.
    with pytest.raises(EvaluacionFinalRepetida):
        servicios.evaluacion_final.evaluar(solicitud(identificadores), procedimientos)
    accesos = [
        g.contenido
        for g in repositorio.listar(TipoRegistro.ACCESO)
        if g.contenido["operacion"] == OPERACION_EVALUACION_FINAL
    ]
    assert len(accesos) == 1
    otra = servicios.evaluacion_final.evaluar(
        solicitud(identificadores, "Repetición de prueba del programa"), procedimientos
    )
    assert otra.accesos_a_la_prueba == 2
    ultimo = repositorio.listar(TipoRegistro.ACCESO)[-1].contenido
    assert "REPETICIÓN justificada: Repetición de prueba del programa" in ultimo["motivo"]
    # Un modelo modificado después de congelarse se rechaza.
    datos = configuracion_desde_datos(congelada)
    archivo = proyecto / json.loads(datos.datos_reentrenamiento)["modelo"]
    original = archivo.read_bytes()
    try:
        archivo.write_bytes(original + b"0")
        with pytest.raises(ConfiguracionInvalida, match="huella"):
            servicios.evaluacion_final.evaluar(solicitud(identificadores, "otra"), procedimientos)
    finally:
        archivo.write_bytes(original)


def test_demostracion_completa_sin_tocar_el_registro_del_proyecto(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    servicios = crear_servicios(proyecto)
    antes = len(servicios.reportes.repositorio().listar(TipoRegistro.EXPERIMENTO))
    comunes = _comunes(proyecto)
    resultado = servicios.evaluacion_final.demostracion(
        SolicitudDemostracionFinal(
            archivo=comunes["archivo"],
            diccionario=comunes["diccionario"],
            definicion=comunes["definicion"],
            poblaciones=comunes["poblaciones"],
            escenarios=comunes["escenarios"],
            experimentos=comunes["experimentos"],
            protocolo=proyecto / EJEMPLOS / "protocolo_evaluacion_final_ficticio.yaml",
            seleccion_escenarios=("T1|A",),
        )
    )
    pasos = {p.titulo: p.resultado for p in resultado.pasos}
    assert (
        "Accesos a la prueba hasta aquí: 0 (PI-10)"
        in pasos["Seleccionar modelo y umbral solo con desarrollo"]
    )
    assert pasos["Evaluación final sin protocolo aprobado"].startswith("Rechazado")
    assert pasos["Evaluar una configuración con el umbral cambiado"].startswith("Rechazado")
    assert pasos["Repetir la evaluación final sin justificación"].startswith("Rechazado")
    assert "1 acceso permitido" in pasos["Registro de accesos al terminar"]
    assert resultado.evaluacion.accesos_a_la_prueba == 1
    assert resultado.evaluacion.ficticio
    despues = len(servicios.reportes.repositorio().listar(TipoRegistro.EXPERIMENTO))
    assert despues == antes
    # La línea de comandos de la demostración.
    argumentos = ["--raiz", str(proyecto), "evaluacion", "demostracion", str(comunes["archivo"])]
    for opcion in ("diccionario", "definicion", "poblaciones", "escenarios", "experimentos"):
        argumentos += [f"--{opcion}", str(comunes[opcion])]
    argumentos += [
        "--protocolo",
        str(proyecto / EJEMPLOS / "protocolo_evaluacion_final_ficticio.yaml"),
        "--escenario",
        "T1|A",
    ]
    assert main(argumentos) == SALIDA_CORRECTA
    salida = capsys.readouterr().out
    assert "DEMOSTRACIÓN con datos SINTÉTICOS y protocolo FICTICIO" in salida
    assert "Regla de suficiencia:" in salida


def test_la_demostracion_exige_protocolo_y_configuracion_ficticios(proyecto: Path) -> None:
    comunes = _comunes(proyecto)
    datos = yaml.safe_load(
        (proyecto / EJEMPLOS / "protocolo_evaluacion_final_ficticio.yaml").read_text(
            encoding="utf-8"
        )
    )
    datos["ficticio"] = False
    real = proyecto / "config" / "protocolo_no_ficticio.yaml"
    real.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfiguracionInvalida, match="ficticio"):
        crear_servicios(proyecto).evaluacion_final.demostracion(
            SolicitudDemostracionFinal(
                archivo=comunes["archivo"],
                diccionario=comunes["diccionario"],
                definicion=comunes["definicion"],
                poblaciones=comunes["poblaciones"],
                escenarios=comunes["escenarios"],
                experimentos=comunes["experimentos"],
                protocolo=real,
                seleccion_escenarios=("T1|A",),
            )
        )
