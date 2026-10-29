"""Servicio de importación, diccionario, auditoría y objetivo (M1): CU-01 a CU-03.

Desde H2.3 valida diccionarios (parte de CU-02) e importa, seudonimiza y audita
archivos **sintéticos** (CU-01 con datos sintéticos). Importar datos reales sigue
bloqueado: requiere DP-02 y DP-14, y el servicio rechaza todo archivo cuyas filas
no estén marcadas como sintéticas. El objetivo (CU-03) llega en H2.4.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    ColumnaAuditada,
    InformeAuditoriaResumen,
    RasgoResumen,
    ResultadoDiccionario,
    ResultadoImportacion,
    SolicitudImportarDataset,
    SolicitudValidarDiccionario,
)
from suficiencia.domain.datos.auditoria import InformeAuditoria, auditar
from suficiencia.domain.datos.diccionario import VALOR_ORIGEN_SINTETICO, Diccionario
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.huella import Huella
from suficiencia.domain.puertos import Seudonimizador

CARPETA_DATOS = Path("data")


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
        DefinicionCasoDeUso("CU-03", "Construir el objetivo y los estados de etiqueta", "H2.4"),
    )

    def __init__(
        self,
        raiz: Path,
        cargar_diccionario: Callable[[Path], Diccionario],
        leer_tabla: Callable[[Path, str], tuple[pd.DataFrame, Huella]],
        seudonimizador: Callable[[bool], Seudonimizador],
        huella_de_tabla: Callable[[pd.DataFrame], Huella],
        escribir_tabla: Callable[[pd.DataFrame, Path], Huella],
    ) -> None:
        self._raiz = raiz
        self._cargar_diccionario = cargar_diccionario
        self._leer_tabla = leer_tabla
        self._seudonimizador = seudonimizador
        self._huella_de_tabla = huella_de_tabla
        self._escribir_tabla = escribir_tabla

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
        tabla, huella_fuente = self._leer_tabla(solicitud.archivo, solicitud.separador)
        _exigir_sintetico(tabla, diccionario, solicitud.archivo)

        # La seudonimización ocurre antes de cualquier otra transformación (M1).
        seudonimizada = self._seudonimizador(solicitud.clave_efimera).seudonimizar(
            tabla, diccionario.identificadores
        )
        del tabla
        resultado = auditar(seudonimizada, diccionario)

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
