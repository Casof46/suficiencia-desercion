"""Entrenamiento de las cinco familias con el historial sintético ampliado (F3.2).

- PI-06: los cinco modelos se entrenan sobre un escenario sintético y dan probabilidades.
- Búsqueda (RF-M3-04): se elige la combinación con mejor puntaje en la cohorte de
  calibración, entre las declaradas; PI-08: mismas combinaciones y folds en todos
  los escenarios.
- RF-M3-05: el desbalance se calcula con las filas de ajuste del fold.
- RF-M3-09: la calibración no vuelve a ajustar el modelo.
- PI-11: dos ejecuciones iguales dan exactamente las mismas probabilidades.
- PI-12 y RF-M3-11: una corrida que falla queda registrada junto con las exitosas.
- RF-M3-07 y RF-M3-08: archivos de cada corrida con sus huellas; al repetir, las
  corridas completas se omiten y las fallidas se reintentan.
- F3.3: métricas con prevalencia e intervalos de las corridas registradas, que
  coinciden con scikit-learn, se reproducen y rechazan predicciones modificadas.

Todo es sintético y ficticio: las probabilidades no son resultados del método.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline

from fixtures.generador_sintetico import COHORTES_AMPLIADAS, generar_historial
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    SolicitudConsultarRegistro,
    SolicitudEntrenar,
    SolicitudMetricas,
)
from suficiencia.application.preparacion_desarrollo import filas_de, preparar
from suficiencia.cli import SALIDA_CORRECTA, SALIDA_ERROR, main
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.experimentos import (
    Calibracion,
    ConfiguracionExperimentos,
    Desbalance,
    Familia,
    FilasFold,
    combinaciones_a_evaluar,
    configuracion_experimentos_desde_datos,
)
from suficiencia.domain.huella import Huella
from suficiencia.experimentation.modelos import entrenar_en_folds
from suficiencia.persistence.diccionario_yaml import FuenteVariablesDiccionario
from suficiencia.persistence.escenarios_yaml import FuenteCatalogoYaml
from suficiencia.persistence.poblaciones_yaml import cargar_configuracion_poblaciones

EJEMPLOS = Path("config/ejemplos")
PRUEBA = {"2014-1", "2014-2", "2015-1", "2015-2"}
ESCENARIO = "T2|A+F+S+B"

# Espacios chicos para que las pruebas tarden poco; LR conserva dos combinaciones
# para probar la búsqueda. Inventados, como todo el ejemplo.
ESPACIOS_RAPIDOS = {
    "lr": {"C": [0.1, 1.0], "max_iter": [1000]},
    "rf": {"n_estimators": [30], "max_depth": [4]},
    "xgboost": {"n_estimators": [30], "max_depth": [2]},
    "lightgbm": {"n_estimators": [30], "num_leaves": [7], "min_child_samples": [10]},
    "svm": {"C": [1.0]},
}


def _datos_rapidos(raiz: Path) -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load(
        (raiz / EJEMPLOS / "experimentos_ficticio.yaml").read_text(encoding="utf-8")
    )
    for familia, espacio in ESPACIOS_RAPIDOS.items():
        datos["modelos"][familia]["espacio"] = copy.deepcopy(espacio)
    return datos


@pytest.fixture(scope="module")
def proyecto(tmp_path_factory: pytest.TempPathFactory) -> Path:
    raiz = Path(__file__).resolve().parents[2]
    destino = tmp_path_factory.mktemp("proyecto")
    (destino / EJEMPLOS).mkdir(parents=True)
    for archivo in (raiz / EJEMPLOS).iterdir():
        (destino / EJEMPLOS / archivo.name).write_bytes(archivo.read_bytes())
    (destino / "config" / "proyecto.yaml").write_bytes((raiz / "config/proyecto.yaml").read_bytes())
    (destino / "config" / "experimentos_rapido.yaml").write_text(
        yaml.safe_dump(_datos_rapidos(raiz), allow_unicode=True), encoding="utf-8"
    )
    datos = destino / "data" / "sintetico" / "ampliado.csv"
    datos.parent.mkdir(parents=True)
    generar_historial(700, semilla=11, cohortes=COHORTES_AMPLIADAS).to_csv(datos, index=False)
    return destino


def _solicitud(proyecto: Path, **cambios: Any) -> SolicitudEntrenar:
    datos: dict[str, Any] = {
        "archivo": proyecto / "data" / "sintetico" / "ampliado.csv",
        "diccionario": proyecto / EJEMPLOS / "diccionario_sintetico.yaml",
        "definicion": EJEMPLOS / "objetivo_ficticio.yaml",
        "poblaciones": EJEMPLOS / "poblaciones_ampliado_ficticio.yaml",
        "escenarios": EJEMPLOS / "escenarios_ficticio.yaml",
        "experimentos": Path("config/experimentos_rapido.yaml"),
        "clave_efimera": True,
    }
    datos.update(cambios)
    return SolicitudEntrenar.model_validate(datos)


@pytest.fixture(scope="module")
def caso(proyecto: Path) -> tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos]:
    """Matriz de un escenario con todos los bloques, sus folds y la configuración rápida."""
    historial = crear_servicios(proyecto).datos.preparar_historial(
        proyecto / "data" / "sintetico" / "ampliado.csv",
        proyecto / EJEMPLOS / "diccionario_sintetico.yaml",
        proyecto / EJEMPLOS / "objetivo_ficticio.yaml",
        True,
        ",",
    )
    configuracion = configuracion_experimentos_desde_datos(_datos_rapidos(proyecto))
    preparacion = preparar(
        historial.tabla,
        historial.columnas,
        historial.definicion,
        cargar_configuracion_poblaciones(
            proyecto / EJEMPLOS / "poblaciones_ampliado_ficticio.yaml"
        ),
        FuenteCatalogoYaml(proyecto / EJEMPLOS / "escenarios_ficticio.yaml").cargar(),
        FuenteVariablesDiccionario(proyecto / EJEMPLOS / "diccionario_sintetico.yaml").cargar(),
        configuracion,
    )
    matriz = next(m for m in preparacion.matrices if m.escenario == ESCENARIO)

    def posiciones(cohortes: tuple[str, ...]) -> tuple[int, ...]:
        return tuple(int(i) for i in np.flatnonzero(filas_de(matriz, cohortes).to_numpy()))

    folds = tuple(
        FilasFold(
            f.numero, posiciones(f.ajuste), posiciones(f.calibracion), posiciones((f.validacion,))
        )
        for f in preparacion.folds
    )
    return matriz, folds, configuracion


def _entrenar(
    caso: tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos],
    familia: Familia,
    **cambios: Any,
) -> list[Any]:
    matriz, folds, configuracion = caso
    modelo = configuracion.modelos[familia]
    return entrenar_en_folds(
        familia,
        configuracion.perfiles[modelo.perfil],
        combinaciones_a_evaluar(modelo, configuracion.busqueda, configuracion.semilla),
        configuracion.busqueda,
        cambios.get("desbalance", configuracion.desbalance),
        cambios.get("calibracion", configuracion.calibracion),
        configuracion.semilla,
        matriz.predictores,
        matriz.objetivo,
        folds,
    )


@pytest.mark.parametrize("familia", list(Familia))
def test_pi06_cada_familia_da_probabilidades_de_validacion(
    caso: tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos], familia: Familia
) -> None:
    _, folds, _ = caso
    resultados = _entrenar(caso, familia)
    assert [r.numero for r in resultados] == [f.numero for f in folds]
    for fold, resultado in zip(folds, resultados, strict=True):
        probabilidades = np.array(resultado.probabilidades)
        assert len(probabilidades) == len(fold.validacion)
        assert np.all((probabilidades >= 0) & (probabilidades <= 1))
        assert np.all(np.isfinite(probabilidades))


def test_la_busqueda_elige_la_mejor_combinacion_en_la_cohorte_de_calibracion(
    caso: tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos],
) -> None:
    matriz, folds, configuracion = caso
    resultados = _entrenar(caso, Familia.LR, calibracion=Calibracion.NINGUNA)
    declaradas = combinaciones_a_evaluar(
        configuracion.modelos[Familia.LR], configuracion.busqueda, configuracion.semilla
    )
    y = matriz.objetivo.to_numpy()
    for fold, resultado in zip(folds, resultados, strict=True):
        assert resultado.configuraciones_evaluadas == len(declaradas) == 2
        assert dict(resultado.combinacion) in [dict(c) for c in declaradas]
        # Recalcular el puntaje de cada combinación con un modelo nuevo ajustado solo
        # con el ajuste del fold: el elegido es el mejor.
        x_aj = matriz.predictores.iloc[list(fold.ajuste)]
        x_cal = matriz.predictores.iloc[list(fold.calibracion)]
        puntajes = []
        for combinacion in declaradas:
            modelo = clone(resultado.modelo).set_params(
                **{f"modelo__{k}": v for k, v in combinacion.items()}
            )
            modelo.fit(x_aj, y[list(fold.ajuste)])
            puntajes.append(
                roc_auc_score(y[list(fold.calibracion)], modelo.predict_proba(x_cal)[:, 1])
            )
        assert resultado.puntaje_busqueda == pytest.approx(max(puntajes))
        assert dict(resultado.combinacion) == dict(declaradas[int(np.argmax(puntajes))])


def test_rf_m3_05_el_desbalance_se_calcula_con_el_ajuste_del_fold(
    caso: tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos],
) -> None:
    matriz, folds, _ = caso
    y = matriz.objetivo.to_numpy()
    con_pesos = _entrenar(caso, Familia.XGBOOST, calibracion=Calibracion.NINGUNA)
    for fold, resultado in zip(folds, con_pesos, strict=True):
        positivos = int(y[list(fold.ajuste)].sum())
        esperado = (len(fold.ajuste) - positivos) / positivos
        escala = resultado.modelo.named_steps["modelo"].get_params()["scale_pos_weight"]
        assert escala == pytest.approx(esperado)
    for familia in (Familia.LR, Familia.RF, Familia.LIGHTGBM):
        modelo = _entrenar(caso, familia, calibracion=Calibracion.NINGUNA)[0].modelo
        assert modelo.named_steps["modelo"].get_params()["class_weight"] == "balanced"
    sin_pesos = _entrenar(
        caso, Familia.XGBOOST, desbalance=Desbalance.NINGUNO, calibracion=Calibracion.NINGUNA
    )
    assert sin_pesos[0].modelo.named_steps["modelo"].get_params()["scale_pos_weight"] == 1.0


@pytest.mark.parametrize("calibracion", [Calibracion.PLATT, Calibracion.ISOTONICA])
def test_rf_m3_09_la_calibracion_no_vuelve_a_ajustar_el_modelo(
    caso: tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos], calibracion: Calibracion
) -> None:
    matriz, folds, _ = caso
    calibrados = _entrenar(caso, Familia.RF, calibracion=calibracion)
    sin_calibrar = _entrenar(caso, Familia.RF, calibracion=Calibracion.NINGUNA)
    x_val = matriz.predictores.iloc[list(folds[0].validacion)]
    modelo = calibrados[0].modelo
    assert isinstance(modelo, CalibratedClassifierCV)
    assert isinstance(sin_calibrar[0].modelo, Pipeline)
    base = modelo.estimator.estimator  # el modelo congelado dentro del calibrador
    np.testing.assert_array_equal(
        base.predict_proba(x_val), sin_calibrar[0].modelo.predict_proba(x_val)
    )
    assert calibrados[0].probabilidades != sin_calibrar[0].probabilidades


@pytest.mark.parametrize("familia", list(Familia))
def test_pi11_dos_ejecuciones_iguales_dan_las_mismas_probabilidades(
    caso: tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos], familia: Familia
) -> None:
    primera = _entrenar(caso, familia)
    segunda = _entrenar(caso, familia)
    for a, b in zip(primera, segunda, strict=True):
        assert a.probabilidades == b.probabilidades
        assert dict(a.combinacion) == dict(b.combinacion)


def test_un_hiperparametro_inexistente_se_rechaza(
    caso: tuple[Any, tuple[FilasFold, ...], ConfiguracionExperimentos],
) -> None:
    matriz, folds, configuracion = caso
    with pytest.raises(ConfiguracionInvalida, match="no_existe"):
        entrenar_en_folds(
            Familia.LR,
            configuracion.perfiles["lineal"],
            [{"no_existe": 1}],
            configuracion.busqueda,
            configuracion.desbalance,
            Calibracion.NINGUNA,
            configuracion.semilla,
            matriz.predictores,
            matriz.objetivo,
            folds,
        )


def _experimentos(servicios: Any) -> list[dict[str, Any]]:
    consulta = servicios.reportes.consultar(SolicitudConsultarRegistro(tipo="experimentos"))
    return [r.contenido for r in consulta.registros]


def test_servicio_registra_guarda_archivos_y_reanuda(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    escenarios = ("T1|A+F", ESCENARIO)
    resultado = servicios.experimentos.entrenar(
        _solicitud(proyecto, seleccion_escenarios=escenarios)
    )
    assert resultado.modo == "exploratorio"
    assert [c.estado for c in resultado.corridas] == ["exitosa"] * 10
    assert [(c.escenario, c.familia) for c in resultado.corridas] == [
        (e, f.value) for e in escenarios for f in Familia
    ]
    registros = _experimentos(servicios)
    assert len(registros) == 10
    for registro in registros:
        assert registro["modo"] == "exploratorio"
        assert registro["version_protocolo"] is None
        assert registro["semillas"] == {"modelos": 20261111, "busqueda": 20261111}
        paquetes = registro["entorno"]["paquetes"]
        assert {"scikit-learn", "xgboost-cpu", "lightgbm"} <= set(paquetes)
        # RF-M3-07: los archivos existen y coinciden con las huellas registradas.
        carpeta = proyecto / registro["resultados"]["carpeta"]
        for nombre, huella in registro["resultados"]["huellas_archivos"].items():
            assert Huella.de_bytes((carpeta / nombre).read_bytes()).valor == huella
        predicciones = pd.read_csv(carpeta / "predicciones.csv", dtype={"cohorte": str})
        assert list(predicciones.columns) == ["fila", "fold", "cohorte", "objetivo", "probabilidad"]
        assert not set(predicciones["cohorte"]) & PRUEBA
        assert (carpeta / "manifiesto.json").exists()
    # PI-08 (búsqueda): mismas combinaciones y mismos folds por familia en ambos escenarios.
    por_familia: dict[str, list[dict[str, Any]]] = {}
    for registro in registros:
        por_familia.setdefault(registro["configuracion"]["familia"], []).append(
            registro["configuracion"]
        )
    for configuraciones in por_familia.values():
        assert configuraciones[0]["combinaciones"] == configuraciones[1]["combinaciones"]
        assert configuraciones[0]["folds"] == configuraciones[1]["folds"]
        assert configuraciones[0]["escenario"] != configuraciones[1]["escenario"]
    # RF-M3-08: repetir omite las corridas completas, aun con otra clave efímera.
    repetido = servicios.experimentos.entrenar(
        _solicitud(proyecto, seleccion_escenarios=("T1|A+F",), seleccion_familias=("lr",))
    )
    assert [c.estado for c in repetido.corridas] == ["omitida"]
    assert len(_experimentos(servicios)) == 10


def _con_falla(proyecto: Path) -> Path:
    """Configuración en la que SVM falla: un hiperparámetro que no existe."""
    datos = _datos_rapidos(proyecto)
    datos["modelos"]["svm"]["espacio"] = {"no_existe": [1]}
    archivo = proyecto / "config" / "experimentos_con_falla.yaml"
    archivo.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return archivo


def test_pi12_una_corrida_que_falla_queda_registrada_y_se_reintenta(proyecto: Path) -> None:
    archivo = _con_falla(proyecto)
    servicios = crear_servicios(proyecto)
    antes = len(_experimentos(servicios))
    solicitud = _solicitud(
        proyecto,
        experimentos=archivo,
        seleccion_escenarios=("T0|A",),
        seleccion_familias=("lr", "svm"),
    )
    resultado = servicios.experimentos.entrenar(solicitud)
    assert [c.estado for c in resultado.corridas] == ["exitosa", "fallida"]
    assert "no_existe" in (resultado.corridas[1].error or "")
    nuevos = _experimentos(servicios)[antes:]
    assert [r["estado"] for r in nuevos] == ["exitosa", "fallida"]
    # Al repetir, la exitosa se omite y la fallida se vuelve a intentar.
    otra = servicios.experimentos.entrenar(solicitud)
    assert [c.estado for c in otra.corridas] == ["omitida", "fallida"]


def test_escenarios_y_familias_inexistentes_se_rechazan(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    for cambios in (
        {"seleccion_escenarios": ("T0|A+B",)},  # no factible
        {"seleccion_escenarios": ("T9|A",)},
        {"seleccion_familias": ("knn",)},
    ):
        with pytest.raises(ConfiguracionInvalida):
            servicios.experimentos.entrenar(_solicitud(proyecto, **cambios))


def test_linea_de_comandos(proyecto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def argumentos(*extra: str) -> list[str]:
        e = proyecto / EJEMPLOS
        return [
            "--raiz",
            str(proyecto),
            "experimentos",
            "entrenar",
            str(proyecto / "data" / "sintetico" / "ampliado.csv"),
            "--diccionario",
            str(e / "diccionario_sintetico.yaml"),
            "--definicion",
            str(e / "objetivo_ficticio.yaml"),
            "--poblaciones",
            str(e / "poblaciones_ampliado_ficticio.yaml"),
            "--escenarios",
            str(e / "escenarios_ficticio.yaml"),
            "--clave-efimera",
            *extra,
        ]

    rapido = str(proyecto / "config" / "experimentos_rapido.yaml")
    codigo = main(argumentos("--experimentos", rapido, "--escenario", "T1|A", "--familia", "lr"))
    salida = capsys.readouterr().out
    assert codigo == SALIDA_CORRECTA
    assert "DATOS SINTÉTICOS" in salida
    assert "Modo: EXPLORATORIO" in salida
    assert "Exitosas: 1; omitidas: 0; fallidas: 0. Configuraciones evaluadas: 12" in salida
    con_falla = str(_con_falla(proyecto))
    codigo = main(
        argumentos("--experimentos", con_falla, "--escenario", "T1|A", "--familia", "svm")
    )
    assert codigo == SALIDA_ERROR
    assert "FALLIDA: ConfiguracionInvalida" in capsys.readouterr().out


# --- F3.3: métricas e intervalos de las corridas registradas -----------------------


def test_metricas_de_las_corridas_registradas(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    servicios.experimentos.entrenar(_solicitud(proyecto, seleccion_escenarios=("T1|A+F",)))
    rapido = Path("config/experimentos_rapido.yaml")
    resultado = servicios.experimentos.metricas(
        SolicitudMetricas(experimentos=rapido, seleccion_escenarios=("T1|A+F",))
    )
    assert [c.familia for c in resultado.corridas] == [f.value for f in Familia]
    registros = {r["identificador"]: r for r in _experimentos(servicios)}
    for corrida in resultado.corridas:
        registro = registros[corrida.identificador]
        carpeta = proyecto / registro["resultados"]["carpeta"]
        predicciones = pd.read_csv(carpeta / "predicciones.csv")
        y = predicciones["objetivo"].to_numpy()
        p = predicciones["probabilidad"].to_numpy()
        assert corrida.filas == len(y)
        assert corrida.eventos == int(y.sum())
        assert corrida.prevalencia == pytest.approx(y.mean())
        auc = corrida.metricas["auc_roc"]
        assert auc.puntual == pytest.approx(roc_auc_score(y, p))
        assert auc.puntual is not None
        assert auc.limite_inferior is not None and auc.limite_superior is not None
        assert auc.limite_inferior <= auc.puntual <= auc.limite_superior
        assert set(corrida.metricas) == {"auc_roc", "brier", "brier_escalado", "recall_q"}
        assert (corrida.ventana, corrida.conjunto) == ("T1", "A+F")  # F4.1
    assert resultado.origen_datos == "sintetico"
    calculo = registros[resultado.identificador_registro]
    assert calculo["modo"] == "exploratorio"
    assert calculo["configuracion"]["tipo"] == "metricas_validacion"
    assert calculo["configuracion"]["corridas"] == [c.identificador for c in resultado.corridas]
    assert calculo["semillas"] == {"bootstrap": 20261111}
    # Con la misma semilla, el cálculo se reproduce exactamente (PU-20).
    otra = servicios.experimentos.metricas(
        SolicitudMetricas(experimentos=rapido, seleccion_escenarios=("T1|A+F",))
    )
    assert otra.corridas == resultado.corridas


def test_metricas_rechazan_predicciones_modificadas_y_escenarios_sin_corridas(
    proyecto: Path,
) -> None:
    servicios = crear_servicios(proyecto)
    servicios.experimentos.entrenar(
        _solicitud(proyecto, seleccion_escenarios=("T1|A+F",), seleccion_familias=("lr",))
    )
    rapido = Path("config/experimentos_rapido.yaml")
    with pytest.raises(ConfiguracionInvalida, match="T3"):
        servicios.experimentos.metricas(
            SolicitudMetricas(experimentos=rapido, seleccion_escenarios=("T3|A",))
        )
    registro = next(
        r
        for r in _experimentos(servicios)
        if r["estado"] == "exitosa"
        and r["configuracion"].get("escenario") == "T1|A+F"
        and r["configuracion"].get("familia") == "lr"
    )
    archivo = proyecto / registro["resultados"]["carpeta"] / "predicciones.csv"
    original = archivo.read_bytes()
    try:
        archivo.write_bytes(original.replace(b",1,", b",0,", 1))
        with pytest.raises(ConfiguracionInvalida, match="huella"):
            servicios.experimentos.metricas(
                SolicitudMetricas(
                    experimentos=rapido,
                    seleccion_escenarios=("T1|A+F",),
                    seleccion_familias=("lr",),
                )
            )
    finally:
        archivo.write_bytes(original)


def test_linea_de_comandos_metricas(proyecto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    servicios = crear_servicios(proyecto)
    servicios.experimentos.entrenar(
        _solicitud(proyecto, seleccion_escenarios=("T1|A+F",), seleccion_familias=("rf",))
    )
    rapido = str(proyecto / "config" / "experimentos_rapido.yaml")
    argumentos = ["--raiz", str(proyecto), "experimentos", "metricas", "--experimentos", rapido]
    codigo = main([*argumentos, "--escenario", "T1|A+F", "--familia", "rf"])
    salida = capsys.readouterr().out
    assert codigo == SALIDA_CORRECTA
    assert "DATOS SINTÉTICOS" in salida
    assert "CONFIGURACIÓN FICTICIA" in salida
    assert "Intervalos percentil al 95% con 1000 réplicas" in salida
    assert "auc_roc" in salida and "prevalencia=" in salida
    assert "no es una estimación final" in salida
    # F4.1 (RF-M4-10, RF-M4-14, PI-16): reporte rotulado de los escenarios en validación.
    filtros = ["--escenario", "T1|A+F", "--familia", "rf"]
    codigo = main([*argumentos, *filtros, "--reporte", "reports/validacion"])
    assert codigo == SALIDA_CORRECTA
    carpeta = proyecto / "reports" / "validacion"
    texto = (carpeta / "reporte.md").read_text(encoding="utf-8")
    assert texto.startswith("> **DATOS SINTÉTICOS")
    assert "## auc_roc por ventana y conjunto" in texto and "**rf**" in texto
    tabla = pd.read_csv(carpeta / "validacion_escenarios.csv")
    assert set(tabla["origen_datos"]) == {"SINTÉTICO"}
    assert set(tabla["familia"]) == {"rf"} and set(tabla["ventana"]) == {"T1"}


def test_rutas_del_registro_con_la_raiz_por_otro_camino(proyecto: Path, tmp_path: Path) -> None:
    """La raíz puede llegar por otro camino que la carpeta de trabajo (en Windows, el
    nombre corto de la carpeta temporal); los archivos de la corrida se encuentran igual."""
    enlace = tmp_path / "enlace"
    try:
        enlace.symlink_to(proyecto, target_is_directory=True)
    except OSError:
        pytest.skip("El sistema no permite crear enlaces simbólicos.")
    servicios = crear_servicios(enlace)
    solicitud = _solicitud(enlace, seleccion_escenarios=("T0|A",), seleccion_familias=("lr",))
    servicios.experimentos.entrenar(solicitud)
    resultado = servicios.experimentos.metricas(
        SolicitudMetricas(
            experimentos=Path("config/experimentos_rapido.yaml"),
            seleccion_escenarios=("T0|A",),
            seleccion_familias=("lr",),
        )
    )
    assert resultado.corridas
