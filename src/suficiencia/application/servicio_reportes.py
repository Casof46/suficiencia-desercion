"""Servicio de trazabilidad y reportes (M6): CU-10.

Desde H2.7: entorno de ejecución, registro de decisiones, consulta, verificación
de integridad y exportación de los registros (DP-16: SQLite). Los reportes de
experimentos y el reporte comparativo (RF-M6-04, RF-M6-07) llegan cuando existan
experimentos, en fases posteriores.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    EntornoResumen,
    RegistroResumen,
    ResultadoConsultaRegistro,
    ResultadoDemostracion,
    ResultadoExportacion,
    ResultadoIntegridad,
    SolicitudConsultarRegistro,
    SolicitudExportarRegistro,
    SolicitudRegistrarDecision,
)
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.huella import Huella
from suficiencia.domain.proyecto import ConfiguracionProyecto
from suficiencia.domain.puertos import CapturadorEntorno, FuenteConfiguracion, RepositorioRegistros
from suficiencia.domain.trazabilidad.registros import (
    ModoExperimento,
    RegistroDecision,
    RegistroGuardado,
    TipoRegistro,
    verificar_cadena,
)

ARCHIVO_CONFIGURACION = Path("config") / "proyecto.yaml"
ARCHIVO_REGISTRO = "registro.sqlite"
ARCHIVO_DEMOSTRACION = "registro_demostracion.sqlite"


def _resumen(guardado: RegistroGuardado) -> RegistroResumen:
    return RegistroResumen(
        tipo=guardado.tipo.value,
        numero=guardado.numero,
        fecha=guardado.fecha,
        huella=guardado.huella,
        contenido=guardado.contenido,
    )


def _tabla(registros: list[RegistroGuardado]) -> pd.DataFrame:
    filas: list[dict[str, Any]] = [
        {"numero": r.numero, "fecha": r.fecha, "huella": r.huella, **r.contenido} for r in registros
    ]
    return (
        pd.json_normalize(filas, sep=".")
        if filas
        else pd.DataFrame(columns=["numero", "fecha", "huella"])
    )


class ServicioReportes(ServicioCasosDeUso):
    """Trazabilidad y reportes (M6)."""

    NOMBRE: ClassVar[str] = "reportes"
    DESCRIPCION: ClassVar[str] = "Trazabilidad y reportes (M6)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-10",
            "Consultar trazabilidad y exportar reporte",
            "los reportes de experimentos, cuando existan experimentos (fase posterior)",
            avance="registro de decisiones, consulta, verificación y exportación (H2.7): "
            "`suficiencia registro`",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        fuente_configuracion: Callable[[Path], FuenteConfiguracion],
        repositorio: Callable[[Path], RepositorioRegistros],
        capturador: Callable[[Path], CapturadorEntorno],
        exportar_tabla: Callable[[pd.DataFrame, Path], Huella],
    ) -> None:
        self._raiz = raiz
        self._fuente_configuracion = fuente_configuracion
        self._repositorio = repositorio
        self._capturador = capturador
        self._exportar_tabla = exportar_tabla

    def _configuracion(self) -> ConfiguracionProyecto:
        return self._fuente_configuracion(self._raiz / ARCHIVO_CONFIGURACION).cargar()

    def archivo_registro(self) -> Path:
        return self._configuracion().rutas["espacio_trabajo"] / ARCHIVO_REGISTRO

    def entorno(self) -> EntornoResumen:
        entorno = self._capturador(self._raiz).capturar()
        return EntornoResumen(
            python=entorno.python,
            sistema=entorno.sistema,
            huella_bloqueo=entorno.huella_bloqueo,
            commit=entorno.commit,
            cambios_sin_commit=entorno.cambios_sin_commit,
            nucleos=entorno.nucleos,
            hilos=entorno.hilos,
            paquetes=entorno.paquetes,
        )

    def registrar_decision(self, solicitud: SolicitudRegistrarDecision) -> RegistroResumen:
        registro = RegistroDecision(
            codigo=solicitud.codigo,
            decision=solicitud.decision,
            justificacion=solicitud.justificacion,
            responsable=solicitud.responsable,
            observaciones=solicitud.observaciones,
        )
        return _resumen(self._repositorio(self.archivo_registro()).agregar(registro))

    def consultar(self, solicitud: SolicitudConsultarRegistro) -> ResultadoConsultaRegistro:
        archivo = self.archivo_registro()
        registros = self._repositorio(archivo).listar(TipoRegistro(solicitud.tipo))
        return ResultadoConsultaRegistro(
            archivo=str(archivo),
            tipo=solicitud.tipo,
            registros=tuple(_resumen(r) for r in registros),
        )

    def verificar(self) -> ResultadoIntegridad:
        """Recalcula la cadena de huellas de cada tipo de registro."""
        archivo = self.archivo_registro()
        repositorio = self._repositorio(archivo)
        conteos: dict[str, int] = {}
        problemas: list[str] = []
        for tipo in TipoRegistro:
            registros = repositorio.listar(tipo)
            conteos[tipo.value] = len(registros)
            problemas += [
                f"{p.tipo.value} n.º {p.numero}: {p.descripcion}"
                for p in verificar_cadena(tipo, registros)
            ]
        return ResultadoIntegridad(
            archivo=str(archivo),
            correcto=not problemas,
            registros_por_tipo=conteos,
            problemas=tuple(problemas),
        )

    def exportar(self, solicitud: SolicitudExportarRegistro) -> ResultadoExportacion:
        """Exporta un tipo de registro, pasando por el filtro de identificadores."""
        configuracion = self._configuracion()
        reportes = configuracion.rutas["reportes"]
        destino = (
            solicitud.salida if solicitud.salida.is_absolute() else self._raiz / solicitud.salida
        )
        if not destino.resolve().is_relative_to(reportes.resolve()):
            raise ConfiguracionInvalida(
                f"La exportación {solicitud.salida} está fuera de la carpeta de reportes.",
                f"Guárdela dentro de {reportes.name}/, que git no versiona.",
            )
        registros = self._repositorio(self.archivo_registro()).listar(TipoRegistro(solicitud.tipo))
        tabla = _tabla(registros)
        huella = self._exportar_tabla(tabla, destino)
        return ResultadoExportacion(archivo=str(destino), filas=len(tabla), huella=huella.valor)

    def demostracion(self) -> ResultadoDemostracion:
        """Registra dos corridas simuladas, una exitosa y una fallida, en un registro aparte.

        Usa ``registro_demostracion.sqlite`` para no mezclar corridas simuladas con
        el registro del proyecto. No entrena ningún modelo.
        """
        archivo = self._configuracion().rutas["espacio_trabajo"] / ARCHIVO_DEMOSTRACION
        registrador = RegistradorCorridas(self._repositorio(archivo), self._capturador(self._raiz))
        configuracion = {"simulacion": True, "aviso": "corrida simulada de H2.7, sin modelo"}

        def exitosa() -> dict[str, Any]:
            return {"mensaje": "corrida simulada completada"}

        def fallida() -> dict[str, Any]:
            raise RuntimeError("falla simulada a propósito")

        guardados = [
            registrador.ejecutar(
                funcion,
                modo=ModoExperimento.EXPLORATORIO,
                configuracion=configuracion,
                semillas={"demostracion": 0},
                huella_datos=None,
                version_protocolo=None,
            )
            for funcion in (exitosa, fallida)
        ]
        return ResultadoDemostracion(
            archivo=str(archivo), registros=tuple(_resumen(g) for g in guardados)
        )
