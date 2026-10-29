"""Composición: construye los servicios con sus implementaciones concretas.

Es el único lugar de la aplicación que elige qué adaptador de persistencia o de
experimentación implementa cada puerto. La línea de comandos y la futura interfaz
obtienen aquí los servicios y no importan otras capas (contratos de ``.importlinter``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import suficiencia
from suficiencia.application._base import ServicioCasosDeUso
from suficiencia.application.servicio_datos import ServicioDatos
from suficiencia.application.servicio_escenarios import ServicioEscenarios
from suficiencia.application.servicio_evaluacion_final import ServicioEvaluacionFinal
from suficiencia.application.servicio_experimentos import ServicioExperimentos
from suficiencia.application.servicio_interpretabilidad import ServicioInterpretabilidad
from suficiencia.application.servicio_protocolo import ServicioProtocolo
from suficiencia.application.servicio_proyecto import ServicioProyecto
from suficiencia.application.servicio_reportes import ServicioReportes
from suficiencia.domain.errores import ErrorSuficiencia
from suficiencia.domain.huella import Huella
from suficiencia.domain.puertos import FuenteVariables, Seudonimizador
from suficiencia.persistence.configuracion import FuenteConfiguracionYaml
from suficiencia.persistence.diccionario_yaml import FuenteVariablesDiccionario, cargar_diccionario
from suficiencia.persistence.entorno import CapturadorEntornoLocal
from suficiencia.persistence.escenarios_yaml import FuenteCatalogoYaml, FuenteVariablesYaml
from suficiencia.persistence.exportacion import exportar_tabla
from suficiencia.persistence.lectores import contenido_canonico, escribir_csv, leer_tabla
from suficiencia.persistence.objetivo_yaml import cargar_definicion_objetivo
from suficiencia.persistence.particion_archivos import cargador_de_prueba, guardar_division
from suficiencia.persistence.poblaciones_yaml import cargar_configuracion_poblaciones
from suficiencia.persistence.repositorio_sqlite import RepositorioSqlite
from suficiencia.persistence.seudonimizacion import SeudonimizadorHmac


@dataclass(frozen=True)
class Servicios:
    """Servicios de aplicación listos para usar."""

    proyecto: ServicioProyecto
    datos: ServicioDatos
    escenarios: ServicioEscenarios
    reportes: ServicioReportes
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


def crear_servicios(raiz: Path) -> Servicios:
    """Construye los servicios para el proyecto ubicado en ``raiz``."""
    datos = ServicioDatos(
        raiz=raiz,
        cargar_diccionario=cargar_diccionario,
        leer_tabla=_leer,
        seudonimizador=_seudonimizador,
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
    casos_de_uso: tuple[ServicioCasosDeUso, ...] = (
        datos,
        escenarios,
        ServicioProtocolo(),
        ServicioExperimentos(),
        ServicioEvaluacionFinal(),
        ServicioInterpretabilidad(),
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
        casos_de_uso=casos_de_uso,
    )
