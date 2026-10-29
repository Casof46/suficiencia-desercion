"""Lectura de archivos CSV y Excel (RF-M1-01) y escritura del dataset procesado.

Todas las celdas se leen como texto, sin interpretar números, fechas ni vacíos:
así un código con ceros a la izquierda (``00123``) no se convierte en ``123``.
La conversión a cada tipo la hace la auditoría según el diccionario. El archivo
original nunca se modifica.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.huella import Huella

EXTENSIONES = {".csv", ".xlsx"}


@dataclass(frozen=True)
class TablaLeida:
    tabla: pd.DataFrame
    huella_fuente: Huella
    """Huella SHA-256 del archivo tal como está en disco (RF-M1-07)."""


def leer_tabla(archivo: Path, separador: str = ",") -> TablaLeida:
    """Lee un CSV (UTF-8, con o sin BOM) o la primera hoja de un .xlsx, todo como texto."""
    if not archivo.is_file():
        raise ConfiguracionInvalida(f"No existe el archivo {archivo}.", "Revise la ruta indicada.")
    extension = archivo.suffix.lower()
    if extension not in EXTENSIONES:
        raise ConfiguracionInvalida(
            f"El archivo {archivo.name} no es CSV ni Excel (.xlsx).",
            "Guarde el archivo como .csv (UTF-8) o .xlsx.",
        )
    contenido = archivo.read_bytes()
    try:
        if extension == ".csv":
            tabla = pd.read_csv(
                archivo,
                sep=separador,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
            )
        else:
            tabla = pd.read_excel(archivo, sheet_name=0, dtype=str, keep_default_na=False)
    except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as error:
        raise ConfiguracionInvalida(
            f"No se pudo leer {archivo.name}: {error}",
            "Compruebe que el archivo no esté dañado, que el CSV esté en UTF-8 y que "
            "el separador sea el indicado.",
        ) from error
    tabla.columns = [str(c).strip() for c in tabla.columns]
    return TablaLeida(tabla=tabla, huella_fuente=Huella.de_bytes(contenido))


def contenido_canonico(tabla: pd.DataFrame) -> bytes:
    """CSV en UTF-8 con columnas y filas en orden fijo: base de la huella del dataset."""
    ordenada = tabla.sort_index(axis=1)
    return ordenada.to_csv(index=False, lineterminator="\n", date_format="%Y-%m-%d").encode("utf-8")


def escribir_csv(tabla: pd.DataFrame, archivo: Path) -> Huella:
    """Escribe el dataset procesado y devuelve su huella. No sobrescribe archivos."""
    if archivo.exists():
        raise ConfiguracionInvalida(
            f"Ya existe {archivo}.",
            "Elija otro nombre: los datasets procesados no se sobrescriben.",
        )
    contenido = contenido_canonico(tabla)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_bytes(contenido)
    return Huella.de_bytes(contenido)
