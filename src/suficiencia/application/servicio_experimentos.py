"""Servicio de experimentos de desarrollo, selección y congelamiento (M3, M4): CU-06 y CU-07.

Desde H2.6: congelar una configuración con su huella (RF-M4-12). Congelar exige un
protocolo aprobado vigente. Los experimentos de desarrollo y la selección del
modelo representativo (DP-10) llegan en fases posteriores.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import ResultadoCongelamiento, SolicitudCongelar
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.evaluacion.congelamiento import configuracion_desde_datos, congelar
from suficiencia.domain.puertos import RepositorioRegistros
from suficiencia.domain.trazabilidad.registros import TipoRegistro


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
            "CU-06", "Ejecutar experimentos de desarrollo", "una fase posterior a la Fase 2"
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
    ) -> None:
        self._raiz = raiz
        self._repositorio = repositorio
        self._archivo_registro = archivo_registro
        self._leer_yaml = leer_yaml

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
