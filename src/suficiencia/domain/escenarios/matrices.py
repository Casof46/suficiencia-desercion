"""Matrices de predictores por escenario (M2 → M3; F3.1).

Para un escenario (ventana × conjunto), construye una fila por unidad de la
población de esa ventana con los valores de las variables del escenario **tal
como se conocían al cierre del periodo índice** de la ventana, y su etiqueta.

Cómo se lee cada variable en el corte depende de DP-03 y DP-15 (qué se registra y
cuándo). Por eso es un dato obligatorio por variable, sin valor por omisión:

- ``primer_registro``: el valor del primer registro de la unidad. Solo se admite
  para variables disponibles desde T0 (atributos de la admisión, que el historial
  repite en cada ciclo).
- ``ultimo_ciclo``: el valor del registro del periodo índice. Si la unidad no
  tiene registro en ese periodo, queda faltante; nunca se toma de un periodo
  posterior.

Protecciones contra la fuga temporal:

- Antes de leer nada se descartan los registros de periodos posteriores al
  periodo índice.
- Una variable cuya ventana mínima es posterior a la ventana del escenario se
  rechaza (complementa el verificador de H2.2).
- Solo entran unidades etiquetables de la población: los no etiquetables nunca
  llegan al entrenamiento (PU-12).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd

from suficiencia.domain.datos.objetivo import COLUMNA_ESTADO, ColumnasHistorial, EstadoEtiqueta
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.construccion import Fuga, FugaTemporal
from suficiencia.domain.escenarios.modelo import Escenario, Variable, orden_ventana

COLUMNA_OBJETIVO = "objetivo"


class Agregacion(Enum):
    PRIMER_REGISTRO = "primer_registro"
    ULTIMO_CICLO = "ultimo_ciclo"


@dataclass(frozen=True)
class DefinicionMatrices:
    """Cómo se lee cada variable en el corte de cada ventana (DP-03, DP-15)."""

    agregacion: Mapping[str, Agregacion]

    def de(self, variable: str) -> Agregacion:
        if variable not in self.agregacion:
            raise DecisionPendiente(
                "DP-03", f"cómo se lee la variable '{variable}' en el corte de cada ventana"
            )
        return self.agregacion[variable]


def definicion_matrices_desde_datos(datos: Any) -> DefinicionMatrices:
    """Lee la sección ``matrices`` de la configuración de experimentos.

    Raises:
        DecisionPendiente: si la sección o una variable vale ``null`` (DP-03).
        ConfiguracionInvalida: si la estructura no es válida.
    """
    if datos is None:
        raise DecisionPendiente("DP-03", "la sección 'matrices' de la configuración")
    if not isinstance(datos, Mapping) or set(datos) != {"agregacion"}:
        raise ConfiguracionInvalida(
            "La sección 'matrices' debe tener exactamente el campo 'agregacion'.",
            "Asocie cada variable con primer_registro o ultimo_ciclo.",
        )
    agregacion = datos["agregacion"]
    if not isinstance(agregacion, Mapping) or not agregacion:
        raise ConfiguracionInvalida(
            "'matrices.agregacion' debe asociar cada variable con su lectura.",
            "Por ejemplo, puntaje_admision: primer_registro.",
        )
    leidas: dict[str, Agregacion] = {}
    for variable, valor in agregacion.items():
        if valor is None:
            raise DecisionPendiente("DP-03", f"cómo se lee la variable '{variable}'")
        try:
            leidas[str(variable)] = Agregacion(valor)
        except ValueError:
            opciones = ", ".join(a.value for a in Agregacion)
            raise ConfiguracionInvalida(
                f"'{valor}' no es una lectura válida para '{variable}'.",
                f"Use una de: {opciones}.",
            ) from None
    return DefinicionMatrices(leidas)


@dataclass(frozen=True)
class MatrizEscenario:
    """Predictores, etiqueta y cohorte de cada unidad de un escenario."""

    escenario: str
    ventana: str
    conjunto: str
    predictores: pd.DataFrame
    objetivo: pd.Series
    cohorte: pd.Series

    @property
    def filas(self) -> int:
        return len(self.predictores)


def _verificar_variables(escenario: Escenario, variables: Mapping[str, Variable]) -> None:
    fugas = [
        Fuga(escenario.codigo, nombre, variables[nombre].ventana_minima)
        for nombre in escenario.variables
        if orden_ventana(variables[nombre].ventana_minima) > orden_ventana(escenario.ventana.codigo)
    ]
    if fugas:
        raise FugaTemporal(tuple(fugas))


def construir_matriz(
    historial: pd.DataFrame,
    columnas: ColumnasHistorial,
    escenario: Escenario,
    variables: Sequence[Variable],
    miembros: pd.DataFrame,
    periodo_indice: int,
    definicion: DefinicionMatrices,
) -> MatrizEscenario:
    """Construye la matriz de un escenario factible para las unidades de ``miembros``.

    ``miembros`` son las unidades de la población de la ventana (por ejemplo, D1),
    ya restringidas a las cohortes que correspondan (desarrollo). Las filas salen
    en el orden de ``miembros``.

    Raises:
        ConfiguracionInvalida: si el escenario no es factible o una lectura no se admite.
        FugaTemporal: si una variable no está disponible en la ventana.
        DecisionPendiente: si falta la lectura de una variable (DP-03).
    """
    if not escenario.factible:
        raise ConfiguracionInvalida(
            f"El escenario {escenario.codigo} no es factible: no tiene variables en "
            f"{', '.join(b.value for b in escenario.bloques_sin_variables)}.",
            "Los escenarios no factibles no se entrenan (RF-M2-03).",
        )
    por_nombre = {v.nombre: v for v in variables}
    _verificar_variables(escenario, por_nombre)
    clave = list(columnas.unidad)
    etiquetables = miembros[miembros[COLUMNA_ESTADO] != EstadoEtiqueta.NO_ETIQUETABLE.value]
    unidades = etiquetables[clave].reset_index(drop=True)

    # Corte: nada posterior al periodo índice entra en la matriz.
    hasta_corte = historial[historial[columnas.periodo] <= periodo_indice]
    primeros = historial.sort_values(columnas.periodo).drop_duplicates(clave, keep="first")
    del_periodo = hasta_corte[hasta_corte[columnas.periodo] == periodo_indice]

    tabla = unidades.copy()
    for nombre in escenario.variables:
        lectura = definicion.de(nombre)
        if lectura is Agregacion.PRIMER_REGISTRO:
            if por_nombre[nombre].ventana_minima != "T0":
                raise ConfiguracionInvalida(
                    f"La variable '{nombre}' no está disponible desde T0 y no puede leerse "
                    "con primer_registro.",
                    "Use ultimo_ciclo para variables que se registran en cada ciclo.",
                )
            fuente = primeros
        else:
            if periodo_indice < 1:
                raise ConfiguracionInvalida(
                    f"La variable '{nombre}' se lee con ultimo_ciclo, pero la ventana "
                    f"{escenario.ventana.codigo} no tiene ningún ciclo cerrado.",
                    "Revise la ventana mínima de la variable o su lectura.",
                )
            fuente = del_periodo
        tabla = tabla.merge(fuente[[*clave, nombre]], on=clave, how="left", validate="1:1")

    objetivo = (
        etiquetables[COLUMNA_ESTADO].reset_index(drop=True) == EstadoEtiqueta.POSITIVO.value
    ).astype("int64")
    return MatrizEscenario(
        escenario=escenario.codigo,
        ventana=escenario.ventana.codigo,
        conjunto=escenario.conjunto.codigo,
        predictores=tabla.set_index(clave)[list(escenario.variables)],
        objetivo=objetivo.set_axis(tabla.set_index(clave).index).rename(COLUMNA_OBJETIVO),
        cohorte=etiquetables[columnas.cohorte]
        .reset_index(drop=True)
        .set_axis(tabla.set_index(clave).index),
    )
