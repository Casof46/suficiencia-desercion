"""Servicio de trazabilidad y reportes (M6): CU-10.

Desde H2.7: entorno de ejecución, registro de decisiones, consulta, verificación
de integridad y exportación de los registros (DP-16: SQLite). Desde H2.8: estado de
las decisiones DP-01 a DP-20 según el catálogo y el registro. Los reportes de
experimentos y el reporte comparativo (RF-M6-04, RF-M6-07) llegan cuando existan
experimentos, en fases posteriores. Desde F3.7: el reporte de resultados de una
evaluación final, con su comparación y su interpretabilidad (RF-M6-04, RF-M6-07), que
solo se exporta con el rótulo de datos sintéticos (RNF-19, PI-16); la exportación de
experimentos del registro lleva también la columna de rótulo.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    DecisionRegistradaResumen,
    EntornoResumen,
    EstadoDecisionResumen,
    RegistroResumen,
    ReporteResultados,
    ResultadoComparacion,
    ResultadoConsultaRegistro,
    ResultadoDemostracion,
    ResultadoEstadoDecisiones,
    ResultadoEvaluacionFinal,
    ResultadoExplicacion,
    ResultadoExportacion,
    ResultadoExportacionResultados,
    ResultadoIntegridad,
    SolicitudConsultarRegistro,
    SolicitudExportarRegistro,
    SolicitudExportarResultados,
    SolicitudRegistrarDecision,
)
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.application.reporte_resultados import construir_reporte, exigir_rotulos
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.huella import Huella
from suficiencia.domain.proyecto import ConfiguracionProyecto
from suficiencia.domain.puertos import CapturadorEntorno, FuenteConfiguracion, RepositorioRegistros
from suficiencia.domain.trazabilidad.decisiones import (
    DecisionRegistrada,
    catalogo_desde_datos,
    estado_decisiones,
)
from suficiencia.domain.trazabilidad.registros import (
    ModoExperimento,
    RegistroAcceso,
    RegistroDecision,
    RegistroGuardado,
    TipoRegistro,
    verificar_cadena,
)
from suficiencia.domain.trazabilidad.rotulo import (
    CAMPO_ORIGEN,
    OrigenDatos,
    exigir_rotulo_tabla,
    origen_de_registro,
    valor_rotulo,
)

ARCHIVO_CONFIGURACION = Path("config") / "proyecto.yaml"
ARCHIVO_REGISTRO = "registro.sqlite"
ARCHIVO_DEMOSTRACION = "registro_demostracion.sqlite"
ARCHIVO_CATALOGO_DECISIONES = Path("config") / "decisiones_metodologicas.yaml"
CARPETA_FICHAS = Path("docs") / "decisiones"


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
    if filas and registros[0].tipo is TipoRegistro.EXPERIMENTO:
        # Resultados de experimentos: rótulo de origen en cada fila (RNF-19).
        for fila, registro in zip(filas, registros, strict=True):
            fila[CAMPO_ORIGEN] = valor_rotulo(
                origen_de_registro(registro.contenido.get("configuracion", {}))
            )
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
            "los reportes de experimentos del proyecto, cuando exista un protocolo aprobado",
            avance="registro de decisiones, consulta, verificación y exportación (H2.7): "
            "`suficiencia registro`; reporte de resultados rotulado de la demostración (F3.7)",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        fuente_configuracion: Callable[[Path], FuenteConfiguracion],
        repositorio: Callable[[Path], RepositorioRegistros],
        capturador: Callable[[Path], CapturadorEntorno],
        exportar_tabla: Callable[[pd.DataFrame, Path], Huella],
        leer_yaml: Callable[[Path], Any],
        archivos_resultados: Callable[[str, Mapping[str, pd.DataFrame]], dict[str, bytes]],
        escribir_archivos: Callable[[Path, Mapping[str, bytes]], dict[str, str]],
    ) -> None:
        self._raiz = raiz
        self._fuente_configuracion = fuente_configuracion
        self._repositorio = repositorio
        self._capturador = capturador
        self._exportar_tabla = exportar_tabla
        self._leer_yaml = leer_yaml
        self._archivos_resultados = archivos_resultados
        self._escribir_archivos = escribir_archivos

    def _configuracion(self) -> ConfiguracionProyecto:
        return self._fuente_configuracion(self._raiz / ARCHIVO_CONFIGURACION).cargar()

    def repositorio(self) -> RepositorioRegistros:
        """Registro del proyecto (en una demostración, el del proyecto temporal)."""
        return self._repositorio(self.archivo_registro())

    def archivo_registro(self) -> Path:
        return self._configuracion().rutas["espacio_trabajo"] / ARCHIVO_REGISTRO

    def carpeta_trabajo(self) -> Path:
        """Carpeta de trabajo del proyecto (``workspace/``, no versionada)."""
        return self._configuracion().rutas["espacio_trabajo"]

    def registrar_acceso(self, registro: RegistroAcceso) -> RegistroResumen:
        """Agrega un intento de acceso a la prueba al registro (RF-M6-06)."""
        return _resumen(self._repositorio(self.archivo_registro()).agregar(registro))

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
        if registros and registros[0].tipo is TipoRegistro.EXPERIMENTO:
            sinteticas = [
                origen_de_registro(r.contenido.get("configuracion", {})) is OrigenDatos.SINTETICO
                for r in registros
            ]
            columnas = [str(c) for c in tabla.columns]
            valores: list[Any] = (
                list(tabla.loc[sinteticas, CAMPO_ORIGEN]) if CAMPO_ORIGEN in columnas else []
            )
            exigir_rotulo_tabla(solicitud.tipo, columnas, valores, OrigenDatos.SINTETICO)
        huella = self._exportar_tabla(tabla, destino)
        return ResultadoExportacion(archivo=str(destino), filas=len(tabla), huella=huella.valor)

    def reporte_resultados(
        self,
        evaluacion: ResultadoEvaluacionFinal,
        comparacion: ResultadoComparacion,
        explicacion: ResultadoExplicacion | None,
    ) -> ReporteResultados:
        """Reporte de una evaluación final con su comparación y su explicación (F3.7)."""
        return construir_reporte(evaluacion, comparacion, explicacion)

    def contenido_resultados(self, reporte: ReporteResultados) -> dict[str, bytes]:
        """Archivos del reporte en memoria (texto, CSV y Excel), para descargarlos.

        Raises:
            RotuloFaltante: si el reporte de datos sintéticos no lleva el rótulo (PI-16).
            IdentificadorEnExportacion: si alguna tabla tiene identificadores (RNF-05).
        """
        exigir_rotulos(reporte)
        tablas = {
            t.nombre: pd.DataFrame(list(t.filas), columns=list(t.columnas)) for t in reporte.tablas
        }
        return self._archivos_resultados(reporte.texto, tablas)

    def exportar_resultados(
        self, solicitud: SolicitudExportarResultados
    ) -> ResultadoExportacionResultados:
        """Escribe el reporte en una carpeta nueva dentro de ``reports/`` (RF-M6-03).

        Raises:
            RotuloFaltante: si el reporte de datos sintéticos no lleva el rótulo (PI-16).
            ConfiguracionInvalida: si la carpeta está fuera de ``reports/`` o ya existe.
        """
        reportes = self._configuracion().rutas["reportes"]
        destino = (
            solicitud.carpeta if solicitud.carpeta.is_absolute() else self._raiz / solicitud.carpeta
        )
        if not destino.resolve().is_relative_to(reportes.resolve()):
            raise ConfiguracionInvalida(
                f"La carpeta {solicitud.carpeta} está fuera de la carpeta de reportes.",
                f"Guárdela dentro de {reportes.name}/, que git no versiona.",
            )
        archivos = self.contenido_resultados(solicitud.reporte)
        huellas = self._escribir_archivos(destino, archivos)
        return ResultadoExportacionResultados(carpeta=str(destino), archivos=huellas)

    def estado_decisiones(self) -> ResultadoEstadoDecisiones:
        """Cada decisión DP-01 a DP-20: registrada o abierta, con sus registros y su ficha."""
        catalogo = catalogo_desde_datos(self._leer_yaml(self._raiz / ARCHIVO_CATALOGO_DECISIONES))
        archivo = self.archivo_registro()
        registros = [
            DecisionRegistrada(
                codigo=g.contenido["codigo"],
                fecha=g.fecha,
                decision=g.contenido["decision"],
                responsable=g.contenido["responsable"],
                observaciones=g.contenido.get("observaciones"),
            )
            for g in self._repositorio(archivo).listar(TipoRegistro.DECISION)
        ]
        estados = estado_decisiones(catalogo, registros)
        resumenes = []
        for estado in estados:
            ficha = self._raiz / CARPETA_FICHAS / f"{estado.catalogada.codigo}.md"
            resumenes.append(
                EstadoDecisionResumen(
                    codigo=estado.catalogada.codigo,
                    nombre=estado.catalogada.nombre,
                    decide=estado.catalogada.decide,
                    resolver_antes_de=estado.catalogada.resolver_antes_de,
                    registrada=estado.registrada,
                    registros=tuple(
                        DecisionRegistradaResumen(
                            codigo=r.codigo,
                            fecha=r.fecha,
                            decision=r.decision,
                            responsable=r.responsable,
                            observaciones=r.observaciones,
                        )
                        for r in estado.registros
                    ),
                    ficha=(CARPETA_FICHAS / ficha.name).as_posix() if ficha.is_file() else None,
                )
            )
        registradas = sum(e.registrada for e in estados)
        return ResultadoEstadoDecisiones(
            archivo_registro=str(archivo),
            decisiones=tuple(resumenes),
            registradas=registradas,
            abiertas=len(estados) - registradas,
        )

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
