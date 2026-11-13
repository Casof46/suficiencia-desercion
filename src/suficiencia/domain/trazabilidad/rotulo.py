"""Rótulo de los resultados obtenidos con datos sintéticos (RNF-19, PI-16; F3.7).

Todo resultado obtenido con datos sintéticos lleva el rótulo en los registros, los
gráficos y los reportes, y no puede exportarse sin él. Mientras el importador solo
admita datos sintéticos (DP-02, DP-14), un registro que no declare su origen se trata
como sintético: el rótulo sobra antes que faltar.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
from typing import Any

from suficiencia.domain.errores import ErrorSuficiencia

CAMPO_ORIGEN = "origen_datos"
"""Campo del registro y columna de cada tabla exportada con el origen de los datos."""

ROTULO_SINTETICO = "SINTÉTICO"
LEYENDA_SINTETICA = (
    "DATOS SINTÉTICOS Y CONFIGURACIONES FICTICIAS: no es evidencia sobre estudiantes "
    "reales ni sobre la eficacia del método."
)


class OrigenDatos(Enum):
    SINTETICO = "sintetico"
    REAL = "real"


class RotuloFaltante(ErrorSuficiencia):
    """Una exportación de resultados sintéticos no lleva el rótulo (RNF-19)."""

    def __init__(self, donde: str) -> None:
        self.donde = donde
        super().__init__(
            f"La exportación no lleva el rótulo de datos sintéticos en {donde}.",
            "Todo resultado obtenido con datos sintéticos debe exportarse rotulado "
            "(RNF-19); no se exporta sin el rótulo.",
        )


def origen_de_registro(contenido: Mapping[str, Any]) -> OrigenDatos:
    """Origen declarado en un registro; sin declaración, sintético (ver el docstring)."""
    valor = contenido.get(CAMPO_ORIGEN)
    if valor == OrigenDatos.REAL.value:
        return OrigenDatos.REAL
    return OrigenDatos.SINTETICO


def origen_de_historial(sintetico: bool) -> OrigenDatos:
    return OrigenDatos.SINTETICO if sintetico else OrigenDatos.REAL


def valor_rotulo(origen: OrigenDatos) -> str:
    """Valor de la columna de rótulo de una tabla exportada."""
    return ROTULO_SINTETICO if origen is OrigenDatos.SINTETICO else "real"


def exigir_rotulo_tabla(
    nombre: str, columnas: Sequence[str], valores: Iterable[Any], origen: OrigenDatos
) -> None:
    """Una tabla de resultados sintéticos debe tener la columna de rótulo en cada fila.

    Raises:
        RotuloFaltante: si falta la columna o alguna fila no lleva el rótulo.
    """
    if origen is not OrigenDatos.SINTETICO:
        return
    if CAMPO_ORIGEN not in columnas:
        raise RotuloFaltante(f"la tabla '{nombre}' (falta la columna {CAMPO_ORIGEN})")
    if any(v != ROTULO_SINTETICO for v in valores):
        raise RotuloFaltante(f"alguna fila de la tabla '{nombre}'")


def exigir_rotulo_texto(nombre: str, texto: str, origen: OrigenDatos) -> None:
    """Un reporte de resultados sintéticos debe empezar con la leyenda.

    Raises:
        RotuloFaltante: si el texto no empieza con la leyenda.
    """
    if origen is not OrigenDatos.SINTETICO:
        return
    primera = next((linea for linea in texto.splitlines() if linea.strip()), "")
    if LEYENDA_SINTETICA not in primera:
        raise RotuloFaltante(f"el comienzo de '{nombre}'")
