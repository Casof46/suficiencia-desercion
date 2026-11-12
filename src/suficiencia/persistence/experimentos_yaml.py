"""Lectura de la configuración de experimentos en YAML (F3.1).

La configuración del proyecto (``config/experimentos.yaml``) depende de DP-03,
DP-07 y DP-12 y todavía no existe. El ejemplo de
``config/ejemplos/experimentos_ficticio.yaml`` es inventado y lo declara.
"""

from __future__ import annotations

from pathlib import Path

from suficiencia.domain.errores import DecisionPendiente
from suficiencia.domain.experimentos import (
    ConfiguracionExperimentos,
    configuracion_experimentos_desde_datos,
)
from suficiencia.persistence.protocolo_yaml import leer_yaml

ARCHIVO_DEL_PROYECTO = Path("config/experimentos.yaml")


def cargar_configuracion_experimentos(archivo: Path) -> ConfiguracionExperimentos:
    """Lee y valida la configuración de experimentos.

    Raises:
        DecisionPendiente: si el archivo del proyecto no existe todavía (DP-07) o un
            campo vale ``null``.
        ConfiguracionInvalida: si el archivo no existe o no tiene el formato esperado.
    """
    if not archivo.exists() and archivo.as_posix().endswith(ARCHIVO_DEL_PROYECTO.as_posix()):
        raise DecisionPendiente(
            "DP-07", f"la configuración de experimentos del proyecto ({ARCHIVO_DEL_PROYECTO})"
        )
    return configuracion_experimentos_desde_datos(leer_yaml(archivo))
