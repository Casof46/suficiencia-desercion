"""Ejecuta todas las comprobaciones de calidad del proyecto, en orden.

Uso (desde la raíz del repositorio, con el entorno del proyecto):

    Windows:      .venv\\Scripts\\python scripts\\verificar.py
    Linux/macOS:  .venv/bin/python scripts/verificar.py

Existe porque Windows no incluye ``make``: un único comando reproduce en
cualquier sistema las mismas comprobaciones. Termina con código distinto de
cero si alguna falla.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

COMPROBACIONES: list[tuple[str, list[str]]] = [
    ("Estilo y errores comunes (ruff check)", ["-m", "ruff", "check", "."]),
    ("Formato (ruff format --check)", ["-m", "ruff", "format", "--check", "."]),
    ("Tipos (mypy)", ["-m", "mypy"]),
    # "python -m importlinter.cli" termina con código 0 sin ejecutar nada; por eso se
    # invoca la misma función que el comando lint-imports.
    (
        "Contratos de capas (import-linter)",
        [
            "-c",
            "import sys; from importlinter.cli import lint_imports_command as c; "
            "sys.exit(c(['--no-cache']))",
        ],
    ),
    ("Pruebas (pytest)", ["-m", "pytest"]),
]


def main() -> int:
    print(f"Python {sys.version.split()[0]} en {sys.executable}")
    resultados: list[tuple[str, int]] = []
    for nombre, argumentos in COMPROBACIONES:
        print(f"\n=== {nombre} ===", flush=True)
        proceso = subprocess.run([sys.executable, *argumentos], cwd=RAIZ, check=False)
        resultados.append((nombre, proceso.returncode))

    print("\n=== Resumen ===")
    for nombre, codigo in resultados:
        print(f"{'OK   ' if codigo == 0 else 'FALLA'}  {nombre}")
    return 0 if all(codigo == 0 for _, codigo in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
