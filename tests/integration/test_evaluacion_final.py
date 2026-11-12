"""Selección, congelamiento y evaluación final con el historial sintético ampliado (F3.4).

- RF-M4-07 y RF-M4-08: modelo y umbral se eligen con las probabilidades de
  validación, según las reglas declaradas (DP-10, DP-06).
- PI-10: seleccionar no accede a la prueba (registro de accesos vacío).
- PU-05: sin protocolo aprobado, la evaluación final se rechaza sin abrir la prueba.
- PI-09: una configuración distinta de la congelada, o un modelo cambiado, se rechazan.
- PI-15 y RF-M4-09: la prueba se abre una sola vez para todas las configuraciones;
  repetir exige justificación, que queda registrada.
- F3.5: R0 y los controles se construyen, congelan y evalúan en el mismo acceso; la
  comparación usa las predicciones guardadas y no abre la prueba (PI-15); sin R0 la
  comparación no es válida (C7).
- F3.6 (PI-13): las explicaciones solo se generan sobre configuraciones congeladas, con
  filas de desarrollo, y registran partición, muestras y semilla; no abren la prueba.
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
    SolicitudComparar,
    SolicitudConstruirPoblaciones,
    SolicitudDemostracionFinal,
    SolicitudEntrenar,
    SolicitudEvaluacionFinal,
    SolicitudExplicar,
    SolicitudSeleccionar,
)
from suficiencia.application.demostracion_protocolo import _SinAjusteFicticio
from suficiencia.application.servicio_evaluacion_final import EvaluacionFinalRepetida
from suficiencia.application.servicio_experimentos import configuraciones_congeladas
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.cli import SALIDA_CORRECTA, main
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
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
    # Los escenarios pedidos y los que necesitan R0 (T3) y R-ven de T1 (F3.5).
    servicios.experimentos.entrenar(
        SolicitudEntrenar(
            **_comunes(proyecto),
            seleccion_escenarios=(*ESCENARIOS, "T3|A+F+S+B", "T1|A+F+S+B"),
        )
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
    # F3.5 (PU-22, PU-23): R0 en el conjunto más completo de T3 con la familia de mayor
    # AUC-ROC en validación; R0-fam por cada familia seleccionada; R-ven solo para T1.
    referentes = {r.codigo: r for r in resultado.referentes}
    r0 = referentes["R0"].seleccion
    assert r0.escenario == "T3|A+F+S+B"
    auc_t3 = {}
    for familia in ("lr", "rf", "xgboost", "lightgbm", "svm"):
        contenido = corridas[("T3|A+F+S+B", familia)].contenido
        tabla = pd.read_csv(proyecto / contenido["resultados"]["carpeta"] / "predicciones.csv")
        auc_t3[familia] = roc_auc_score(tabla["objetivo"], tabla["probabilidad"])
    assert r0.familia == max(auc_t3, key=lambda f: auc_t3[f])
    familias = {e.familia for e in resultado.escenarios}
    assert {c for c in referentes if c.startswith("R0-fam-")} == {f"R0-fam-{f}" for f in familias}
    assert set(referentes) - {"R0"} - {f"R0-fam-{f}" for f in familias} == {"R-ven-T1"}
    assert referentes["R-ven-T1"].seleccion.escenario == "T1|A+F+S+B"
    assert referentes["R0"].rol == "referencia_r0"
    assert referentes["R-ven-T1"].rol == "control"
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
    # CU-12 sin R0 congelada: la comparación no es válida (C7) y no abre la prueba.
    comparacion = servicios.evaluacion_final.comparar(
        SolicitudComparar(
            evaluacion=resultado.identificador_registro,
            experimentos=_comunes(proyecto)["experimentos"],
            poblaciones=_comunes(proyecto)["poblaciones"],
        )
    )
    assert comparacion.estado == "C7_comparacion_no_valida"
    assert "R0 no es evaluable" in comparacion.motivos_no_validez
    assert comparacion.accesos_a_la_prueba == 1
    with pytest.raises(ConfiguracionInvalida, match="No hay una evaluación final"):
        servicios.evaluacion_final.comparar(SolicitudComparar(evaluacion="EXP-inexistente"))
    _explicaciones(proyecto, servicios, resultado, identificadores)
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
        with pytest.raises(ConfiguracionInvalida, match="huella"):
            servicios.interpretabilidad.explicar(
                SolicitudExplicar(**_comunes(proyecto), evaluacion=resultado.identificador_registro)
            )
    finally:
        archivo.write_bytes(original)


def _explicaciones(
    proyecto: Path, servicios: Any, evaluacion: Any, identificadores: tuple[str, ...]
) -> None:
    """CU-09 y PI-13 sobre la evaluación final recién hecha."""
    repositorio = servicios.reportes.repositorio()
    accesos = len(repositorio.listar(TipoRegistro.ACCESO))
    explicacion = servicios.interpretabilidad.explicar(
        SolicitudExplicar(**_comunes(proyecto), evaluacion=evaluacion.identificador_registro)
    )
    # El ejemplo de DP-11 pide todas las congeladas, con los tres niveles.
    assert [c.identificador for c in explicacion.configuraciones] == list(identificadores)
    assert explicacion.niveles == ("global", "bloque", "local")
    assert len(repositorio.listar(TipoRegistro.ACCESO)) == accesos  # PI-15
    explicadores = {"lr": "lineal", "rf": "arboles", "xgboost": "arboles"}
    explicadores |= {"lightgbm": "arboles", "svm": "kernel"}
    for c in explicacion.configuraciones:
        assert c.explicador == explicadores[c.algoritmo]  # PU-21
        assert c.error_aditividad < 1e-5
        assert c.filas_fondo == 50 and c.filas_explicadas == 100 < c.filas_particion
        assert set(c.importancia_variables) == set(
            configuracion_desde_datos(
                next(
                    g.contenido["configuracion"]
                    for g in repositorio.listar(TipoRegistro.CONGELAMIENTO)
                    if g.contenido["configuracion"]["identificador"] == c.identificador
                )
            ).variables
        )
        assert sum(c.importancia_bloques.values()) == pytest.approx(
            sum(c.importancia_variables.values())
        )
        assert len(c.locales) == 3 and all(len(r.shap) <= 5 for r in c.locales)
    registro = next(
        g.contenido
        for g in repositorio.listar(TipoRegistro.EXPERIMENTO)
        if g.contenido["identificador"] == explicacion.identificador_registro
    )
    # PI-13: partición, muestras y semilla en el registro; modo exploratorio.
    assert registro["modo"] == "exploratorio" and registro["estado"] == "exitosa"
    assert registro["configuracion"]["particion"] == "desarrollo"
    assert registro["semillas"] == {"explicacion": explicacion.semilla}
    desarrollo = set(
        yaml.safe_load(
            (proyecto / EJEMPLOS / "poblaciones_ampliado_ficticio.yaml").read_text(encoding="utf-8")
        )["particion"]["cohortes_desarrollo"]
    )
    for muestra in registro["configuracion"]["muestras"]:
        assert set(muestra["cohortes"]) <= desarrollo
        assert muestra["filas_fondo"] == 50 and muestra["registros_locales"] == 3
        assert muestra["fondo_en_shap"] is (muestra["explicador"] != "arboles")
    archivos = registro["resultados"]["archivos"]
    carpeta = proyecto / archivos["carpeta"]
    locales = pd.read_csv(carpeta / archivos["configuracion_1_locales"]["archivo"])
    assert set(locales["metodo"]) == {"shap", "lime"}
    importancias = pd.read_csv(carpeta / archivos["configuracion_1_importancias"]["archivo"])
    assert set(importancias["nivel"]) == {"variable", "bloque"}
    # Con la misma semilla, las mismas importancias.
    otra = servicios.interpretabilidad.explicar(
        SolicitudExplicar(**_comunes(proyecto), evaluacion=evaluacion.identificador_registro)
    )
    assert [c.importancia_variables for c in otra.configuraciones] == [
        c.importancia_variables for c in explicacion.configuraciones
    ]
    # DP-11: solo el escenario suficiente; un null detiene; otro identificador no sirve.
    datos = _experimentos(Path(__file__).resolve().parents[2])
    datos["interpretabilidad"]["alcance"] = "escenario_suficiente"
    (proyecto / "config" / "experimentos_suficiente.yaml").write_text(
        yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8"
    )
    solicitud = SolicitudExplicar(
        **_comunes(proyecto, "experimentos_suficiente.yaml"),
        evaluacion=evaluacion.identificador_registro,
    )
    if evaluacion.estado_regla == "escenario_suficiente":
        solo = servicios.interpretabilidad.explicar(solicitud)
        assert [c.escenario for c in solo.configuraciones] == [evaluacion.escenario_suficiente]
    else:
        with pytest.raises(ConfiguracionInvalida, match="no eligió un escenario suficiente"):
            servicios.interpretabilidad.explicar(solicitud)
    datos["interpretabilidad"] = None
    (proyecto / "config" / "experimentos_sin_dp11.yaml").write_text(
        yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(DecisionPendiente, match="DP-11"):
        servicios.interpretabilidad.explicar(
            SolicitudExplicar(
                **_comunes(proyecto, "experimentos_sin_dp11.yaml"),
                evaluacion=evaluacion.identificador_registro,
            )
        )
    with pytest.raises(ConfiguracionInvalida, match="No hay una evaluación final"):
        servicios.interpretabilidad.explicar(
            SolicitudExplicar(**_comunes(proyecto), evaluacion=explicacion.identificador_registro)
        )


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
        in pasos["Seleccionar modelo y umbral con desarrollo; construir R0 y controles"]
    )
    assert pasos["Evaluación final sin protocolo aprobado"].startswith("Rechazado")
    assert pasos["Evaluar una configuración con el umbral cambiado"].startswith("Rechazado")
    assert pasos["Repetir la evaluación final sin justificación"].startswith("Rechazado")
    assert "1 acceso permitido" in pasos["Registro de accesos al terminar"]
    assert resultado.evaluacion.accesos_a_la_prueba == 1
    assert resultado.evaluacion.ficticio
    # F3.5: R0 y los controles se congelaron y evaluaron en el mismo acceso; la
    # comparación no abre la prueba (PI-15).
    roles = {c.rol for c in resultado.evaluacion.configuraciones}
    assert roles == {"seleccionada", "referencia_r0", "control"}
    comparacion = resultado.comparacion
    assert comparacion.referencia == "R0"
    assert comparacion.accesos_a_la_prueba == 1
    assert comparacion.estado.startswith(("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"))
    assert "Comparar con R0 y los controles sin volver a abrir la prueba" in pasos
    # F3.6: explicaciones de las configuraciones congeladas, sin abrir la prueba.
    explicacion = resultado.explicacion
    assert len(explicacion.configuraciones) == len(resultado.evaluacion.configuraciones)
    assert explicacion.accesos_a_la_prueba == 1
    assert explicacion.ficticio
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
    assert "Evaluación comparativa de" in salida
    assert "No se declara superioridad." in salida
    assert "Son asociaciones del modelo, no causas." in salida


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
