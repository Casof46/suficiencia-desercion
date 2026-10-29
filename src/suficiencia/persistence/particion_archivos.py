"""Persistencia de los índices de la partición (RF-M2-06) en la carpeta de trabajo.

Cada partición se guarda en su propia carpeta dentro de ``workspace/particiones/``
(que git no versiona) con un archivo por partición, solo con las columnas que
identifican cada unidad (seudónimo) y su cohorte, y un manifiesto con las
cohortes, los tamaños y las huellas. Nunca se sobrescribe una partición.

El archivo de prueba solo se vuelve a leer a través del sello (``SelloPrueba``),
que registra cada intento. Quien abra el archivo con otro programa queda fuera
de ese control: la protección del sello es del software, no del sistema de archivos.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.particion import Division
from suficiencia.domain.huella import Huella
from suficiencia.persistence.lectores import contenido_canonico

MANIFIESTO = "particion.json"
ARCHIVOS = {
    "desarrollo": "desarrollo.csv",
    "prueba": "prueba.csv",
    "piloto": "piloto.csv",
    "excluidas": "excluidas.csv",
}


def guardar_division(
    division: Division, columnas: list[str], carpeta: Path, datos_manifiesto: dict[str, Any]
) -> dict[str, str]:
    """Escribe los índices de cada partición y el manifiesto; devuelve las huellas."""
    if carpeta.exists():
        raise ConfiguracionInvalida(
            f"Ya existe la partición {carpeta}.",
            "Las particiones no se sobrescriben; cada construcción crea una carpeta nueva.",
        )
    carpeta.mkdir(parents=True)
    huellas: dict[str, str] = {}
    partes = {
        "desarrollo": division.desarrollo,
        "prueba": division.prueba,
        "piloto": division.piloto,
        "excluidas": division.excluidas,
    }
    for nombre, tabla in partes.items():
        contenido = contenido_canonico(tabla[columnas].sort_values(columnas, ignore_index=True))
        (carpeta / ARCHIVOS[nombre]).write_bytes(contenido)
        huellas[nombre] = Huella.de_bytes(contenido).valor
    manifiesto = {**datos_manifiesto, "huellas": huellas, "columnas": columnas}
    (carpeta / MANIFIESTO).write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return huellas


def cargador_de_prueba(carpeta: Path) -> Callable[[], pd.DataFrame]:
    """Función que lee la prueba guardada; solo debe entregarse a ``SelloPrueba``."""
    manifiesto = leer_manifiesto(carpeta)

    def cargar() -> pd.DataFrame:
        tabla = pd.read_csv(carpeta / ARCHIVOS["prueba"], dtype=str, keep_default_na=False)
        if Huella.de_bytes(contenido_canonico(tabla)).valor != manifiesto["huellas"]["prueba"]:
            raise ConfiguracionInvalida(
                f"Los índices de prueba de {carpeta} no coinciden con su huella.",
                "La partición fue modificada fuera del programa; no la use.",
            )
        return tabla

    return cargar


def leer_manifiesto(carpeta: Path) -> dict[str, Any]:
    archivo = carpeta / MANIFIESTO
    if not archivo.is_file():
        raise ConfiguracionInvalida(
            f"{carpeta} no es una partición guardada (falta {MANIFIESTO}).",
            "Indique una carpeta creada por `suficiencia poblaciones construir`.",
        )
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ConfiguracionInvalida(f"{archivo} no es válido.", "No modifique el manifiesto.")
    return datos
