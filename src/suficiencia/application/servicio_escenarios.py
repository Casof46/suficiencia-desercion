"""Servicio de escenarios, poblaciones, particiones y exploración (M2): CU-04 y CU-11.

Desde H2.2 construye y verifica la matriz de 32 escenarios (parte de CU-04). Desde
H2.5 construye, con datos sintéticos y configuración ficticia, las poblaciones D1,
D2 y D3 por ventana, la partición cronológica por cohortes y el sello de la prueba,
y describe solo la partición de desarrollo (CU-11; RF-M2-09, RF-M2-12). De la
prueba solo se informa el tamaño.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    DescripcionPoblacionResumen,
    EscenarioResumen,
    NoEtiquetablesCohorteResumen,
    ResultadoEscenarios,
    ResultadoPoblaciones,
    SeguimientoCohorteResumen,
    SolicitudConstruirPoblaciones,
    SolicitudGenerarEscenarios,
    SolicitudLeerPrueba,
    VentanaResumen,
)
from suficiencia.application.servicio_datos import HistorialPreparado
from suficiencia.domain.datos.objetivo import resumir_no_etiquetables
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.construccion import construir_escenarios, verificar_sin_fuga
from suficiencia.domain.escenarios.particion import (
    Division,
    SelloPrueba,
    dividir,
    sellar,
)
from suficiencia.domain.escenarios.poblaciones import (
    ConfiguracionPoblaciones,
    construir_poblaciones,
    contar_exclusiones,
    describir,
    seguimiento_por_cohorte,
)
from suficiencia.domain.puertos import FuenteCatalogoVentanas, FuenteVariables
from suficiencia.domain.trazabilidad.registros import RegistroAcceso

ARCHIVO_ESCENARIOS = Path("config") / "escenarios.yaml"
ARCHIVO_VARIABLES = Path("config") / "diccionario" / "variables.yaml"
ARCHIVO_POBLACIONES = Path("config") / "poblaciones.yaml"
CARPETA_PARTICIONES = "particiones"
OPERACION_CONSULTA = "consulta_desde_la_linea_de_comandos"


def _particion_de(cohorte: str, configuracion: ConfiguracionPoblaciones) -> str:
    particion = configuracion.particion
    for nombre, cohortes in (
        ("desarrollo", particion.desarrollo),
        ("prueba", particion.prueba),
        ("piloto", particion.piloto),
        ("excluidas", particion.excluidas),
    ):
        if cohorte in cohortes:
            return nombre
    return "sin asignar"


class ServicioEscenarios(ServicioCasosDeUso):
    """Escenarios, poblaciones, particiones y análisis exploratorio (M2)."""

    NOMBRE: ClassVar[str] = "escenarios"
    DESCRIPCION: ClassVar[str] = (
        "Escenarios, poblaciones, particiones y análisis exploratorio (M2)."
    )
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-04",
            "Generar escenarios, poblaciones y particiones",
            "con la configuración real, cuando se resuelvan DP-01d, DP-04, DP-05 y DP-17",
            avance="los 32 escenarios y el verificador anti-fuga (H2.2): `suficiencia "
            "escenarios`; poblaciones, partición y sello con datos sintéticos (H2.5): "
            "`suficiencia poblaciones`",
        ),
        DefinicionCasoDeUso(
            "CU-11",
            "Ejecutar el análisis exploratorio de viabilidad",
            "con datos reales, cuando se resuelvan DP-02 y DP-14",
            avance="seguimiento por cohorte (parte A) y descriptivos de desarrollo (parte B) "
            "con datos sintéticos (H2.5): `suficiencia poblaciones construir`",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        fuente_catalogo: Callable[[Path], FuenteCatalogoVentanas],
        fuente_variables: Callable[[Path, bool], FuenteVariables],
        fuente_diccionario: Callable[[Path], FuenteVariables],
        preparar_historial: Callable[[Path, Path, Path | None, bool, str], HistorialPreparado],
        cargar_poblaciones: Callable[[Path], ConfiguracionPoblaciones],
        guardar_division: Callable[[Division, list[str], Path, dict[str, Any]], dict[str, str]],
        cargador_de_prueba: Callable[[Path], Callable[[], pd.DataFrame]],
        registrar_acceso: Callable[[RegistroAcceso], object],
        carpeta_trabajo: Callable[[], Path],
    ) -> None:
        self._raiz = raiz
        self._fuente_catalogo = fuente_catalogo
        self._fuente_variables = fuente_variables
        self._fuente_diccionario = fuente_diccionario
        self._preparar_historial = preparar_historial
        self._cargar_poblaciones = cargar_poblaciones
        self._guardar_division = guardar_division
        self._cargador_de_prueba = cargador_de_prueba
        self._registrar_acceso = registrar_acceso
        self._carpeta_trabajo = carpeta_trabajo

    def generar_escenarios(self, solicitud: SolicitudGenerarEscenarios) -> ResultadoEscenarios:
        """Construye los 32 escenarios y comprueba que ninguno tenga fuga temporal.

        Raises:
            DecisionPendiente: si faltan las fechas índice (DP-01d) o las variables (DP-03).
            ConfiguracionInvalida: si algún archivo no es válido.
            FugaTemporal: si algún escenario usa una variable antes de su ventana.
        """
        catalogo = self._fuente_catalogo(
            solicitud.configuracion or self._raiz / ARCHIVO_ESCENARIOS
        ).cargar()
        if solicitud.variables is not None and solicitud.diccionario is not None:
            raise ConfiguracionInvalida(
                "Se indicaron a la vez un archivo de variables y un diccionario.",
                "Use solo uno de los dos.",
            )
        if solicitud.diccionario is not None:
            variables = self._fuente_diccionario(solicitud.diccionario).cargar()
        else:
            por_omision = solicitud.variables is None
            variables = self._fuente_variables(
                solicitud.variables or self._raiz / ARCHIVO_VARIABLES, por_omision
            ).cargar()

        escenarios = construir_escenarios(catalogo.catalogo, variables.variables)
        verificar_sin_fuga(escenarios, variables.variables)

        return ResultadoEscenarios(
            ficticio=catalogo.ficticio or variables.ficticio,
            ventanas=tuple(
                VentanaResumen(codigo=v.codigo, fecha_indice=v.fecha_indice)
                for v in catalogo.catalogo.ventanas
            ),
            escenarios=tuple(
                EscenarioResumen(
                    codigo=e.codigo,
                    ventana=e.ventana.codigo,
                    conjunto=e.conjunto.codigo,
                    factible=e.factible,
                    variables=e.variables,
                    bloques_sin_variables=tuple(b.value for b in e.bloques_sin_variables),
                )
                for e in escenarios
            ),
            variables_evaluadas=len(variables.variables),
            sin_fuga=True,
        )

    def _ruta(self, archivo: Path | None, por_omision: Path) -> Path:
        if archivo is None:
            return self._raiz / por_omision
        return archivo if archivo.is_absolute() else self._raiz / archivo

    def construir_poblaciones(
        self, solicitud: SolicitudConstruirPoblaciones
    ) -> ResultadoPoblaciones:
        """Etiqueta, construye D1 a D3, particiona por cohortes, sella la prueba y la guarda.

        Raises:
            DecisionPendiente: si falta la configuración de poblaciones (DP-04 y
                relacionadas), la definición del objetivo (DP-01), la marca sintética
                (DP-02) o la clave de seudonimización (DP-14).
            AuditoriaConErrores: si la auditoría no es apta (PU-17).
        """
        configuracion = self._cargar_poblaciones(
            self._ruta(solicitud.configuracion, ARCHIVO_POBLACIONES)
        )
        historial = self._preparar_historial(
            solicitud.archivo,
            solicitud.diccionario,
            solicitud.definicion,
            solicitud.clave_efimera,
            solicitud.separador,
        )
        columnas, definicion = historial.columnas, historial.definicion
        seguimiento = seguimiento_por_cohorte(
            historial.tabla, columnas, definicion, configuracion.indices
        )
        poblaciones = construir_poblaciones(
            historial.tabla, columnas, definicion, configuracion.indices
        )
        division = dividir(poblaciones.etiquetas_base, columnas.cohorte, configuracion.particion)

        marca = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%f")
        carpeta = self._carpeta_trabajo() / CARPETA_PARTICIONES / f"particion-{marca}"
        particion_def = configuracion.particion
        manifiesto: dict[str, Any] = {
            "configuracion": configuracion.nombre,
            "ficticia": configuracion.ficticio,
            "definicion_objetivo": definicion.nombre,
            "huella_dataset": historial.huella_dataset.valor,
            "cohortes": {
                "desarrollo": sorted(particion_def.desarrollo),
                "prueba": sorted(particion_def.prueba),
                "piloto": sorted(particion_def.piloto),
                "excluidas": sorted(particion_def.excluidas),
            },
            "tamanos": {
                "desarrollo": len(division.desarrollo),
                "prueba": len(division.prueba),
                "piloto": len(division.piloto),
                "excluidas": len(division.excluidas),
            },
            "plan_contingencia": particion_def.plan_contingencia,
        }
        huellas = self._guardar_division(
            division, [*columnas.unidad, columnas.cohorte], carpeta, manifiesto
        )
        particion = sellar(
            division,
            particion_def,
            SelloPrueba(self._cargador_de_prueba(carpeta), self._registrar_acceso),
        )

        desarrollo = particion_def.desarrollo
        no_etiquetables = resumir_no_etiquetables(
            particion.desarrollo, columnas.cohorte, definicion.nivel_sensibilidad
        )
        return ResultadoPoblaciones(
            archivo=str(solicitud.archivo),
            sintetico=historial.sintetico,
            definicion_ficticia=definicion.ficticio,
            configuracion_ficticia=configuracion.ficticio,
            huella_dataset=historial.huella_dataset.valor,
            diseno_principal=configuracion.diseno_principal.value,
            complementarios=tuple(sorted(d.value for d in configuracion.complementarios)),
            periodos_indice=dict(configuracion.indices.periodos),
            seguimiento=tuple(
                SeguimientoCohorteResumen(
                    cohorte=s.cohorte,
                    particion=_particion_de(s.cohorte, configuracion),
                    unidades=s.unidades,
                    ultimo_periodo_observable=s.ultimo_periodo_observable,
                    periodo_necesario=s.periodo_necesario,
                    completo=s.completo,
                )
                for s in seguimiento
            ),
            unidades_desarrollo=len(particion.desarrollo),
            tamano_prueba=particion.tamano_prueba,
            unidades_piloto=particion.piloto,
            unidades_excluidas=particion.excluidas,
            descripciones_desarrollo=tuple(
                DescripcionPoblacionResumen(
                    diseno=d.diseno.value,
                    ventana=d.ventana,
                    tamano=d.tamano,
                    eventos=d.eventos,
                    prevalencia=d.prevalencia,
                    eventos_detectables=d.eventos_detectables,
                )
                for d in describir(poblaciones, columnas.cohorte, desarrollo)
            ),
            exclusiones_desarrollo=contar_exclusiones(poblaciones, columnas.cohorte, desarrollo),
            no_etiquetables_desarrollo=tuple(
                NoEtiquetablesCohorteResumen(
                    cohorte=n.cohorte,
                    unidades=n.unidades,
                    no_etiquetables=n.no_etiquetables,
                    por_motivo=dict(n.por_motivo),
                    proporcion=n.proporcion,
                    requiere_analisis_sensibilidad=n.requiere_analisis_sensibilidad,
                )
                for n in no_etiquetables
            ),
            nivel_sensibilidad=definicion.nivel_sensibilidad,
            carpeta_particion=str(carpeta),
            huellas=huellas,
        )

    def leer_prueba(self, solicitud: SolicitudLeerPrueba) -> None:
        """Intenta leer la prueba de una partición guardada.

        Ninguna operación de la línea de comandos es la evaluación final, así que el
        sello siempre la rechaza; el intento queda en el registro de accesos (PI-02).

        Raises:
            AccesoPruebaDenegado: siempre, después de registrar el intento.
        """
        carpeta = solicitud.particion
        if not carpeta.is_absolute():
            carpeta = self._raiz / carpeta
        sello = SelloPrueba(self._cargador_de_prueba(carpeta), self._registrar_acceso)
        sello.leer(OPERACION_CONSULTA, solicitud.motivo)
