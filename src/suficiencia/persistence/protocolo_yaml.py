"""Lectura en YAML del protocolo confirmatorio y de configuraciones para congelar (H2.6).

El protocolo del proyecto no existe todavía (DP-06 a DP-20 abiertas). El ejemplo
de ``config/ejemplos/protocolo_ficticio.yaml`` es inventado y lo declara. No hay
ruta por omisión: cada comando recibe el archivo que debe leer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from suficiencia.domain.errores import ConfiguracionInvalida


def leer_yaml(archivo: Path) -> Any:
    """Devuelve el contenido de un archivo YAML.

    Raises:
        ConfiguracionInvalida: si el archivo no existe o no es un YAML válido.
    """
    if not archivo.is_file():
        raise ConfiguracionInvalida(f"No existe el archivo {archivo}.", "Revise la ruta indicada.")
    try:
        return yaml.safe_load(archivo.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfiguracionInvalida(
            f"{archivo}: no es un YAML válido ({error.__class__.__name__}).",
            "Corrija el archivo; el ejemplo válido está en "
            "config/ejemplos/protocolo_ficticio.yaml.",
        ) from error
