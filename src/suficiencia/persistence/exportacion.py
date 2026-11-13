"""Exportación de tablas a CSV y Excel (RF-M6-03), siempre a través del filtro de
identificadores (RNF-05, PI-04). Desde F3.7, también los archivos del reporte de
resultados."""

from __future__ import annotations

import io
from collections.abc import Iterable, Mapping
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


def archivos_resultados(texto: str, tablas: Mapping[str, pd.DataFrame]) -> dict[str, bytes]:
    """Contenido de los archivos de un reporte (F3.7): texto, un CSV por tabla y un Excel.

    Cada tabla pasa por el filtro de identificadores (RNF-05). Se construye en memoria,
    para que la interfaz pueda ofrecer las descargas sin escribir archivos.
    """
    for tabla in tablas.values():
        exigir_sin_identificadores([str(c) for c in tabla.columns])
    archivos = {"reporte.md": texto.encode("utf-8")}
    for nombre, tabla in tablas.items():
        archivos[f"{nombre}.csv"] = tabla.to_csv(index=False, lineterminator="\n").encode("utf-8")
    libro = io.BytesIO()
    with pd.ExcelWriter(libro, engine="openpyxl") as escritor:
        for nombre, tabla in tablas.items():
            tabla.to_excel(escritor, sheet_name=nombre[:31], index=False)
    archivos["resultados.xlsx"] = libro.getvalue()
    return archivos


def escribir_archivos(carpeta: Path, archivos: Mapping[str, bytes]) -> dict[str, str]:
    """Escribe los archivos en una carpeta nueva y devuelve la huella de cada uno.

    Raises:
        ConfiguracionInvalida: si la carpeta ya existe (las exportaciones no se sobrescriben).
    """
    if carpeta.exists():
        raise ConfiguracionInvalida(
            f"Ya existe {carpeta}.", "Elija otro nombre: las exportaciones no se sobrescriben."
        )
    carpeta.mkdir(parents=True)
    huellas = {}
    for nombre, contenido in archivos.items():
        (carpeta / nombre).write_bytes(contenido)
        huellas[nombre] = Huella.de_bytes(contenido).valor
    return huellas
