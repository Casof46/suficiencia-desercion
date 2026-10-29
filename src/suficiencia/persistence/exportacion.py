"""Exportación de tablas a CSV y Excel (RF-M6-03), siempre a través del filtro de
identificadores (RNF-05, PI-04)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.huella import Huella
from suficiencia.domain.trazabilidad.filtro import exigir_sin_identificadores


def exportar_tabla(
    tabla: pd.DataFrame, archivo: Path, identificadores_declarados: Iterable[str] = ()
) -> Huella:
    """Escribe la tabla en .csv o .xlsx, sin sobrescribir, y devuelve la huella del archivo."""
    exigir_sin_identificadores([str(c) for c in tabla.columns], identificadores_declarados)
    extension = archivo.suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise ConfiguracionInvalida(
            f"No se puede exportar a {archivo.name}.", "Use un nombre terminado en .csv o .xlsx."
        )
    if archivo.exists():
        raise ConfiguracionInvalida(
            f"Ya existe {archivo}.", "Elija otro nombre: las exportaciones no se sobrescriben."
        )
    archivo.parent.mkdir(parents=True, exist_ok=True)
    if extension == ".csv":
        tabla.to_csv(archivo, index=False, encoding="utf-8")
    else:
        tabla.to_excel(archivo, index=False)
    return Huella.de_bytes(archivo.read_bytes())
