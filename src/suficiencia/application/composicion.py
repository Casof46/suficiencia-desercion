"""Composición: construye los servicios con sus implementaciones concretas.

Es el único lugar de la aplicación que elige qué adaptador de persistencia o de
experimentación implementa cada puerto. La línea de comandos y la futura interfaz
obtienen aquí los servicios y no importan otras capas (contratos de ``.importlinter``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

import suficiencia
from suficiencia.application._base import ServicioCasosDeUso
from suficiencia.application.demostracion_final import ejecutar_demostracion_final
from suficiencia.application.servicio_datos import ServicioDatos
from suficiencia.application.servicio_escenarios import ServicioEscenarios
from suficiencia.application.servicio_evaluacion_final import ServicioEvaluacionFinal
from suficiencia.application.servicio_experimentos import ServicioExperimentos
from suficiencia.application.servicio_interpretabilidad import ServicioInterpretabilidad
from suficiencia.application.servicio_protocolo import ServicioProtocolo
from suficiencia.application.servicio_proyecto import ServicioProyecto
from suficiencia.application.servicio_reportes import ServicioReportes
from suficiencia.domain.errores import ErrorSuficiencia
from suficiencia.domain.experimentos import PerfilPreprocesamiento, ResultadoFold
from suficiencia.domain.huella import Huella
from suficiencia.domain.puertos import FuenteVariables, Seudonimizador
from suficiencia.persistence.configuracion import FuenteConfiguracionYaml
from suficiencia.persistence.corridas_archivos import (
    guardar_corrida,
    guardar_explicaciones,
    guardar_modelo_final,
    guardar_predicciones_prueba,
    leer_csv_verificado,
    leer_modelo,
    leer_predicciones,
)
from suficiencia.persistence.diccionario_yaml import FuenteVariablesDiccionario, cargar_diccionario
from suficiencia.persistence.entorno import CapturadorEntornoLocal
from suficiencia.persistence.escenarios_yaml import FuenteCatalogoYaml, FuenteVariablesYaml
from suficiencia.persistence.experimentos_yaml import cargar_configuracion_experimentos
from suficiencia.persistence.exportacion import exportar_tabla
from suficiencia.persistence.lectores import contenido_canonico, escribir_csv, leer_tabla
from suficiencia.persistence.objetivo_yaml import cargar_definicion_objetivo
from suficiencia.persistence.particion_archivos import (
    cargador_de_prueba,
    guardar_division,
    leer_manifiesto,
)
from suficiencia.persistence.poblaciones_yaml import cargar_configuracion_poblaciones
from suficiencia.persistence.protocolo_yaml import leer_yaml
from suficiencia.persistence.repositorio_sqlite import RepositorioSqlite
from suficiencia.persistence.seudonimizacion import SeudonimizadorHmac


@dataclass(frozen=True)
class Servicios:
    """Servicios de aplicación listos para usar."""

    proyecto: ServicioProyecto
    datos: ServicioDatos
    escenarios: ServicioEscenarios
    reportes: ServicioReportes
    protocolo: ServicioProtocolo
    experimentos: ServicioExperimentos
    evaluacion_final: ServicioEvaluacionFinal
    interpretabilidad: ServicioInterpretabilidad
    casos_de_uso: tuple[ServicioCasosDeUso, ...]

    def servicio_de(self, codigo: str) -> ServicioCasosDeUso:
        """Devuelve el servicio que atiende el caso de uso indicado."""
        for servicio in self.casos_de_uso:
            if any(caso.codigo == codigo for caso in servicio.CASOS_DE_USO):
                return servicio
        raise ErrorSuficiencia(
            f"No existe el caso de uso {codigo}.",
            "Use un código entre CU-01 y CU-12; `suficiencia estado` los lista.",
        )


def _fuente_variables(archivo: Path, por_omision: bool) -> FuenteVariables:
    return FuenteVariablesYaml(archivo, por_omision=por_omision)


def _fuente_diccionario(archivo: Path) -> FuenteVariables:
    return FuenteVariablesDiccionario(archivo)


def _leer(archivo: Path, separador: str) -> tuple[pd.DataFrame, Huella]:
    leida = leer_tabla(archivo, separador)
    return leida.tabla, leida.huella_fuente


def _seudonimizador(clave_efimera: bool) -> Seudonimizador:
    if clave_efimera:
        return SeudonimizadorHmac.con_clave_efimera()
    return SeudonimizadorHmac.desde_entorno()


def _huella_de_tabla(tabla: pd.DataFrame) -> Huella:
    return Huella.de_bytes(contenido_canonico(tabla))


def _exportar(tabla: pd.DataFrame, archivo: Path) -> Huella:
    return exportar_tabla(tabla, archivo)


def _columnas_tras_preprocesar(
    perfil: PerfilPreprocesamiento, ajuste: pd.DataFrame, otras: Sequence[pd.DataFrame]
) -> int:
    # scikit-learn se importa solo al preparar el desarrollo: el resto de los
    # comandos no debe cargarlo (arranque rápido; prueba de la línea de comandos).
    from suficiencia.experimentation.pipelines import columnas_tras_preprocesar

    return columnas_tras_preprocesar(perfil, ajuste, otras)


def _entrenar_en_folds(*argumentos: Any) -> list[ResultadoFold]:
    # Igual que el preprocesamiento: scikit-learn, XGBoost y LightGBM se importan
    # solo al entrenar.
    from suficiencia.experimentation.modelos import entrenar_en_folds

    return entrenar_en_folds(*argumentos)


def _ajustar_final(*argumentos: Any) -> ResultadoFold:
    from suficiencia.experimentation.modelos import ajustar_final

    return ajustar_final(*argumentos)


def _predecir(modelo: object, predictores: pd.DataFrame) -> Any:
    from suficiencia.experimentation.modelos import predecir

    return predecir(modelo, predictores)


def _explicar_modelo(*argumentos: Any) -> Any:
    # SHAP y LIME se importan solo al explicar.
    from suficiencia.experimentation.explicadores import explicar_modelo

    return explicar_modelo(*argumentos)


def crear_servicios(raiz: Path, clave_sesion: bytes | None = None) -> Servicios:
    """Construye los servicios para el proyecto ubicado en ``raiz``.

    Con ``clave_sesion``, la "clave efímera" es la misma en todas las operaciones de
    estos servicios, sin guardarse en ningún lado: así una demostración puede construir
    la partición y después evaluarla con los mismos seudónimos (F3.4).
    """

    def seudonimizador(clave_efimera: bool) -> Seudonimizador:
        if clave_efimera and clave_sesion is not None:
            return SeudonimizadorHmac(clave_sesion)
        return _seudonimizador(clave_efimera)

    datos = ServicioDatos(
        raiz=raiz,
        cargar_diccionario=cargar_diccionario,
        leer_tabla=_leer,
        seudonimizador=seudonimizador,
        huella_de_tabla=_huella_de_tabla,
        escribir_tabla=escribir_csv,
        cargar_definicion=cargar_definicion_objetivo,
    )
    reportes = ServicioReportes(
        raiz=raiz,
        fuente_configuracion=FuenteConfiguracionYaml,
        repositorio=RepositorioSqlite,
        capturador=CapturadorEntornoLocal,
        exportar_tabla=_exportar,
        leer_yaml=leer_yaml,
    )
    escenarios = ServicioEscenarios(
        raiz=raiz,
        fuente_catalogo=FuenteCatalogoYaml,
        fuente_variables=_fuente_variables,
        fuente_diccionario=_fuente_diccionario,
        preparar_historial=datos.preparar_historial,
        cargar_poblaciones=cargar_configuracion_poblaciones,
        guardar_division=guardar_division,
        cargador_de_prueba=cargador_de_prueba,
        registrar_acceso=reportes.registrar_acceso,
        carpeta_trabajo=reportes.carpeta_trabajo,
    )
    archivo_registro = reportes.archivo_registro
    protocolo = ServicioProtocolo(raiz, RepositorioSqlite, archivo_registro, leer_yaml)
    experimentos = ServicioExperimentos(
        raiz,
        RepositorioSqlite,
        archivo_registro,
        leer_yaml,
        preparar_historial=datos.preparar_historial,
        cargar_poblaciones=cargar_configuracion_poblaciones,
        fuente_catalogo=FuenteCatalogoYaml,
        fuente_diccionario=_fuente_diccionario,
        cargar_experimentos=cargar_configuracion_experimentos,
        preprocesar=_columnas_tras_preprocesar,
        capturador=CapturadorEntornoLocal(raiz),
        carpeta_trabajo=reportes.carpeta_trabajo,
        entrenar_familia=_entrenar_en_folds,
        guardar_corrida=guardar_corrida,
        leer_predicciones=leer_predicciones,
        ajustar_final=_ajustar_final,
        guardar_modelo_final=guardar_modelo_final,
        leer_modelo=leer_modelo,
    )
    evaluacion_final = ServicioEvaluacionFinal(
        raiz,
        RepositorioSqlite,
        archivo_registro,
        leer_yaml,
        preparar_historial=datos.preparar_historial,
        cargar_poblaciones=cargar_configuracion_poblaciones,
        fuente_catalogo=FuenteCatalogoYaml,
        fuente_diccionario=_fuente_diccionario,
        cargar_experimentos=cargar_configuracion_experimentos,
        cargador_de_prueba=cargador_de_prueba,
        leer_manifiesto=leer_manifiesto,
        leer_modelo=leer_modelo,
        predecir=_predecir,
        capturador=CapturadorEntornoLocal(raiz),
        demostrar=lambda solicitud: ejecutar_demostracion_final(
            raiz, solicitud, crear_servicios, leer_yaml
        ),
        carpeta_trabajo=reportes.carpeta_trabajo,
        guardar_predicciones=guardar_predicciones_prueba,
        leer_csv=leer_csv_verificado,
    )
    interpretabilidad = ServicioInterpretabilidad(
        raiz,
        RepositorioSqlite,
        archivo_registro,
        preparar_historial=datos.preparar_historial,
        cargar_poblaciones=cargar_configuracion_poblaciones,
        fuente_catalogo=FuenteCatalogoYaml,
        fuente_diccionario=_fuente_diccionario,
        cargar_experimentos=cargar_configuracion_experimentos,
        leer_modelo=leer_modelo,
        explicar_modelo=_explicar_modelo,
        capturador=CapturadorEntornoLocal(raiz),
        carpeta_trabajo=reportes.carpeta_trabajo,
        guardar_tablas=guardar_explicaciones,
    )
    casos_de_uso: tuple[ServicioCasosDeUso, ...] = (
        datos,
        escenarios,
        protocolo,
        experimentos,
        evaluacion_final,
        interpretabilidad,
        reportes,
    )
    proyecto = ServicioProyecto(
        raiz=raiz,
        version_paquete=suficiencia.__version__,
        servicios=casos_de_uso,
        fuente_configuracion=FuenteConfiguracionYaml,
    )
    return Servicios(
        proyecto=proyecto,
        datos=datos,
        escenarios=escenarios,
        reportes=reportes,
        protocolo=protocolo,
        experimentos=experimentos,
        evaluacion_final=evaluacion_final,
        interpretabilidad=interpretabilidad,
        casos_de_uso=casos_de_uso,
    )
