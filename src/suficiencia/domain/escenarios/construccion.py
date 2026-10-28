"""Construcción de la matriz de escenarios y verificador de fuga temporal (M2).

El constructor y el verificador son independientes a propósito: el verificador no
confía en el constructor y revisa cada escenario contra las ventanas mínimas de
las variables (RF-M2-04). Así, un error futuro en el constructor, o un escenario
modificado a mano, no puede introducir una fuga sin que se detecte.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from suficiencia.domain.errores import ErrorSuficiencia
from suficiencia.domain.escenarios.modelo import (
    Bloque,
    CatalogoVentanas,
    Escenario,
    Variable,
    generar_conjuntos,
    orden_ventana,
    validar_variables,
)


def construir_escenarios(
    catalogo: CatalogoVentanas, variables: Iterable[Variable]
) -> tuple[Escenario, ...]:
    """Construye los 32 escenarios: 4 ventanas × 8 conjuntos (RF-M2-03).

    Cada escenario recibe las variables de sus bloques disponibles en su ventana.
    Un escenario con algún bloque sin variables queda marcado como no factible; no
    se imputa el bloque ausente (RM-09).
    """
    lista = validar_variables(variables)
    escenarios = []
    for ventana in catalogo.ventanas:
        for conjunto in generar_conjuntos():
            disponibles = [
                v for v in lista if v.bloque in conjunto.bloques and v.disponible_en(ventana)
            ]
            con_variables = {v.bloque for v in disponibles}
            escenarios.append(
                Escenario(
                    ventana=ventana,
                    conjunto=conjunto,
                    variables=tuple(sorted(v.nombre for v in disponibles)),
                    bloques_sin_variables=tuple(
                        b for b in Bloque if b in conjunto.bloques and b not in con_variables
                    ),
                )
            )
    return tuple(escenarios)


@dataclass(frozen=True)
class Fuga:
    """Variable presente en un escenario anterior a su ventana mínima."""

    escenario: str
    variable: str
    ventana_minima: str


class FugaTemporal(ErrorSuficiencia):
    """Algún escenario usa información que no estaba disponible en su ventana."""

    def __init__(self, fugas: tuple[Fuga, ...]) -> None:
        self.fugas = fugas
        detalle = "; ".join(
            f"{f.variable} (disponible desde {f.ventana_minima}) en {f.escenario}" for f in fugas
        )
        super().__init__(
            f"Fuga temporal en {len(fugas)} caso(s): {detalle}.",
            "No ejecute estos escenarios. Revise la ventana mínima de las variables "
            "y el constructor de escenarios.",
        )


def detectar_fugas(
    escenarios: Iterable[Escenario], variables: Iterable[Variable]
) -> tuple[Fuga, ...]:
    """Devuelve las fugas encontradas, sin lanzar error.

    Una variable que no figura entre las variables conocidas también cuenta como
    fuga: no hay forma de comprobar cuándo está disponible.
    """
    minima = {v.nombre: v.ventana_minima for v in validar_variables(variables)}
    fugas = []
    for escenario in escenarios:
        for nombre in escenario.variables:
            ventana_minima = minima.get(nombre)
            if ventana_minima is None or orden_ventana(ventana_minima) > escenario.ventana.orden:
                fugas.append(Fuga(escenario.codigo, nombre, ventana_minima or "desconocida"))
    return tuple(fugas)


def verificar_sin_fuga(escenarios: Iterable[Escenario], variables: Iterable[Variable]) -> None:
    """Lanza :class:`FugaTemporal` si algún escenario tiene una fuga (RF-M2-04)."""
    fugas = detectar_fugas(escenarios, variables)
    if fugas:
        raise FugaTemporal(fugas)
