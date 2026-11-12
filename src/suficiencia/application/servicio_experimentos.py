"""Servicio de experimentos de desarrollo, selección y congelamiento (M3, M4): CU-06 y CU-07.

Desde H2.6: congelar una configuración con su huella (RF-M4-12). Congelar exige un
protocolo aprobado vigente. Desde F3.1: preparar el desarrollo (matrices por
escenario, folds cronológicos y preprocesamiento dentro de cada fold), sin
entrenar todavía. El entrenamiento y la selección del modelo representativo
(DP-10) llegan en los hitos siguientes de la Fase 3.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    ConteoFoldResumen,
    EscenarioPreparadoResumen,
    FoldResumen,
    ResultadoCongelamiento,
    ResultadoPreparacionDesarrollo,
    SolicitudCongelar,
    SolicitudPrepararDesarrollo,
    VentanaPreparadaResumen,
)
from suficiencia.application.preparacion_desarrollo import filas_de, preparar
from suficiencia.application.servicio_datos import HistorialPreparado
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.escenarios.matrices import MatrizEscenario
from suficiencia.domain.escenarios.poblaciones import ConfiguracionPoblaciones
from suficiencia.domain.evaluacion.congelamiento import configuracion_desde_datos, congelar
from suficiencia.domain.experimentos import (
    ConfiguracionExperimentos,
    Fold,
    PerfilPreprocesamiento,
)
from suficiencia.domain.puertos import (
    FuenteCatalogoVentanas,
    FuenteVariables,
    RepositorioRegistros,
)
from suficiencia.domain.trazabilidad.registros import TipoRegistro

ARCHIVO_EXPERIMENTOS = Path("config") / "experimentos.yaml"
ARCHIVO_POBLACIONES = Path("config") / "poblaciones.yaml"
ARCHIVO_ESCENARIOS = Path("config") / "escenarios.yaml"

PreparadorHistorial = Callable[[Path, Path, Path | None, bool, str], HistorialPreparado]
Preprocesar = Callable[[PerfilPreprocesamiento, pd.DataFrame, Sequence[pd.DataFrame]], int]


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
            avance="matrices, folds y preprocesamiento por fold (F3.1)",
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

    def _ruta(self, archivo: Path | None, por_omision: Path) -> Path:
        if archivo is None:
            return self._raiz / por_omision
        return archivo if archivo.is_absolute() else self._raiz / archivo

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
            configuraciones_ficticias=(
                experimentos.ficticio
                or poblaciones.ficticio
                or catalogo.ficticio
                or variables.ficticio
            ),
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
