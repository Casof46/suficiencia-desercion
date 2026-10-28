"""Configuración del proyecto como objeto del dominio.

Solo describe los valores ya validados. Leer y validar ``config/proyecto.yaml``
es entrada y salida, y corresponde a la capa de persistencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfiguracionProyecto:
    """Configuración validada del proyecto.

    ``semilla_global`` y ``tolerancia_metricas`` pueden ser ``None``: la
    especificación los deja pendientes (RF-M3-06, RNF-03) y no se suponen valores.
    """

    raiz: Path
    nombre: str
    version_especificacion: str
    rutas: dict[str, Path]
    semilla_global: int | None
    tolerancia_metricas: float | None
