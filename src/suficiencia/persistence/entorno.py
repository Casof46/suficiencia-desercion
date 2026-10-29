"""Captura del entorno de ejecución (RNF-17, RF-M6-01).

Registra la versión de Python, el sistema operativo, la huella del archivo de
bloqueo de dependencias, el commit de git (si lo hay) y los parámetros de
paralelismo. No registra rutas personales, usuario ni nombre del equipo.
"""

from __future__ import annotations

import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from suficiencia.domain.huella import Huella
from suficiencia.domain.trazabilidad.registros import Entorno

VARIABLES_HILOS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)
PAQUETES = ("suficiencia", "numpy", "pandas", "pydantic", "PyYAML", "openpyxl")


def _git(raiz: Path, *argumentos: str) -> str | None:
    ejecutable = shutil.which("git")
    if ejecutable is None:
        return None
    try:
        proceso = subprocess.run(
            [ejecutable, *argumentos],
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proceso.stdout.strip() if proceso.returncode == 0 else None


class CapturadorEntornoLocal:
    """Implementa el puerto ``CapturadorEntorno``."""

    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz

    def capturar(self) -> Entorno:
        bloqueo = self.raiz / "requirements.lock"
        commit = _git(self.raiz, "rev-parse", "HEAD")
        estado = _git(self.raiz, "status", "--porcelain") if commit else None
        paquetes = {}
        for paquete in PAQUETES:
            try:
                paquetes[paquete] = importlib.metadata.version(paquete)
            except importlib.metadata.PackageNotFoundError:
                paquetes[paquete] = "no instalado"
        return Entorno(
            python=sys.version.split()[0],
            sistema=f"{platform.system()} {platform.release()} ({platform.machine()})",
            huella_bloqueo=(
                Huella.de_bytes(bloqueo.read_bytes()).valor if bloqueo.is_file() else None
            ),
            commit=commit or None,
            cambios_sin_commit=bool(estado) if estado is not None else None,
            nucleos=os.cpu_count(),
            hilos={v: os.environ.get(v, "no definido") for v in VARIABLES_HILOS},
            paquetes=paquetes,
        )
