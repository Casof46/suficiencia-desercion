"""Servicio de experimentos de desarrollo, selección y congelamiento (M3, M4): CU-06 y CU-07.

Desde H2.6: congelar una configuración con su huella (RF-M4-12). Congelar exige un
protocolo aprobado vigente. Desde F3.1: preparar el desarrollo (matrices por
escenario, folds cronológicos y preprocesamiento dentro de cada fold). Desde
F3.2: entrenar las cinco familias en esos folds, en modo exploratorio, con cada
corrida registrada (también las fallidas) y sus archivos guardados. Desde F3.3:
métricas con prevalencia e intervalos bootstrap sobre las probabilidades de
validación de esas corridas. Desde F3.4: selección del modelo representativo
(DP-10) y del umbral (DP-06) de cada escenario, solo con desarrollo, con el modelo
final guardado y la configuración lista para congelar.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    ConteoFoldResumen,
    CorridaResumen,
    EscenarioPreparadoResumen,
    EstimacionResumen,
    FoldResumen,
    MetricasCorridaResumen,
    ResultadoCongelamiento,
    ResultadoEntrenamiento,
    ResultadoMetricas,
    ResultadoPreparacionDesarrollo,
    ResultadoSeleccion,
    SeleccionEscenarioResumen,
    SolicitudCongelar,
    SolicitudEntrenar,
    SolicitudMetricas,
    SolicitudPrepararDesarrollo,
    SolicitudSeleccionar,
    VentanaPreparadaResumen,
)
from suficiencia.application.preparacion_desarrollo import (
    PreparacionDesarrollo,
    filas_de,
    preparar,
)
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.application.servicio_datos import HistorialPreparado
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.matrices import MatrizEscenario
from suficiencia.domain.escenarios.poblaciones import ConfiguracionPoblaciones
from suficiencia.domain.evaluacion.congelamiento import configuracion_desde_datos, congelar
from suficiencia.domain.evaluacion.metricas import (
    EstimacionBootstrap,
    estimar,
    prevalencia,
    remuestras,
)
from suficiencia.domain.evaluacion.seleccion import (
    Reentrenamiento,
    elegir_umbral,
    seleccionar_familia,
)
from suficiencia.domain.experimentos import (
    Calibracion,
    ConfiguracionExperimentos,
    DefinicionBusqueda,
    Desbalance,
    Familia,
    FilasFold,
    Fold,
    PerfilPreprocesamiento,
    ResultadoFold,
    Valor,
    combinaciones_a_evaluar,
)
from suficiencia.domain.puertos import (
    CapturadorEntorno,
    FuenteCatalogoVentanas,
    FuenteVariables,
    RepositorioRegistros,
)
from suficiencia.domain.trazabilidad.registros import (
    EstadoCorrida,
    ModoExperimento,
    TipoRegistro,
)

ARCHIVO_EXPERIMENTOS = Path("config") / "experimentos.yaml"
ARCHIVO_POBLACIONES = Path("config") / "poblaciones.yaml"
ARCHIVO_ESCENARIOS = Path("config") / "escenarios.yaml"

PreparadorHistorial = Callable[[Path, Path, Path | None, bool, str], HistorialPreparado]
Preprocesar = Callable[[PerfilPreprocesamiento, pd.DataFrame, Sequence[pd.DataFrame]], int]
EntrenarFamilia = Callable[
    [
        Familia,
        PerfilPreprocesamiento,
        Sequence[Mapping[str, Valor]],
        DefinicionBusqueda,
        Desbalance,
        Calibracion,
        int,
        pd.DataFrame,
        pd.Series,
        Sequence[FilasFold],
    ],
    list[ResultadoFold],
]
LeerPredicciones = Callable[[Path, str], pd.DataFrame]
AjustarFinal = Callable[
    [
        Familia,
        PerfilPreprocesamiento,
        Sequence[Mapping[str, Valor]],
        DefinicionBusqueda,
        Desbalance,
        Calibracion,
        int,
        pd.DataFrame,
        pd.Series,
        Sequence[int],
        Sequence[int],
    ],
    ResultadoFold,
]
GuardarModeloFinal = Callable[[Path, object, Mapping[str, Any]], str]
CARPETA_SELECCION = "seleccion"
GuardarCorrida = Callable[
    [Path, pd.DataFrame, Mapping[int, object], Mapping[str, Any]], dict[str, str]
]
CARPETA_EXPERIMENTOS = "experimentos"


def ruta_en_registro(carpeta: Path, raiz: Path) -> str:
    """Ruta que se guarda en el registro: relativa a la raíz si está dentro, si no absoluta.

    Se comparan las rutas resueltas: en Windows, la carpeta temporal puede llegar con
    el nombre corto (``JORGE_~1``) y la de trabajo con el largo, y sin resolver no
    parecerían la misma carpeta (F3.4).
    """
    resuelta = carpeta.resolve()
    try:
        return resuelta.relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return resuelta.as_posix()


def configuraciones_congeladas(repositorio: RepositorioRegistros) -> Mapping[str, str]:
    """Identificador de cada configuración congelada y su huella."""
    return {
        g.contenido["configuracion"]["identificador"]: g.contenido["huella"]
        for g in repositorio.listar(TipoRegistro.CONGELAMIENTO)
    }


class ServicioExperimentos(ServicioCasosDeUso):
    """Experimentos de desarrollo, selección y congelamiento (M3, M4)."""

    NOMBRE: ClassVar[str] = "experimentos"
    DESCRIPCION: ClassVar[str] = "Experimentos de desarrollo, selección y congelamiento (M3, M4)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-06",
            "Ejecutar experimentos de desarrollo",
            "hitos F3.2 a F3.4 (entrenamiento y selección)",
            avance="matrices, folds y preprocesamiento (F3.1); cinco familias en modo "
            "exploratorio con corridas registradas (F3.2)",
        ),
        DefinicionCasoDeUso(
            "CU-07",
            "Seleccionar y congelar configuraciones",
            "fase posterior a la Fase 2 (selección)",
            avance="congelamiento con huella (H2.6)",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        repositorio: Callable[[Path], RepositorioRegistros],
        archivo_registro: Callable[[], Path],
        leer_yaml: Callable[[Path], Any],
        *,
        preparar_historial: PreparadorHistorial,
        cargar_poblaciones: Callable[[Path], ConfiguracionPoblaciones],
        fuente_catalogo: Callable[[Path], FuenteCatalogoVentanas],
        fuente_diccionario: Callable[[Path], FuenteVariables],
        cargar_experimentos: Callable[[Path], ConfiguracionExperimentos],
        preprocesar: Preprocesar,
        capturador: CapturadorEntorno,
        carpeta_trabajo: Callable[[], Path],
        entrenar_familia: EntrenarFamilia,
        guardar_corrida: GuardarCorrida,
        leer_predicciones: LeerPredicciones,
        ajustar_final: AjustarFinal,
        guardar_modelo_final: GuardarModeloFinal,
        leer_modelo: Callable[[Path, str], object],
    ) -> None:
        self._raiz = raiz
        self._repositorio = repositorio
        self._archivo_registro = archivo_registro
        self._leer_yaml = leer_yaml
        self._preparar_historial = preparar_historial
        self._cargar_poblaciones = cargar_poblaciones
        self._fuente_catalogo = fuente_catalogo
        self._fuente_diccionario = fuente_diccionario
        self._cargar_experimentos = cargar_experimentos
        self._preprocesar = preprocesar
        self._capturador = capturador
        self._carpeta_trabajo = carpeta_trabajo
        self._entrenar_familia = entrenar_familia
        self._guardar_corrida = guardar_corrida
        self._leer_predicciones = leer_predicciones
        self._ajustar_final = ajustar_final
        self._guardar_modelo_final = guardar_modelo_final
        self._leer_modelo = leer_modelo

    def _ruta(self, archivo: Path | None, por_omision: Path) -> Path:
        if archivo is None:
            return self._raiz / por_omision
        return archivo if archivo.is_absolute() else self._raiz / archivo

    def _preparar(
        self, solicitud: SolicitudPrepararDesarrollo
    ) -> tuple[ConfiguracionExperimentos, HistorialPreparado, PreparacionDesarrollo, bool]:
        experimentos = self._cargar_experimentos(
            self._ruta(solicitud.experimentos, ARCHIVO_EXPERIMENTOS)
        )
        poblaciones = self._cargar_poblaciones(
            self._ruta(solicitud.poblaciones, ARCHIVO_POBLACIONES)
        )
        catalogo = self._fuente_catalogo(
            self._ruta(solicitud.escenarios, ARCHIVO_ESCENARIOS)
        ).cargar()
        variables = self._fuente_diccionario(solicitud.diccionario).cargar()
        historial = self._preparar_historial(
            solicitud.archivo,
            solicitud.diccionario,
            solicitud.definicion,
            solicitud.clave_efimera,
            solicitud.separador,
        )
        preparacion = preparar(
            historial.tabla,
            historial.columnas,
            historial.definicion,
            poblaciones,
            catalogo,
            variables,
            experimentos,
        )
        ficticias = (
            experimentos.ficticio or poblaciones.ficticio or catalogo.ficticio or variables.ficticio
        )
        return experimentos, historial, preparacion, ficticias

    def preparar_desarrollo(
        self, solicitud: SolicitudPrepararDesarrollo
    ) -> ResultadoPreparacionDesarrollo:
        """Prepara matrices, folds y preprocesamiento del desarrollo (CU-06, F3.1).

        Solo se leen las cohortes de desarrollo; la prueba no se etiqueta ni se lee.
        No escribe en el registro: es una verificación previa al entrenamiento.

        Raises:
            DecisionPendiente: si falta una configuración o un dato de una decisión
                abierta (DP-01, DP-02, DP-03, DP-04, DP-05, DP-07, DP-12, DP-14).
            ConfiguracionInvalida: si alguna configuración no es válida.
            FugaTemporal: si algún escenario usa información no disponible en su ventana.
            AuditoriaConErrores: si la auditoría del archivo no es apta.
        """
        experimentos, historial, preparacion, ficticias = self._preparar(solicitud)
        folds = preparacion.folds
        ventanas: dict[str, VentanaPreparadaResumen] = {}
        escenarios = []
        for matriz in preparacion.matrices:
            if matriz.ventana not in ventanas:
                ventanas[matriz.ventana] = VentanaPreparadaResumen(
                    ventana=matriz.ventana,
                    periodo_indice=preparacion.periodos_indice[matriz.ventana],
                    filas=matriz.filas,
                    eventos=int(matriz.objetivo.sum()),
                    folds=tuple(_conteo(matriz, fold) for fold in folds),
                )
            escenarios.append(
                EscenarioPreparadoResumen(
                    escenario=matriz.escenario,
                    ventana=matriz.ventana,
                    conjunto=matriz.conjunto,
                    variables=tuple(str(c) for c in matriz.predictores.columns),
                    filas=matriz.filas,
                    columnas_preprocesadas={
                        nombre: self._columnas(perfil, matriz, folds)
                        for nombre, perfil in experimentos.perfiles.items()
                    },
                )
            )
        return ResultadoPreparacionDesarrollo(
            archivo=solicitud.archivo.name,
            sintetico=historial.sintetico,
            configuraciones_ficticias=ficticias,
            huella_dataset=historial.huella_dataset.valor,
            diseno=preparacion.diseno.value,
            cohortes_desarrollo=preparacion.cohortes_desarrollo,
            folds=tuple(
                FoldResumen(
                    numero=f.numero,
                    ajuste=f.ajuste,
                    calibracion=f.calibracion,
                    validacion=f.validacion,
                )
                for f in folds
            ),
            ventanas=tuple(ventanas.values()),
            escenarios=tuple(escenarios),
            no_factibles=tuple(e.codigo for e in preparacion.no_factibles),
            perfiles=tuple(experimentos.perfiles),
        )

    def entrenar(self, solicitud: SolicitudEntrenar) -> ResultadoEntrenamiento:
        """Entrena las familias en los folds de desarrollo (CU-06; RF-M3-01, 04 a 09, 11).

        Siempre en modo exploratorio: no hay protocolo aprobado y nada de esto es
        confirmatorio. Cada corrida (escenario × familia) queda en el registro del
        proyecto, exitosa o fallida; una falla no detiene las demás (RF-M3-11). Una
        corrida ya completa con la misma configuración y el mismo archivo se omite
        (RF-M3-08). La prueba nunca se lee.

        Raises:
            DecisionPendiente, ConfiguracionInvalida, FugaTemporal, AuditoriaConErrores:
                como en ``preparar_desarrollo``, o si se pide un escenario o una familia
                que no existe.
        """
        experimentos, historial, preparacion, ficticias = self._preparar(solicitud)
        matrices = _seleccionar_escenarios(preparacion, solicitud.seleccion_escenarios)
        familias = _seleccionar_familias(solicitud.seleccion_familias)
        repositorio = self._repositorio(self._archivo_registro())
        registrador = RegistradorCorridas(repositorio, self._capturador)
        completas = _claves_completas(repositorio)
        carpeta_base = self._carpeta_trabajo() / CARPETA_EXPERIMENTOS
        corridas = []
        for matriz in matrices:
            folds = _filas_de_folds(matriz, preparacion.folds)
            for familia in familias:
                corridas.append(
                    self._corrida(
                        registrador,
                        completas,
                        carpeta_base,
                        experimentos,
                        historial,
                        preparacion,
                        matriz,
                        folds,
                        familia,
                        ficticias,
                    )
                )
        return ResultadoEntrenamiento(
            archivo=solicitud.archivo.name,
            sintetico=historial.sintetico,
            configuraciones_ficticias=ficticias,
            huella_dataset=historial.huella_dataset.valor,
            modo=ModoExperimento.EXPLORATORIO.value,
            semilla=experimentos.semilla,
            corridas=tuple(corridas),
        )

    def metricas(self, solicitud: SolicitudMetricas) -> ResultadoMetricas:
        """Métricas con prevalencia e intervalos de las corridas registradas (RF-M4-01 a 03).

        Se calculan sobre las probabilidades de validación fuera de fold de todos los
        folds juntos. Son exploratorias: el máximo de muchas puntuaciones de validación
        es optimista y no es una estimación final. El cálculo queda en el registro.

        Raises:
            DecisionPendiente: si falta la configuración (DP-07) o un dato de DP-08a,
                DP-08e o DP-08i.
            ConfiguracionInvalida: si no hay corridas, si se pide un escenario o una
                familia sin corridas, o si un archivo de predicciones cambió.
        """
        experimentos = self._cargar_experimentos(
            self._ruta(solicitud.experimentos, ARCHIVO_EXPERIMENTOS)
        )
        definicion = experimentos.metricas
        repositorio = self._repositorio(self._archivo_registro())
        corridas = _corridas_de(
            repositorio,
            experimentos.nombre,
            solicitud.seleccion_escenarios,
            _seleccionar_familias(solicitud.seleccion_familias),
        )
        filas = []
        for contenido in corridas:
            resultados = contenido["resultados"]
            predicciones = self._leer_predicciones(
                self._raiz / resultados["carpeta"],
                resultados["huellas_archivos"]["predicciones.csv"],
            )
            y = predicciones["objetivo"].to_numpy(dtype="int64")
            p = predicciones["probabilidad"].to_numpy(dtype="float64")
            cohorte = predicciones["cohorte"].astype(str).tolist()
            indices = remuestras(
                y, cohorte, definicion.estratificacion, definicion.replicas, experimentos.semilla
            )
            filas.append(
                MetricasCorridaResumen(
                    identificador=contenido["identificador"],
                    escenario=contenido["configuracion"]["escenario"],
                    familia=contenido["configuracion"]["familia"],
                    filas=len(y),
                    eventos=int(y.sum()),
                    prevalencia=prevalencia(y),
                    metricas={
                        m.value: _resumen_estimacion(
                            estimar(definicion.funcion(m), y, p, indices, definicion.nivel)
                        )
                        for m in definicion.metricas
                    },
                )
            )
        configuracion = {
            "tipo": "metricas_validacion",
            "configuracion_experimentos": experimentos.nombre,
            "configuraciones_ficticias": experimentos.ficticio,
            "corridas": [f.identificador for f in filas],
            "metricas": [m.value for m in definicion.metricas],
            "q": definicion.q,
            "intervalos": {
                "metodo": definicion.metodo.value,
                "nivel": definicion.nivel,
                "replicas": definicion.replicas,
                "estratificacion": definicion.estratificacion.value,
            },
        }
        guardado = RegistradorCorridas(repositorio, self._capturador).ejecutar(
            lambda: {"corridas": [f.model_dump() for f in filas]},
            modo=ModoExperimento.EXPLORATORIO,
            configuracion=configuracion,
            semillas={"bootstrap": experimentos.semilla},
            huella_datos=None,
            version_protocolo=None,
        )
        return ResultadoMetricas(
            configuracion_experimentos=experimentos.nombre,
            configuraciones_ficticias=experimentos.ficticio,
            metodo=definicion.metodo.value,
            nivel=definicion.nivel,
            replicas=definicion.replicas,
            estratificacion=definicion.estratificacion.value,
            q=definicion.q,
            corridas=tuple(filas),
            identificador_registro=guardado.contenido["identificador"],
        )

    def seleccionar(self, solicitud: SolicitudSeleccionar) -> ResultadoSeleccion:
        """Modelo representativo y umbral de cada escenario, solo con desarrollo (F3.4).

        Para cada escenario se comparan las cinco familias con la métrica de la regla
        (DP-10) sobre sus probabilidades de validación; el umbral se elige con las del
        modelo seleccionado (DP-06; RF-M4-07, RF-M4-08). Nunca se lee la prueba. El
        modelo final se guarda y la selección queda en el registro (exploratoria), con
        la configuración lista para congelar.

        Raises:
            ConfiguracionInvalida: si a algún escenario le falta una corrida de alguna
                familia con esta configuración y este archivo, o un archivo cambió.
        """
        experimentos, historial, preparacion, ficticias = self._preparar(solicitud)
        matrices = _seleccionar_escenarios(preparacion, solicitud.seleccion_escenarios)
        repositorio = self._repositorio(self._archivo_registro())
        regla = experimentos.seleccion
        funcion = experimentos.metricas.funcion(regla.metrica)
        escenarios = []
        for matriz in matrices:
            corridas = _corridas_por_familia(
                repositorio, experimentos.nombre, historial.huella_fuente.valor, matriz.escenario
            )
            predicciones = {
                familia: self._leer_predicciones(
                    self._raiz / c["resultados"]["carpeta"],
                    c["resultados"]["huellas_archivos"]["predicciones.csv"],
                )
                for familia, c in corridas.items()
            }
            valores = {
                familia: funcion(
                    t["objetivo"].to_numpy(dtype="int64"),
                    t["probabilidad"].to_numpy(dtype="float64"),
                )
                for familia, t in predicciones.items()
            }
            elegida = seleccionar_familia(valores, regla)
            validacion = predicciones[elegida]
            umbral = elegir_umbral(
                validacion["objetivo"].to_numpy(dtype="int64"),
                validacion["probabilidad"].to_numpy(dtype="float64"),
                experimentos.umbral,
                experimentos.metricas.q,
            )
            escenarios.append(
                self._modelo_final(
                    experimentos,
                    historial,
                    preparacion,
                    matriz,
                    Familia(elegida),
                    corridas[elegida],
                    regla.reentrenamiento,
                    valores,
                    umbral,
                )
            )
        guardado = RegistradorCorridas(repositorio, self._capturador).ejecutar(
            lambda: {"escenarios": [e.model_dump() for e in escenarios]},
            modo=ModoExperimento.EXPLORATORIO,
            configuracion={
                "tipo": "seleccion_desarrollo",
                "configuracion_experimentos": experimentos.nombre,
                "configuraciones_ficticias": ficticias,
                "huella_fuente": historial.huella_fuente.valor,
                "seleccion": {
                    "metrica": regla.metrica.value,
                    "margen": regla.margen,
                    "orden_familias": list(regla.orden_familias),
                    "reentrenamiento": regla.reentrenamiento.value,
                },
                "umbral": {
                    "regla": experimentos.umbral.regla.value,
                    "valor": experimentos.umbral.valor,
                    "q": experimentos.metricas.q,
                },
            },
            semillas={"modelos": experimentos.semilla},
            huella_datos=historial.huella_dataset.valor,
            version_protocolo=None,
        )
        return ResultadoSeleccion(
            configuracion_experimentos=experimentos.nombre,
            configuraciones_ficticias=ficticias,
            escenarios=tuple(escenarios),
            identificador_registro=guardado.contenido["identificador"],
        )

    def _modelo_final(
        self,
        experimentos: ConfiguracionExperimentos,
        historial: HistorialPreparado,
        preparacion: PreparacionDesarrollo,
        matriz: MatrizEscenario,
        familia: Familia,
        corrida: Mapping[str, Any],
        reentrenamiento: Reentrenamiento,
        valores: Mapping[str, float],
        umbral: float,
    ) -> SeleccionEscenarioResumen:
        modelo_familia = experimentos.modelos[familia]
        perfil = experimentos.perfiles[modelo_familia.perfil]
        cohortes = preparacion.cohortes_desarrollo
        if reentrenamiento is Reentrenamiento.TODO_DESARROLLO:
            ultima = (cohortes[-1],)
            ajuste = _posiciones(matriz, cohortes[:-1])
            final = self._ajustar_final(
                familia,
                perfil,
                combinaciones_a_evaluar(
                    modelo_familia, experimentos.busqueda, experimentos.semilla
                ),
                experimentos.busqueda,
                experimentos.desbalance,
                experimentos.calibracion,
                experimentos.semilla,
                matriz.predictores,
                matriz.objetivo,
                ajuste,
                _posiciones(matriz, ultima),
            )
            modelo, combinacion, usadas = final.modelo, dict(final.combinacion), cohortes
        else:
            ultimo = corrida["resultados"]["folds"][-1]
            numero = ultimo["numero"]
            carpeta_corrida = self._raiz / corrida["resultados"]["carpeta"]
            nombre = f"modelo_fold_{numero}.joblib"
            modelo = self._leer_modelo(
                carpeta_corrida / nombre, corrida["resultados"]["huellas_archivos"][nombre]
            )
            combinacion = dict(ultimo["combinacion"])
            fold = preparacion.folds[-1]
            usadas = (*fold.ajuste, *fold.calibracion)
        configuracion = {
            "escenario": matriz.escenario,
            "algoritmo": familia.value,
            "hiperparametros": combinacion,
            "preprocesamiento": {
                "perfil": perfil.nombre,
                "imputacion_numerica": perfil.imputacion_numerica.value,
                "indicador_faltante": perfil.indicador_faltante,
                "escalado": perfil.escalado.value,
                "imputacion_categorica": perfil.imputacion_categorica.value,
            },
            "variables": [str(c) for c in matriz.predictores.columns],
            "umbral": umbral,
            "calibracion": {"metodo": experimentos.calibracion.value},
            "semilla": experimentos.semilla,
        }
        clave = _huella_json({**configuracion, "huella_fuente": historial.huella_fuente.valor})
        nombre_carpeta = f"{matriz.escenario.replace('|', '_').replace('+', '')}-{familia.value}"
        carpeta = self._carpeta_trabajo() / CARPETA_SELECCION / f"{nombre_carpeta}-{clave[:12]}"
        relativa = ruta_en_registro(carpeta, self._raiz)
        if carpeta.exists():
            huella_modelo = json.loads((carpeta / "manifiesto.json").read_text(encoding="utf-8"))[
                "huella_modelo"
            ]
        else:
            huella_modelo = self._guardar_modelo_final(
                carpeta,
                modelo,
                {"configuracion": configuracion, "corrida": corrida["identificador"]},
            )
        configuracion["datos_reentrenamiento"] = json.dumps(
            {
                "reentrenamiento": reentrenamiento.value,
                "cohortes": list(usadas),
                "huella_fuente": historial.huella_fuente.valor,
                "modelo": f"{relativa}/modelo_final.joblib",
                "huella_modelo": huella_modelo,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return SeleccionEscenarioResumen(
            escenario=matriz.escenario,
            familia=familia.value,
            metrica=experimentos.seleccion.metrica.value,
            valores=dict(valores),
            umbral=umbral,
            reentrenamiento=reentrenamiento.value,
            carpeta=relativa,
            configuracion_candidata=configuracion,
        )

    def _corrida(
        self,
        registrador: RegistradorCorridas,
        completas: Mapping[str, str],
        carpeta_base: Path,
        experimentos: ConfiguracionExperimentos,
        historial: HistorialPreparado,
        preparacion: PreparacionDesarrollo,
        matriz: MatrizEscenario,
        folds: tuple[FilasFold, ...],
        familia: Familia,
        ficticias: bool,
    ) -> CorridaResumen:
        modelo_familia = experimentos.modelos[familia]
        perfil = experimentos.perfiles[modelo_familia.perfil]
        combinaciones = combinaciones_a_evaluar(
            modelo_familia, experimentos.busqueda, experimentos.semilla
        )
        configuracion: dict[str, Any] = {
            "tipo": "entrenamiento_desarrollo",
            "configuracion_experimentos": experimentos.nombre,
            "configuraciones_ficticias": ficticias,
            "escenario": matriz.escenario,
            "ventana": matriz.ventana,
            "conjunto": matriz.conjunto,
            "variables": [str(c) for c in matriz.predictores.columns],
            "lecturas": {
                str(c): experimentos.matrices.de(str(c)).value for c in matriz.predictores.columns
            },
            "diseno": preparacion.diseno.value,
            "cohortes_desarrollo": list(preparacion.cohortes_desarrollo),
            "folds": [
                {
                    "numero": f.numero,
                    "ajuste": list(f.ajuste),
                    "calibracion": list(f.calibracion),
                    "validacion": f.validacion,
                }
                for f in preparacion.folds
            ],
            "familia": familia.value,
            "perfil": {
                "nombre": perfil.nombre,
                "imputacion_numerica": perfil.imputacion_numerica.value,
                "indicador_faltante": perfil.indicador_faltante,
                "escalado": perfil.escalado.value,
                "imputacion_categorica": perfil.imputacion_categorica.value,
            },
            "combinaciones": [dict(c) for c in combinaciones],
            "busqueda": {
                "metodo": experimentos.busqueda.metodo.value,
                "metrica": experimentos.busqueda.metrica.value,
                "intentos": experimentos.busqueda.intentos,
            },
            "desbalance": experimentos.desbalance.value,
            "calibracion": experimentos.calibracion.value,
            "huella_fuente": historial.huella_fuente.valor,
        }
        clave = _huella_json({**configuracion, "semilla": experimentos.semilla})
        configuracion["clave_corrida"] = clave
        if clave in completas:
            return CorridaResumen(
                escenario=matriz.escenario,
                familia=familia.value,
                estado="omitida",
                identificador=completas[clave],
                configuraciones_evaluadas=0,
                carpeta=None,
                error=None,
            )
        nombre_carpeta = f"{matriz.escenario.replace('|', '_').replace('+', '')}-{familia.value}"
        carpeta = carpeta_base / f"{nombre_carpeta}-{clave[:12]}"
        semillas = {"modelos": experimentos.semilla, "busqueda": experimentos.semilla}

        def ejecutar() -> dict[str, Any]:
            resultados = self._entrenar_familia(
                familia,
                perfil,
                combinaciones,
                experimentos.busqueda,
                experimentos.desbalance,
                experimentos.calibracion,
                experimentos.semilla,
                matriz.predictores,
                matriz.objetivo,
                folds,
            )
            predicciones = _predicciones(matriz, folds, resultados)
            huellas = self._guardar_corrida(
                carpeta,
                predicciones,
                {r.numero: r.modelo for r in resultados},
                {"configuracion": configuracion, "semillas": semillas},
            )
            return {
                "folds": [
                    _resumen_fold(matriz, f, r) for f, r in zip(folds, resultados, strict=True)
                ],
                "configuraciones_evaluadas": sum(r.configuraciones_evaluadas for r in resultados),
                "carpeta": ruta_en_registro(carpeta, self._raiz),
                "huellas_archivos": huellas,
            }

        guardado = registrador.ejecutar(
            ejecutar,
            modo=ModoExperimento.EXPLORATORIO,
            configuracion=configuracion,
            semillas=semillas,
            huella_datos=historial.huella_dataset.valor,
            version_protocolo=None,
        )
        contenido = guardado.contenido
        exitosa = contenido["estado"] == EstadoCorrida.EXITOSA.value
        return CorridaResumen(
            escenario=matriz.escenario,
            familia=familia.value,
            estado="exitosa" if exitosa else "fallida",
            identificador=contenido["identificador"],
            configuraciones_evaluadas=(
                contenido["resultados"]["configuraciones_evaluadas"] if exitosa else 0
            ),
            carpeta=contenido["resultados"]["carpeta"] if exitosa else None,
            error=contenido.get("error"),
        )

    def _columnas(
        self, perfil: PerfilPreprocesamiento, matriz: MatrizEscenario, folds: tuple[Fold, ...]
    ) -> tuple[int, int]:
        anchos = []
        for fold in folds:
            ajuste = matriz.predictores[filas_de(matriz, fold.ajuste).to_numpy()]
            otras = [
                matriz.predictores[filas_de(matriz, fold.calibracion).to_numpy()],
                matriz.predictores[filas_de(matriz, (fold.validacion,)).to_numpy()],
            ]
            anchos.append(self._preprocesar(perfil, ajuste, otras))
        return min(anchos), max(anchos)

    def congelar(self, solicitud: SolicitudCongelar) -> ResultadoCongelamiento:
        """Congela la configuración del archivo (CU-07; RF-M4-12).

        Raises:
            SinProtocoloVigente: si no hay protocolo aprobado o la configuración
                declara otra versión.
            ConfiguracionInvalida: si falta un campo o el identificador ya está congelado.
        """
        archivo = (
            solicitud.archivo if solicitud.archivo.is_absolute() else self._raiz / solicitud.archivo
        )
        configuracion = configuracion_desde_datos(self._leer_yaml(archivo))
        repositorio = self._repositorio(self._archivo_registro())
        registro = congelar(
            configuracion, historial_protocolo(repositorio), configuraciones_congeladas(repositorio)
        )
        repositorio.agregar(registro)
        return ResultadoCongelamiento(
            identificador=configuracion.identificador,
            rol=configuracion.rol.value,
            escenario=configuracion.escenario,
            huella=registro.huella,
            version_protocolo=configuracion.version_protocolo,
            ficticio=configuracion.ficticio,
        )


def _conteo(matriz: MatrizEscenario, fold: Fold) -> ConteoFoldResumen:
    def contar(cohortes: tuple[str, ...]) -> tuple[int, int]:
        mascara = filas_de(matriz, cohortes).to_numpy()
        return int(mascara.sum()), int(matriz.objetivo[mascara].sum())

    ajuste, eventos_ajuste = contar(fold.ajuste)
    calibracion, eventos_calibracion = contar(fold.calibracion)
    validacion, eventos_validacion = contar((fold.validacion,))
    return ConteoFoldResumen(
        numero=fold.numero,
        ajuste=ajuste,
        eventos_ajuste=eventos_ajuste,
        calibracion=calibracion,
        eventos_calibracion=eventos_calibracion,
        validacion=validacion,
        eventos_validacion=eventos_validacion,
    )


def _huella_json(datos: Mapping[str, Any]) -> str:
    texto = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _claves_completas(repositorio: RepositorioRegistros) -> dict[str, str]:
    """Clave de cada corrida exitosa ya registrada y su identificador (RF-M3-08)."""
    completas = {}
    for guardado in repositorio.listar(TipoRegistro.EXPERIMENTO):
        contenido = guardado.contenido
        clave = contenido.get("configuracion", {}).get("clave_corrida")
        if clave and contenido.get("estado") == EstadoCorrida.EXITOSA.value:
            completas[clave] = contenido["identificador"]
    return completas


def _seleccionar_escenarios(
    preparacion: PreparacionDesarrollo, seleccion: tuple[str, ...]
) -> tuple[MatrizEscenario, ...]:
    if not seleccion:
        return preparacion.matrices
    por_codigo = {m.escenario: m for m in preparacion.matrices}
    no_factibles = {e.codigo for e in preparacion.no_factibles}
    for codigo in seleccion:
        if codigo in no_factibles:
            raise ConfiguracionInvalida(
                f"El escenario {codigo} no es factible y no se entrena.",
                "Elija un escenario factible (RF-M2-03).",
            )
        if codigo not in por_codigo:
            raise ConfiguracionInvalida(
                f"El escenario {codigo!r} no existe.",
                "Use el código ventana|conjunto, por ejemplo T1|A+F.",
            )
    return tuple(por_codigo[c] for c in dict.fromkeys(seleccion))


def _seleccionar_familias(seleccion: tuple[str, ...]) -> tuple[Familia, ...]:
    if not seleccion:
        return tuple(Familia)
    validas = {f.value: f for f in Familia}
    desconocidas = [f for f in seleccion if f not in validas]
    if desconocidas:
        raise ConfiguracionInvalida(
            f"Familia desconocida: {', '.join(desconocidas)}.",
            f"Use: {', '.join(validas)}.",
        )
    return tuple(validas[f] for f in dict.fromkeys(seleccion))


def _filas_de_folds(matriz: MatrizEscenario, folds: tuple[Fold, ...]) -> tuple[FilasFold, ...]:
    def posiciones(cohortes: tuple[str, ...]) -> tuple[int, ...]:
        return tuple(int(i) for i in filas_de(matriz, cohortes).to_numpy().nonzero()[0])

    return tuple(
        FilasFold(
            numero=f.numero,
            ajuste=posiciones(f.ajuste),
            calibracion=posiciones(f.calibracion),
            validacion=posiciones((f.validacion,)),
        )
        for f in folds
    )


def _predicciones(
    matriz: MatrizEscenario, folds: tuple[FilasFold, ...], resultados: list[ResultadoFold]
) -> pd.DataFrame:
    """Probabilidades de validación fuera de fold, sin seudónimos."""
    filas = []
    objetivo = matriz.objetivo.to_numpy()
    cohorte = matriz.cohorte.astype(str).to_numpy()
    for fold, resultado in zip(folds, resultados, strict=True):
        for posicion, probabilidad in zip(fold.validacion, resultado.probabilidades, strict=True):
            filas.append(
                {
                    "fila": posicion,
                    "fold": fold.numero,
                    "cohorte": cohorte[posicion],
                    "objetivo": int(objetivo[posicion]),
                    "probabilidad": probabilidad,
                }
            )
    return pd.DataFrame(filas, columns=["fila", "fold", "cohorte", "objetivo", "probabilidad"])


def _resumen_fold(
    matriz: MatrizEscenario, fold: FilasFold, resultado: ResultadoFold
) -> dict[str, Any]:
    objetivo = matriz.objetivo.to_numpy()
    return {
        "numero": fold.numero,
        "combinacion": dict(resultado.combinacion),
        "puntaje_busqueda": resultado.puntaje_busqueda,
        "configuraciones_evaluadas": resultado.configuraciones_evaluadas,
        "filas_ajuste": len(fold.ajuste),
        "eventos_ajuste": int(objetivo[list(fold.ajuste)].sum()),
        "filas_calibracion": len(fold.calibracion),
        "filas_validacion": len(fold.validacion),
        "eventos_validacion": int(objetivo[list(fold.validacion)].sum()),
    }


def _numero(valor: float) -> float | None:
    return None if valor != valor else valor  # NaN no se guarda en el registro


def _resumen_estimacion(estimacion: EstimacionBootstrap) -> EstimacionResumen:
    return EstimacionResumen(
        puntual=_numero(estimacion.puntual),
        limite_inferior=_numero(estimacion.limite_inferior),
        limite_superior=_numero(estimacion.limite_superior),
        replicas_validas=estimacion.replicas_validas,
    )


def _corridas_de(
    repositorio: RepositorioRegistros,
    configuracion: str,
    escenarios: tuple[str, ...],
    familias: tuple[Familia, ...],
) -> list[dict[str, Any]]:
    """Corridas de entrenamiento exitosas de una configuración, en el orden del registro."""
    nombres = {f.value for f in familias}
    elegidas = []
    for guardado in repositorio.listar(TipoRegistro.EXPERIMENTO):
        contenido = guardado.contenido
        datos = contenido.get("configuracion", {})
        if (
            contenido.get("estado") == EstadoCorrida.EXITOSA.value
            and datos.get("tipo") == "entrenamiento_desarrollo"
            and datos.get("configuracion_experimentos") == configuracion
            and datos.get("familia") in nombres
            and (not escenarios or datos.get("escenario") in escenarios)
        ):
            elegidas.append(contenido)
    encontrados = {c["configuracion"]["escenario"] for c in elegidas}
    faltan = [e for e in escenarios if e not in encontrados]
    if not elegidas or faltan:
        detalle = f" para {', '.join(faltan)}" if faltan else ""
        raise ConfiguracionInvalida(
            f"No hay corridas de entrenamiento exitosas de '{configuracion}'{detalle}.",
            "Entrene primero con `suficiencia experimentos entrenar` y la misma configuración.",
        )
    return elegidas


def _posiciones(matriz: MatrizEscenario, cohortes: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(int(i) for i in filas_de(matriz, cohortes).to_numpy().nonzero()[0])


def _corridas_por_familia(
    repositorio: RepositorioRegistros, configuracion: str, huella_fuente: str, escenario: str
) -> dict[str, dict[str, Any]]:
    """Última corrida exitosa de cada familia del escenario, con esta configuración y archivo."""
    por_familia: dict[str, dict[str, Any]] = {}
    for guardado in repositorio.listar(TipoRegistro.EXPERIMENTO):
        contenido = guardado.contenido
        datos = contenido.get("configuracion", {})
        if (
            contenido.get("estado") == EstadoCorrida.EXITOSA.value
            and datos.get("tipo") == "entrenamiento_desarrollo"
            and datos.get("configuracion_experimentos") == configuracion
            and datos.get("huella_fuente") == huella_fuente
            and datos.get("escenario") == escenario
        ):
            por_familia[datos["familia"]] = contenido
    faltan = [f.value for f in Familia if f.value not in por_familia]
    if faltan:
        raise ConfiguracionInvalida(
            f"Al escenario {escenario} le faltan corridas exitosas de: {', '.join(faltan)}.",
            "Entrene las cinco familias con `suficiencia experimentos entrenar` y la misma "
            "configuración y el mismo archivo antes de seleccionar.",
        )
    return por_familia
