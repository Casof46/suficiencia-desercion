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
