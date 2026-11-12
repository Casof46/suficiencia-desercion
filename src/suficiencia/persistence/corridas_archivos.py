"""Archivos de cada corrida de entrenamiento (RF-M3-07; F3.2).

Cada corrida (escenario × familia) guarda, en ``workspace/experimentos/`` (no
versionado):

- ``predicciones.csv``: probabilidades de validación fuera de fold, con su fold,
  cohorte y etiqueta. Sin seudónimos ni códigos de estudiante.
- ``modelo_fold_<n>.joblib``: el modelo ajustado de cada fold.
- ``manifiesto.json``: configuración de la corrida y huellas de los archivos.

Los archivos ``.joblib`` solo deben abrirse si los generó este programa.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.huella import Huella


def guardar_corrida(
    carpeta: Path,
    predicciones: pd.DataFrame,
    modelos: Mapping[int, object],
    manifiesto: Mapping[str, Any],
) -> dict[str, str]:
    """Escribe los archivos de una corrida y devuelve la huella de cada uno.

    Se escribe primero en una carpeta ``.incompleta`` que solo se renombra al final:
    una corrida que falla a mitad de camino no deja una carpeta que parezca completa.

    Raises:
        ConfiguracionInvalida: si la carpeta final ya existe (nunca se sobrescribe).
    """
    if carpeta.exists():
        raise ConfiguracionInvalida(
            f"La carpeta de la corrida ya existe: {carpeta.name}.",
            "Ya hay archivos de una corrida igual que no figura en el registro; muévalos "
            "o bórrelos antes de repetirla.",
        )
    final, carpeta = carpeta, carpeta.with_name(carpeta.name + ".incompleta")
    if carpeta.exists():
        shutil.rmtree(carpeta)  # restos de un intento anterior que falló
    carpeta.mkdir(parents=True)
    huellas: dict[str, str] = {}
    archivo = carpeta / "predicciones.csv"
    predicciones.to_csv(archivo, index=False, encoding="utf-8", lineterminator="\n")
    huellas[archivo.name] = Huella.de_bytes(archivo.read_bytes()).valor
    for numero, modelo in sorted(modelos.items()):
        archivo = carpeta / f"modelo_fold_{numero}.joblib"
        joblib.dump(modelo, archivo)
        huellas[archivo.name] = Huella.de_bytes(archivo.read_bytes()).valor
    contenido = {**manifiesto, "huellas_archivos": huellas}
    (carpeta / "manifiesto.json").write_text(
        json.dumps(contenido, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    carpeta.rename(final)
    return huellas


def leer_predicciones(carpeta: Path, huella_esperada: str) -> pd.DataFrame:
    """Lee ``predicciones.csv`` de una corrida, después de comprobar su huella.

    Raises:
        ConfiguracionInvalida: si el archivo no existe o cambió desde que se registró.
    """
    archivo = carpeta / "predicciones.csv"
    if not archivo.exists():
        raise ConfiguracionInvalida(
            f"No se encuentra {archivo}.",
            "Los archivos de la corrida se movieron o se borraron; vuelva a entrenarla.",
        )
    contenido = archivo.read_bytes()
    if Huella.de_bytes(contenido).valor != huella_esperada:
        raise ConfiguracionInvalida(
            f"{archivo} cambió después de registrarse: su huella no coincide.",
            "No use predicciones modificadas; vuelva a entrenar la corrida.",
        )
    return pd.read_csv(archivo, dtype={"cohorte": str})


def guardar_modelo_final(carpeta: Path, modelo: object, manifiesto: Mapping[str, Any]) -> str:
    """Guarda el modelo representativo de un escenario y devuelve la huella del archivo (F3.4).

    Raises:
        ConfiguracionInvalida: si la carpeta ya existe (nunca se sobrescribe).
    """
    if carpeta.exists():
        raise ConfiguracionInvalida(
            f"La carpeta de la selección ya existe: {carpeta.name}.",
            "Ya hay una selección igual; no se sobrescribe.",
        )
    carpeta.mkdir(parents=True)
    archivo = carpeta / "modelo_final.joblib"
    joblib.dump(modelo, archivo)
    huella = Huella.de_bytes(archivo.read_bytes()).valor
    (carpeta / "manifiesto.json").write_text(
        json.dumps(
            {**manifiesto, "huella_modelo": huella}, ensure_ascii=False, indent=2, sort_keys=True
        ),
        encoding="utf-8",
    )
    return huella


def leer_modelo(archivo: Path, huella_esperada: str) -> object:
    """Carga un modelo guardado por este programa, después de comprobar su huella.

    Raises:
        ConfiguracionInvalida: si el archivo no existe o cambió desde que se guardó.
    """
    if not archivo.exists():
        raise ConfiguracionInvalida(
            f"No se encuentra el modelo {archivo}.",
            "El archivo se movió o se borró; vuelva a seleccionar y congelar.",
        )
    if Huella.de_bytes(archivo.read_bytes()).valor != huella_esperada:
        raise ConfiguracionInvalida(
            f"El modelo {archivo} cambió después de guardarse: su huella no coincide.",
            "No evalúe un modelo modificado; vuelva a seleccionar y congelar.",
        )
    return joblib.load(archivo)


def guardar_predicciones_prueba(
    carpeta: Path, tablas: Mapping[str, pd.DataFrame]
) -> dict[str, dict[str, str]]:
    """Guarda las predicciones de prueba de cada configuración evaluada (F3.5).

    Las usa la evaluación comparativa (CU-12), que así no vuelve a abrir la prueba
    (PI-15). Cada tabla lleva seudónimo, cohorte, etiqueta y probabilidad. Devuelve,
    por configuración, el archivo (relativo a ``carpeta``) y su huella.

    Raises:
        ConfiguracionInvalida: si la carpeta ya existe.
    """
    if carpeta.exists():
        raise ConfiguracionInvalida(
            f"La carpeta de la evaluación final ya existe: {carpeta.name}.",
            "No se sobrescribe; repita la evaluación final más tarde.",
        )
    carpeta.mkdir(parents=True)
    resultado = {}
    for numero, (identificador, tabla) in enumerate(tablas.items(), start=1):
        archivo = carpeta / f"configuracion_{numero}.csv"
        tabla.to_csv(archivo, index=False, encoding="utf-8", lineterminator="\n")
        resultado[identificador] = {
            "archivo": archivo.name,
            "huella": Huella.de_bytes(archivo.read_bytes()).valor,
        }
    return resultado


def guardar_explicaciones(
    carpeta: Path, tablas: Mapping[str, pd.DataFrame]
) -> dict[str, dict[str, str]]:
    """Guarda las tablas de una explicación (F3.6): ``<nombre>.csv`` por cada tabla.

    Devuelve, por nombre, el archivo (relativo a ``carpeta``) y su huella, que quedan
    en el registro (PI-13).

    Raises:
        ConfiguracionInvalida: si la carpeta ya existe o un nombre no es válido.
    """
    if carpeta.exists():
        raise ConfiguracionInvalida(
            f"La carpeta de la explicación ya existe: {carpeta.name}.",
            "No se sobrescribe; repita la explicación más tarde.",
        )
    invalidos = [n for n in tablas if not n or not all(c.isalnum() or c == "_" for c in n)]
    if invalidos:
        raise ConfiguracionInvalida(
            f"Nombres de tabla no válidos: {', '.join(invalidos)}.",
            "Es un defecto del programa; informe el caso.",
        )
    carpeta.mkdir(parents=True)
    resultado = {}
    for nombre, tabla in tablas.items():
        archivo = carpeta / f"{nombre}.csv"
        tabla.to_csv(archivo, index=False, encoding="utf-8", lineterminator="\n")
        resultado[nombre] = {
            "archivo": archivo.name,
            "huella": Huella.de_bytes(archivo.read_bytes()).valor,
        }
    return resultado


def leer_csv_verificado(archivo: Path, huella_esperada: str) -> pd.DataFrame:
    """Lee un CSV guardado por el programa después de comprobar su huella (F3.5).

    Raises:
        ConfiguracionInvalida: si no existe o cambió desde que se registró.
    """
    if not archivo.exists():
        raise ConfiguracionInvalida(
            f"No se encuentra {archivo}.", "El archivo se movió o se borró."
        )
    if Huella.de_bytes(archivo.read_bytes()).valor != huella_esperada:
        raise ConfiguracionInvalida(
            f"{archivo} cambió después de registrarse: su huella no coincide.",
            "No use archivos modificados.",
        )
    return pd.read_csv(archivo, dtype={"cohorte": str})
