"""Servicio de protocolo confirmatorio y desviaciones (M4): CU-05.

Desde H2.6: guardar borradores del protocolo, aprobarlos, consultar sus versiones
y registrar desviaciones. Todo queda en el registro de solo agregar (DP-16).

Reglas que el servicio agrega a las del dominio:

- Un protocolo marcado como ficticio nunca se aprueba en el registro del
  proyecto. Para ver el recorrido completo con el ejemplo ficticio está
  ``demostracion``, que trabaja en un registro temporal.
- Para aprobar un protocolo real, cada decisión que exige CU-05 (DP-06, 07, 08,
  09, 10, 12, 17, 19 y 20) debe estar registrada en el registro de decisiones.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    DesviacionResumen,
    ResultadoAprobacionProtocolo,
    ResultadoBorradorProtocolo,
    ResultadoConsultaProtocolo,
    ResultadoDemostracionProtocolo,
    SolicitudAprobarProtocolo,
    SolicitudGuardarBorrador,
    VersionProtocoloResumen,
)
from suficiencia.application.demostracion_protocolo import ejecutar_demostracion
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente, ErrorSuficiencia
from suficiencia.domain.evaluacion.protocolo import (
    DECISIONES_DEL_PROTOCOLO,
    DatosDesviacion,
    HistorialProtocolo,
    aprobar,
    contenido_desde_datos,
    guardar_borrador,
)
from suficiencia.domain.puertos import RepositorioRegistros
from suficiencia.domain.trazabilidad.registros import ModoExperimento, TipoRegistro


class ProtocoloFicticioNoAprobable(ErrorSuficiencia):
    def __init__(self, version: int) -> None:
        super().__init__(
            f"La versión {version} del protocolo está marcada como ejemplo ficticio y no se "
            "aprueba en el registro del proyecto.",
            "Use `suficiencia protocolo demostracion` para ver el recorrido con el ejemplo. "
            "El protocolo real se aprueba cuando el equipo y la asesoría resuelvan sus decisiones.",
        )


def historial_protocolo(repositorio: RepositorioRegistros) -> HistorialProtocolo:
    """Versiones del protocolo según el registro."""
    return HistorialProtocolo.desde_registros(
        [g.contenido for g in repositorio.listar(TipoRegistro.PROTOCOLO)]
    )


def experimentos_confirmatorios(repositorio: RepositorioRegistros) -> tuple[str, ...]:
    """Identificadores de los experimentos confirmatorios registrados."""
    return tuple(
        g.contenido["identificador"]
        for g in repositorio.listar(TipoRegistro.EXPERIMENTO)
        if g.contenido["modo"] == ModoExperimento.CONFIRMATORIO.value
    )


class ServicioProtocolo(ServicioCasosDeUso):
    """Protocolo confirmatorio y desviaciones (M4)."""

    NOMBRE: ClassVar[str] = "protocolo"
    DESCRIPCION: ClassVar[str] = "Protocolo confirmatorio y desviaciones (M4)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-05",
            "Definir y aprobar el protocolo confirmatorio",
            "H2.6; el protocolo real espera DP-06 a DP-20",
            avance="borrador, aprobación, versiones y desviaciones (H2.6): `suficiencia protocolo`",
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

    def _ruta(self, archivo: Path) -> Path:
        return archivo if archivo.is_absolute() else self._raiz / archivo

    def _registro(self) -> RepositorioRegistros:
        return self._repositorio(self._archivo_registro())

    def guardar_borrador(self, solicitud: SolicitudGuardarBorrador) -> ResultadoBorradorProtocolo:
        """Lee el protocolo y lo guarda como borrador (CU-05, paso de definición)."""
        contenido = contenido_desde_datos(self._leer_yaml(self._ruta(solicitud.archivo)))
        repositorio = self._registro()
        registro = guardar_borrador(historial_protocolo(repositorio), contenido, solicitud.version)
        repositorio.agregar(registro)
        return ResultadoBorradorProtocolo(
            version=registro.version,
            huella=registro.huella,
            ficticio=contenido.ficticio,
            decisiones_faltantes=contenido.decisiones_faltantes(),
            archivo_registro=str(self._archivo_registro()),
        )

    def aprobar(self, solicitud: SolicitudAprobarProtocolo) -> ResultadoAprobacionProtocolo:
        """Aprueba una versión en borrador (CU-05).

        Raises:
            ProtocoloFicticioNoAprobable: si la versión es un ejemplo ficticio.
            DecisionPendiente: si falta una decisión en el protocolo o en el registro.
            DesviacionRequerida: si hay experimentos confirmatorios y no se da la desviación.
        """
        if (solicitud.desviacion is None) != (solicitud.justificacion is None):
            raise ConfiguracionInvalida(
                "La desviación necesita descripción y justificación.",
                "Indique las dos, o ninguna si no hay desviación.",
            )
        repositorio = self._registro()
        historial = historial_protocolo(repositorio)
        version = historial.version(solicitud.version)
        if version.contenido.ficticio:
            raise ProtocoloFicticioNoAprobable(version.numero)
        registradas = {g.contenido["codigo"] for g in repositorio.listar(TipoRegistro.DECISION)}
        for codigo in DECISIONES_DEL_PROTOCOLO:
            if codigo not in registradas:
                raise DecisionPendiente(
                    codigo, f"el registro de la decisión {codigo} (`suficiencia registro decision`)"
                )
        anterior = historial.vigente()
        desviacion = (
            DatosDesviacion(solicitud.desviacion, solicitud.justificacion)
            if solicitud.desviacion is not None and solicitud.justificacion is not None
            else None
        )
        resultado = aprobar(
            historial,
            solicitud.version,
            solicitud.huella,
            solicitud.responsable,
            experimentos_confirmatorios(repositorio),
            desviacion,
        )
        if resultado.desviacion is not None:
            repositorio.agregar(resultado.desviacion)
        repositorio.agregar(resultado.aprobacion)
        return ResultadoAprobacionProtocolo(
            version=resultado.aprobacion.version,
            huella=resultado.aprobacion.huella,
            version_reemplazada=anterior.numero if anterior else None,
            desviacion_registrada=resultado.desviacion is not None,
            resultados_afectados=(
                resultado.desviacion.resultados_afectados if resultado.desviacion else ()
            ),
        )

    def consultar(self) -> ResultadoConsultaProtocolo:
        """Versiones del protocolo, la vigente y las desviaciones registradas."""
        repositorio = self._registro()
        historial = historial_protocolo(repositorio)
        vigente = historial.vigente()
        return ResultadoConsultaProtocolo(
            archivo_registro=str(self._archivo_registro()),
            versiones=tuple(
                VersionProtocoloResumen(
                    numero=v.numero,
                    estado=v.estado.value,
                    huella=v.huella.valor,
                    ficticio=v.contenido.ficticio,
                    responsable_aprobacion=v.responsable_aprobacion,
                    decisiones_faltantes=v.contenido.decisiones_faltantes(),
                    multiplicidad=v.contenido.criterio.multiplicidad,
                    condiciones=len(v.contenido.criterio.condiciones),
                )
                for v in historial.versiones
            ),
            vigente=vigente.numero if vigente else None,
            desviaciones=tuple(
                DesviacionResumen(
                    version_anterior=g.contenido["version_anterior"],
                    version_nueva=g.contenido["version_nueva"],
                    descripcion=g.contenido["descripcion"],
                    justificacion=g.contenido["justificacion"],
                    responsable=g.contenido["responsable"],
                    resultados_afectados=tuple(g.contenido["resultados_afectados"]),
                )
                for g in repositorio.listar(TipoRegistro.DESVIACION)
            ),
        )

    def demostracion(self, archivo_protocolo: Path) -> ResultadoDemostracionProtocolo:
        """Recorre el ciclo completo con un protocolo ficticio en un registro temporal.

        No escribe en el registro del proyecto.
        """
        return ejecutar_demostracion(
            self._ruta(archivo_protocolo), self._leer_yaml, self._repositorio
        )
