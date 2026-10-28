"""Servicio del proyecto: estado del motor y validación de la configuración.

No corresponde a ningún caso de uso de la sección 3; da soporte a todos (H2.1).
Recibe sus dependencias ya construidas (ver ``composicion.py``), de modo que las
pruebas pueden sustituirlas sin archivos.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from suficiencia.application._base import ServicioCasosDeUso
from suficiencia.application.contratos import (
    EstadoProyecto,
    ResultadoValidacionConfiguracion,
    SolicitudValidarConfiguracion,
)
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.puertos import FuenteConfiguracion

ARCHIVO_CONFIGURACION = Path("config") / "proyecto.yaml"


class ServicioProyecto:
    """Estado del motor y validación de ``config/proyecto.yaml``."""

    def __init__(
        self,
        raiz: Path,
        version_paquete: str,
        servicios: Sequence[ServicioCasosDeUso],
        fuente_configuracion: Callable[[Path], FuenteConfiguracion],
    ) -> None:
        self._raiz = raiz
        self._version_paquete = version_paquete
        self._servicios = tuple(servicios)
        self._fuente_configuracion = fuente_configuracion

    def estado(self) -> EstadoProyecto:
        return EstadoProyecto(
            version_paquete=self._version_paquete,
            servicios=tuple(servicio.estado() for servicio in self._servicios),
        )

    def validar_configuracion(
        self, solicitud: SolicitudValidarConfiguracion
    ) -> ResultadoValidacionConfiguracion:
        archivo = solicitud.archivo or self._raiz / ARCHIVO_CONFIGURACION
        try:
            configuracion = self._fuente_configuracion(archivo).cargar()
        except ConfiguracionInvalida as error:
            return ResultadoValidacionConfiguracion(
                valida=False, archivo=str(archivo), error=str(error)
            )
        return ResultadoValidacionConfiguracion(
            valida=True,
            archivo=str(archivo),
            nombre_proyecto=configuracion.nombre,
            version_especificacion=configuracion.version_especificacion,
            semilla_global_definida=configuracion.semilla_global is not None,
            tolerancia_metricas_definida=configuracion.tolerancia_metricas is not None,
        )
