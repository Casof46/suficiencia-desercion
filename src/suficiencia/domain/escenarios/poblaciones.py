"""Poblaciones por ventana según los diseños D1, D2 y D3 (M2; RF-M2-05, RF-M2-12).

Las cuatro ventanas no observan la misma población (sección 4, M2):

- **D1, población elegible por ventana:** en Tk entra quien no presentó el evento
  antes de la fecha índice de Tk y tiene una etiqueta observable.
- **D2, población común:** solo quienes están en D1 en la ventana más tardía, con
  la misma etiqueta en todas las ventanas.
- **D3, cobertura sobre la cohorte de admisión:** toda la cohorte etiquetable; en
  Tk, quien desertó antes de la fecha índice cuenta como evento no detectable a
  tiempo.

El programa construye los tres diseños sin elegir ninguno: el diseño principal es
DP-04 y los complementarios, DP-17. La fecha índice de cada ventana se expresa
aquí como el periodo ordinal al final del cual se consolida su información
(DP-01d, en el formato del historial; D-69 de H2.4).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum

import pandas as pd

from suficiencia.domain.datos.objetivo import (
    COLUMNA_ESTADO,
    ColumnasHistorial,
    DefinicionObjetivo,
    EstadoEtiqueta,
    Etiqueta,
    InicioHorizonte,
    etiquetar_unidad,
    fila_de_etiqueta,
    periodo_necesario,
    preparar_unidades,
    tabla_de_etiquetas,
)
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.modelo import CODIGOS_VENTANA
from suficiencia.domain.escenarios.particion import DefinicionParticion

COLUMNA_VENTANA = "ventana"
COLUMNA_DETECTABLE = "detectable_a_tiempo"
EXCLUSION_EVENTO_PREVIO = "evento_antes_de_la_fecha_indice"


class Diseno(Enum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"


@dataclass(frozen=True)
class PeriodosIndice:
    """Periodo ordinal en el que se consolida la información de cada ventana (DP-01d)."""

    periodos: Mapping[str, int]

    def __post_init__(self) -> None:
        if tuple(self.periodos) != CODIGOS_VENTANA:
            raise ConfiguracionInvalida(
                "Los periodos índice deben declarar T0, T1, T2 y T3, en ese orden.",
                "Corrija 'periodo_indice' en la configuración de poblaciones.",
            )
        anterior = -1
        for ventana, periodo in self.periodos.items():
            if isinstance(periodo, bool) or not isinstance(periodo, int) or periodo < 0:
                raise ConfiguracionInvalida(
                    f"El periodo índice de {ventana} debe ser un entero mayor o igual a 0.",
                    "Use 0 para el momento de la admisión, 1 para el final del primer periodo...",
                )
            if periodo <= anterior:
                raise ConfiguracionInvalida(
                    "Los periodos índice deben crecer de T0 a T3.",
                    "Cada ventana se consolida después de la anterior.",
                )
            anterior = periodo

    @property
    def ultima_ventana(self) -> str:
        return CODIGOS_VENTANA[-1]


@dataclass(frozen=True)
class Poblaciones:
    """Miembros de cada diseño en cada ventana y exclusiones de D1 por motivo."""

    miembros: Mapping[tuple[Diseno, str], pd.DataFrame]
    exclusiones: Mapping[str, pd.DataFrame]
    """Por ventana: unidades fuera de D1, con su motivo y cohorte."""
    etiquetas_base: pd.DataFrame
    """Etiqueta de cada unidad con el horizonte desde el ingreso (o la de la última
    ventana si el horizonte es relativo), para la partición y los reportes."""
    fuera_de_poblacion: int
    fuera_de_cohortes: int


def _etiqueta_en_ventana(
    unidad_estados: Mapping[int, str],
    limite: int,
    definicion: DefinicionObjetivo,
    periodo_indice: int,
    base: Etiqueta | None,
) -> tuple[bool, Etiqueta]:
    """Devuelve si hubo evento antes de la fecha índice y la etiqueta en la ventana."""
    if definicion.horizonte_desde is InicioHorizonte.INGRESO:
        assert base is not None
        previo = (
            base.estado is EstadoEtiqueta.POSITIVO
            and base.periodo_evento is not None
            and base.periodo_evento <= periodo_indice
        )
        return previo, base
    previo = False
    if periodo_indice > 0:
        hasta_indice = replace(
            definicion, horizonte_periodos=periodo_indice, horizonte_desde=InicioHorizonte.INGRESO
        )
        previo = (
            etiquetar_unidad(unidad_estados, limite, hasta_indice).estado is EstadoEtiqueta.POSITIVO
        )
    return previo, etiquetar_unidad(unidad_estados, limite, definicion, periodo_indice)


def construir_poblaciones(
    historial: pd.DataFrame,
    columnas: ColumnasHistorial,
    definicion: DefinicionObjetivo,
    indices: PeriodosIndice,
) -> Poblaciones:
    """Construye D1, D2 y D3 en cada ventana (RF-M2-05; RF-M2-12 sin esperar DP-17).

    D3 solo se construye con el horizonte desde el ingreso: cuenta la cohorte desde
    la admisión y no se define con un horizonte relativo a la fecha índice.
    """
    preparadas = preparar_unidades(historial, columnas, definicion)
    ultima = indices.ultima_ventana
    desde_ingreso = definicion.horizonte_desde is InicioHorizonte.INGRESO

    filas_d1: dict[str, list[dict[str, object]]] = {v: [] for v in CODIGOS_VENTANA}
    filas_d3: dict[str, list[dict[str, object]]] = {v: [] for v in CODIGOS_VENTANA}
    excluidas: dict[str, list[dict[str, object]]] = {v: [] for v in CODIGOS_VENTANA}
    filas_base: list[dict[str, object]] = []
    for unidad in preparadas.unidades:
        base = (
            etiquetar_unidad(unidad.estados, unidad.limite_observable, definicion)
            if desde_ingreso
            else None
        )
        for ventana, periodo in indices.periodos.items():
            previo, etiqueta = _etiqueta_en_ventana(
                unidad.estados, unidad.limite_observable, definicion, periodo, base
            )
            fila = fila_de_etiqueta(unidad, columnas, etiqueta)
            if previo:
                motivo = EXCLUSION_EVENTO_PREVIO
            elif etiqueta.estado is EstadoEtiqueta.NO_ETIQUETABLE:
                assert etiqueta.motivo is not None
                motivo = etiqueta.motivo.value
            else:
                motivo = ""
            if motivo:
                excluidas[ventana].append(
                    {
                        **dict(zip(columnas.unidad, unidad.clave, strict=True)),
                        columnas.cohorte: unidad.cohorte,
                        "motivo_exclusion": motivo,
                    }
                )
            else:
                filas_d1[ventana].append(fila)
            if base is not None and base.estado is not EstadoEtiqueta.NO_ETIQUETABLE:
                filas_d3[ventana].append({**fila, COLUMNA_DETECTABLE: not previo})
            if ventana == ultima and base is None:
                filas_base.append(fila)
        if base is not None:
            filas_base.append(fila_de_etiqueta(unidad, columnas, base))

    miembros: dict[tuple[Diseno, str], pd.DataFrame] = {}
    clave = list(columnas.unidad)
    comun = tabla_de_etiquetas(filas_d1[ultima], columnas)
    for ventana in CODIGOS_VENTANA:
        d1 = tabla_de_etiquetas(filas_d1[ventana], columnas)
        miembros[(Diseno.D1, ventana)] = d1.sort_values(clave, ignore_index=True)
        miembros[(Diseno.D2, ventana)] = comun.sort_values(clave, ignore_index=True)
        if desde_ingreso:
            # D3 cuenta la cohorte desde la admisión: con horizonte relativo no se define.
            d3 = tabla_de_etiquetas(filas_d3[ventana], columnas)
            d3[COLUMNA_DETECTABLE] = [bool(f[COLUMNA_DETECTABLE]) for f in filas_d3[ventana]]
            miembros[(Diseno.D3, ventana)] = d3.sort_values(clave, ignore_index=True)
    exclusiones = {
        v: pd.DataFrame(
            excluidas[v], columns=[*columnas.unidad, columnas.cohorte, "motivo_exclusion"]
        )
        for v in CODIGOS_VENTANA
    }
    return Poblaciones(
        miembros=miembros,
        exclusiones=exclusiones,
        etiquetas_base=tabla_de_etiquetas(filas_base, columnas),
        fuera_de_poblacion=preparadas.fuera_de_poblacion,
        fuera_de_cohortes=preparadas.fuera_de_cohortes,
    )


@dataclass(frozen=True)
class DescripcionPoblacion:
    """Tamaño, eventos y prevalencia de un diseño en una ventana (RF-M2-09, RF-M2-12)."""

    diseno: Diseno
    ventana: str
    tamano: int
    eventos: int
    prevalencia: float | None
    eventos_detectables: int | None
    """Solo D3: eventos posteriores a la fecha índice."""


def describir(
    poblaciones: Poblaciones, columna_cohorte: str, cohortes: frozenset[str]
) -> tuple[DescripcionPoblacion, ...]:
    """Describe cada diseño y ventana usando SOLO las cohortes indicadas.

    Muestra eventos y prevalencia: según RF-M2-09 y PI-02, solo se aplica a la
    partición de desarrollo.
    """
    descripciones: list[DescripcionPoblacion] = []
    for (diseno, ventana), miembros in sorted(
        poblaciones.miembros.items(), key=lambda par: (par[0][0].value, par[0][1])
    ):
        filas = miembros[miembros[columna_cohorte].astype(str).isin(cohortes)]
        eventos = int((filas[COLUMNA_ESTADO] == EstadoEtiqueta.POSITIVO.value).sum())
        detectables = None
        if diseno is Diseno.D3:
            positivos = filas[filas[COLUMNA_ESTADO] == EstadoEtiqueta.POSITIVO.value]
            detectables = int(positivos[COLUMNA_DETECTABLE].astype(bool).sum())
        descripciones.append(
            DescripcionPoblacion(
                diseno=diseno,
                ventana=ventana,
                tamano=len(filas),
                eventos=eventos,
                prevalencia=eventos / len(filas) if len(filas) else None,
                eventos_detectables=detectables,
            )
        )
    return tuple(descripciones)


def contar_exclusiones(
    poblaciones: Poblaciones, columna_cohorte: str, cohortes: frozenset[str]
) -> dict[str, dict[str, int]]:
    """Unidades fuera de D1 por ventana y motivo, solo en las cohortes indicadas."""
    resultado: dict[str, dict[str, int]] = {}
    for ventana, tabla in poblaciones.exclusiones.items():
        filas = tabla[tabla[columna_cohorte].astype(str).isin(cohortes)]
        resultado[ventana] = dict(sorted(Counter(filas["motivo_exclusion"]).items()))
    return resultado


@dataclass(frozen=True)
class ConfiguracionPoblaciones:
    """Ventanas en periodos (DP-01d), diseños (DP-04, DP-17) y partición (DP-05, DP-08h)."""

    nombre: str
    ficticio: bool
    indices: PeriodosIndice
    diseno_principal: Diseno
    complementarios: frozenset[Diseno]
    particion: DefinicionParticion

    def __post_init__(self) -> None:
        if self.diseno_principal in self.complementarios:
            raise ConfiguracionInvalida(
                f"{self.diseno_principal.value} es a la vez el diseño principal y un análisis "
                "complementario.",
                "Quítelo de 'analisis_complementarios' (DP-17).",
            )


@dataclass(frozen=True)
class SeguimientoCohorte:
    """CU-11 parte A: tamaño y completitud del seguimiento, sin usar el resultado."""

    cohorte: str
    unidades: int
    ultimo_periodo_observable: int
    periodo_necesario: int

    @property
    def completo(self) -> bool:
        return self.ultimo_periodo_observable >= self.periodo_necesario


def seguimiento_por_cohorte(
    historial: pd.DataFrame,
    columnas: ColumnasHistorial,
    definicion: DefinicionObjetivo,
    indices: PeriodosIndice,
) -> tuple[SeguimientoCohorte, ...]:
    """Unidades y completitud del seguimiento de cada cohorte (todas las cohortes).

    No cuenta eventos ni estados de etiqueta: puede aplicarse a todas las cohortes
    antes de la partición (CU-11 parte A).
    """
    preparadas = preparar_unidades(historial, columnas, definicion)
    desde = 0
    if definicion.horizonte_desde is InicioHorizonte.FECHA_INDICE:
        desde = indices.periodos[indices.ultima_ventana]
    necesario = periodo_necesario(definicion, desde)
    conteo = Counter(u.cohorte for u in preparadas.unidades)
    limites = {u.cohorte: u.limite_observable for u in preparadas.unidades}
    return tuple(
        SeguimientoCohorte(cohorte, conteo[cohorte], limites[cohorte], necesario)
        for cohorte in sorted(conteo)
    )
