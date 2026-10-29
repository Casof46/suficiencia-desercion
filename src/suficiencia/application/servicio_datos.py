"""Servicio de importación, diccionario, auditoría y objetivo (M1): CU-01 a CU-03.

Desde H2.3 valida diccionarios (parte de CU-02) e importa, seudonimiza y audita
archivos **sintéticos** (CU-01 con datos sintéticos). Importar datos reales sigue
bloqueado: requiere DP-02 y DP-14, y el servicio rechaza todo archivo cuyas filas
no estén marcadas como sintéticas.

Desde H2.4 construye el objetivo y los estados de etiqueta (CU-03) con datos
sintéticos y una definición que, mientras DP-01 y DP-18 sigan abiertas, solo
puede ser un ejemplo ficticio. El resultado no muestra la distribución de los
estados de etiqueta: se reporta solo en desarrollo, después del sellado (RF-M1-03).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    CasoDemostracionObjetivo,
    ColumnaAuditada,
    InformeAuditoriaResumen,
    ParametroObjetivo,
    RasgoResumen,
    ResultadoDefinicionObjetivo,
    ResultadoDemostracionObjetivo,
    ResultadoDiccionario,
    ResultadoImportacion,
    ResultadoObjetivo,
    SolicitudConstruirObjetivo,
    SolicitudImportarDataset,
    SolicitudValidarDiccionario,
    SolicitudValidarObjetivo,
)
from suficiencia.application.demostracion_objetivo import CASOS, DEFINICION_DEMOSTRACION
from suficiencia.domain.datos.auditoria import (
    InformeAuditoria,
    ResultadoAuditoria,
    auditar,
    exigir_apto,
)
from suficiencia.domain.datos.diccionario import (
    COLUMNA_SEUDONIMO,
    VALOR_ORIGEN_SINTETICO,
    Diccionario,
    Rol,
)
from suficiencia.domain.datos.objetivo import (
    ColumnasHistorial,
    DefinicionObjetivo,
    Unidad,
    codigos_sin_categoria,
    construir_objetivo,
    etiquetar_unidad,
)
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.huella import Huella
from suficiencia.domain.puertos import Seudonimizador

CARPETA_DATOS = Path("data")


@dataclass(frozen=True)
class HistorialPreparado:
    """Historial sintético seudonimizado y con auditoría apta, listo para etiquetar."""

    tabla: pd.DataFrame
    columnas: ColumnasHistorial
    definicion: DefinicionObjetivo
    sintetico: bool
    huella_fuente: Huella
    huella_dataset: Huella


DEFINICION_OBJETIVO_DEL_PROYECTO = Path("config/objetivo/definicion.yaml")


def _resumen(informe: InformeAuditoria) -> InformeAuditoriaResumen:
    return InformeAuditoriaResumen(
        n_filas=informe.n_filas,
        n_columnas=informe.n_columnas,
        columnas=tuple(
            ColumnaAuditada(
                nombre=c.nombre,
                rol=c.rol,
                tipo=c.tipo,
                nulos=c.nulos,
                tipo_invalido=c.tipo_invalido,
                fuera_de_dominio=c.fuera_de_dominio,
                cardinalidad=c.cardinalidad,
                minimo=c.minimo,
                maximo=c.maximo,
                filas_con_problemas=c.filas_con_problemas,
            )
            for c in informe.columnas
        ),
        duplicados_clave=informe.duplicados_clave,
        filas_duplicadas=informe.filas_duplicadas,
        errores_criticos=informe.errores_criticos,
        alertas=informe.alertas,
        apto_para_m2=informe.apto_para_m2,
    )


def _exigir_sintetico(tabla: pd.DataFrame, diccionario: Diccionario, archivo: Path) -> None:
    """Rechaza cualquier archivo que no esté marcado como sintético en todas sus filas."""
    columna = diccionario.columna_origen
    marcado = (
        columna is not None
        and columna in tabla.columns
        and len(tabla) > 0
        and bool((tabla[columna].astype("string").str.strip() == VALOR_ORIGEN_SINTETICO).all())
    )
    if not marcado:
        raise DecisionPendiente(
            "DP-02",
            f"la autorización para importar datos que no son sintéticos ({archivo.name} tiene "
            f"filas sin la marca {VALOR_ORIGEN_SINTETICO} en la columna de origen)",
        )


class ServicioDatos(ServicioCasosDeUso):
    """Importación, diccionario, auditoría y objetivo (M1)."""

    NOMBRE: ClassVar[str] = "datos"
    DESCRIPCION: ClassVar[str] = "Importación, diccionario, auditoría y objetivo (M1)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-01",
            "Importar y auditar un dataset",
            "con datos reales, cuando se resuelvan DP-02 y DP-14",
            avance="importación, seudonimización y auditoría de datos sintéticos (H2.3): "
            "`suficiencia datos importar`",
        ),
        DefinicionCasoDeUso(
            "CU-02",
            "Configurar el diccionario de variables",
            "con el diccionario real, cuando se resuelvan DP-03 y DP-15",
            avance="validación de diccionarios (H2.3): `suficiencia datos diccionario`",
        ),
        DefinicionCasoDeUso(
            "CU-03",
            "Construir el objetivo y los estados de etiqueta",
            "con la definición real, cuando se aprueben DP-01 y DP-18",
            avance="objetivo y estados de etiqueta con datos sintéticos y definiciones "
            "ficticias (H2.4): `suficiencia objetivo`",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        cargar_diccionario: Callable[[Path], Diccionario],
        leer_tabla: Callable[[Path, str], tuple[pd.DataFrame, Huella]],
        seudonimizador: Callable[[bool], Seudonimizador],
        huella_de_tabla: Callable[[pd.DataFrame], Huella],
        escribir_tabla: Callable[[pd.DataFrame, Path], Huella],
        cargar_definicion: Callable[[Path], DefinicionObjetivo],
    ) -> None:
        self._raiz = raiz
        self._cargar_diccionario = cargar_diccionario
        self._leer_tabla = leer_tabla
        self._seudonimizador = seudonimizador
        self._huella_de_tabla = huella_de_tabla
        self._escribir_tabla = escribir_tabla
        self._cargar_definicion = cargar_definicion

    def validar_diccionario(self, solicitud: SolicitudValidarDiccionario) -> ResultadoDiccionario:
        diccionario = self._cargar_diccionario(solicitud.archivo)
        return ResultadoDiccionario(
            nombre=diccionario.nombre,
            ficticio=diccionario.ficticio,
            variables_por_rol=dict(Counter(v.rol.value for v in diccionario.variables)),
            rasgos=tuple(
                RasgoResumen(
                    nombre=v.nombre, bloque=v.bloque.value, ventana_minima=v.ventana_minima
                )
                for v in diccionario.variables_de_escenario()
            ),
            clave=diccionario.clave,
        )

    def _validar_salida(self, salida: Path) -> Path:
        destino = salida if salida.is_absolute() else self._raiz / salida
        permitida = (self._raiz / CARPETA_DATOS).resolve()
        if not destino.resolve().is_relative_to(permitida):
            raise ConfiguracionInvalida(
                f"La salida {salida} está fuera de la carpeta data/.",
                "Guarde los datasets procesados dentro de data/, que git no versiona.",
            )
        return destino

    def importar_dataset(self, solicitud: SolicitudImportarDataset) -> ResultadoImportacion:
        """Importa un archivo sintético: lo seudonimiza primero y después lo audita.

        Raises:
            DecisionPendiente: si el archivo no es sintético (DP-02) o falta la clave (DP-14).
            ConfiguracionInvalida: si el archivo o el diccionario no se pueden leer.
        """
        diccionario = self._cargar_diccionario(solicitud.diccionario)
        destino = self._validar_salida(solicitud.salida) if solicitud.salida else None
        resultado, huella_fuente = self._importar(
            solicitud.archivo, diccionario, solicitud.clave_efimera, solicitud.separador
        )

        huella_procesado: Huella | None = None
        if resultado.informe.apto_para_m2:
            huella_procesado = (
                self._escribir_tabla(resultado.tabla, destino)
                if destino is not None
                else self._huella_de_tabla(resultado.tabla)
            )
        return ResultadoImportacion(
            archivo=str(solicitud.archivo),
            sintetico=resultado.informe.sintetico,
            huella_fuente=huella_fuente.valor,
            columnas_seudonimizadas=diccionario.identificadores,
            informe=_resumen(resultado.informe),
            huella_procesado=huella_procesado.valor if huella_procesado else None,
            archivo_salida=str(destino) if destino is not None and huella_procesado else None,
        )

    def _importar(
        self, archivo: Path, diccionario: Diccionario, clave_efimera: bool, separador: str
    ) -> tuple[ResultadoAuditoria, Huella]:
        """Lee, exige la marca sintética, seudonimiza y audita (en ese orden)."""
        tabla, huella_fuente = self._leer_tabla(archivo, separador)
        _exigir_sintetico(tabla, diccionario, archivo)
        # La seudonimización ocurre antes de cualquier otra transformación (M1).
        seudonimizada = self._seudonimizador(clave_efimera).seudonimizar(
            tabla, diccionario.identificadores
        )
        del tabla
        return auditar(seudonimizada, diccionario), huella_fuente

    def _ruta_definicion(self, archivo: Path | None) -> Path:
        if archivo is None:
            return self._raiz / DEFINICION_OBJETIVO_DEL_PROYECTO
        return archivo if archivo.is_absolute() else self._raiz / archivo

    def validar_objetivo(self, solicitud: SolicitudValidarObjetivo) -> ResultadoDefinicionObjetivo:
        """Valida una definición del objetivo y la resume parámetro por parámetro."""
        ruta = self._ruta_definicion(solicitud.archivo)
        definicion = self._cargar_definicion(ruta)
        return ResultadoDefinicionObjetivo(
            archivo=str(solicitud.archivo or DEFINICION_OBJETIVO_DEL_PROYECTO),
            nombre=definicion.nombre,
            ficticio=definicion.ficticio,
            parametros=_parametros(definicion),
            catalogo={c: categoria.value for c, categoria in definicion.catalogo.items()},
        )

    def construir_objetivo(self, solicitud: SolicitudConstruirObjetivo) -> ResultadoObjetivo:
        """Importa y audita un archivo sintético y etiqueta cada unidad (CU-03).

        Raises:
            DecisionPendiente: si el archivo no es sintético (DP-02), falta la clave
                (DP-14) o la definición del proyecto todavía no existe (DP-01).
            AuditoriaConErrores: si la auditoría no es apta (PU-17).
            ConfiguracionInvalida: si la definición no encaja con el diccionario.
        """
        destino = self._validar_salida(solicitud.salida) if solicitud.salida else None
        historial = self.preparar_historial(
            solicitud.archivo,
            solicitud.diccionario,
            solicitud.definicion,
            solicitud.clave_efimera,
            solicitud.separador,
        )
        definicion = historial.definicion
        objetivo = construir_objetivo(historial.tabla, historial.columnas, definicion)
        huella_registros = (
            self._escribir_tabla(objetivo.registros, destino)
            if destino is not None
            else self._huella_de_tabla(objetivo.registros)
        )
        return ResultadoObjetivo(
            archivo=str(solicitud.archivo),
            sintetico=historial.sintetico,
            definicion=definicion.nombre,
            definicion_ficticia=definicion.ficticio,
            huella_fuente=historial.huella_fuente.valor,
            huella_dataset=historial.huella_dataset.valor,
            unidades=len(objetivo.registros),
            fuera_de_poblacion=objetivo.fuera_de_poblacion,
            fuera_de_cohortes=objetivo.fuera_de_cohortes,
            huella_registros=huella_registros.valor,
            archivo_salida=str(destino) if destino is not None else None,
        )

    def preparar_historial(
        self,
        archivo: Path,
        diccionario: Path,
        definicion: Path | None,
        clave_efimera: bool,
        separador: str,
    ) -> HistorialPreparado:
        """Carga la definición, importa y audita el archivo y exige una auditoría apta.

        Raises:
            DecisionPendiente: si el archivo no es sintético (DP-02), falta la clave
                (DP-14) o la definición del proyecto todavía no existe (DP-01).
            AuditoriaConErrores: si la auditoría no es apta (PU-17).
        """
        dic = self._cargar_diccionario(diccionario)
        definicion_objetivo = self._cargar_definicion(self._ruta_definicion(definicion))
        columnas = _columnas_del_historial(dic, definicion_objetivo)
        resultado, huella_fuente = self._importar(archivo, dic, clave_efimera, separador)
        exigir_apto(resultado.informe)
        return HistorialPreparado(
            tabla=resultado.tabla,
            columnas=columnas,
            definicion=definicion_objetivo,
            sintetico=resultado.informe.sintetico,
            huella_fuente=huella_fuente,
            huella_dataset=self._huella_de_tabla(resultado.tabla),
        )

    def demostracion_objetivo(self) -> ResultadoDemostracionObjetivo:
        """Etiqueta historiales ficticios escritos a mano con la definición de ejemplo."""
        definicion = self._cargar_definicion(self._raiz / DEFINICION_DEMOSTRACION)
        casos = []
        for caso in CASOS:
            etiqueta = etiquetar_unidad(caso.estados(), caso.periodos_observables, definicion)
            casos.append(
                CasoDemostracionObjetivo(
                    nombre=caso.nombre,
                    historial=caso.historial(),
                    periodos_observables=caso.periodos_observables,
                    estado=etiqueta.estado.value,
                    motivo=etiqueta.motivo.value if etiqueta.motivo else None,
                    periodo_evento=etiqueta.periodo_evento,
                )
            )
        return ResultadoDemostracionObjetivo(
            definicion=definicion.nombre,
            horizonte_periodos=definicion.horizonte_periodos,
            casos=tuple(casos),
        )


def _unica(diccionario: Diccionario, rol: Rol) -> str:
    columnas = diccionario.de_rol(rol)
    if len(columnas) != 1:
        raise ConfiguracionInvalida(
            f"El diccionario declara {len(columnas)} columnas con rol '{rol.value}'.",
            f"Para construir el objetivo se necesita exactamente una columna '{rol.value}'.",
        )
    return columnas[0].nombre


def _columnas_del_historial(
    diccionario: Diccionario, definicion: DefinicionObjetivo
) -> ColumnasHistorial:
    estado = diccionario.de_rol(Rol.OBJETIVO)
    if len(estado) != 1:
        raise ConfiguracionInvalida(
            f"El diccionario declara {len(estado)} columnas con rol 'objetivo'.",
            "Declare una sola columna con el estado de matrícula de cada periodo.",
        )
    sin_categoria = codigos_sin_categoria(estado[0].valores or (), definicion)
    if sin_categoria:
        raise ConfiguracionInvalida(
            f"Estados del diccionario sin categoría en el catálogo: {', '.join(sin_categoria)}.",
            "Agregue cada código al catálogo de la definición del objetivo (DP-01).",
        )
    unidad: tuple[str, ...] = (COLUMNA_SEUDONIMO,)
    if definicion.unidad is Unidad.ESTUDIANTE_CARRERA:
        assert definicion.columna_carrera is not None
        if definicion.columna_carrera not in diccionario.columnas:
            raise ConfiguracionInvalida(
                f"La columna de carrera '{definicion.columna_carrera}' no está en el diccionario.",
                "Declárela en el diccionario o use la unidad 'estudiante' (DP-01b).",
            )
        unidad += (definicion.columna_carrera,)
    return ColumnasHistorial(
        unidad=unidad,
        cohorte=_unica(diccionario, Rol.COHORTE),
        periodo=_unica(diccionario, Rol.PERIODO),
        estado=estado[0].nombre,
    )


def _parametros(definicion: DefinicionObjetivo) -> tuple[ParametroObjetivo, ...]:
    def lista(valores: frozenset[str] | frozenset[int] | None, vacio: str) -> str:
        if valores is None:
            return "todas"
        return ", ".join(str(v) for v in sorted(valores)) or vacio

    pausas = definicion.pausas.value
    if definicion.limite_pausas is not None:
        pausas += f" (hasta {definicion.limite_pausas} periodo(s) seguidos)"
    elif definicion.pausas.value == "neutral":
        pausas += " (sin límite)"
    filas = (
        ("DP-01a", "Periodos seguidos sin matrícula", str(definicion.periodos_sin_matricula)),
        ("DP-01b", "Unidad de análisis", definicion.unidad.value),
        ("DP-01c", "Población inicial", definicion.poblacion_inicial.value),
        ("DP-01c", "Cohortes", lista(definicion.cohortes, "ninguna")),
        ("DP-01e", "Horizonte (periodos)", str(definicion.horizonte_periodos)),
        ("DP-01e", "Horizonte desde", definicion.horizonte_desde.value),
        ("DP-01f", "Fechado del evento", definicion.fechado.value),
        ("DP-01g", "Pausas y reservas", pausas),
        ("DP-01h", "Retiro dentro del periodo", definicion.retiro_en_periodo.value),
        ("DP-01i", "Traslado interno", definicion.traslado_interno.value),
        ("DP-01i", "Traslado externo", definicion.traslado_externo.value),
        ("DP-01j", "Reingreso", definicion.reingreso.value),
        ("DP-01k", "Periodos extraordinarios", definicion.periodos_extraordinarios.value),
        ("DP-01k", "Lista de extraordinarios", lista(definicion.lista_extraordinarios, "ninguno")),
        ("DP-01l", "Desenlaces excluidos", definicion.desenlaces_excluidos.value),
        ("DP-01m", "Seguimiento exigido", definicion.seguimiento.value),
        ("DP-01m", "Periodo sin registro", definicion.registro_faltante.value),
        ("DP-18", "No etiquetables", definicion.tratamiento_no_etiquetables),
        ("DP-18", "Nivel para el análisis de sensibilidad", f"{definicion.nivel_sensibilidad:g}"),
    )
    return tuple(ParametroObjetivo(decision=d, parametro=p, valor=v) for d, p, v in filas)
