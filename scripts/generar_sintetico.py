"""Genera un historial de matrícula SINTÉTICO para probar la importación (H2.3).

Uso, desde la raíz del repositorio (en Linux o macOS, con ``.venv/bin/python``):

    .venv\\Scripts\\python scripts\\generar_sintetico.py --semilla 1 \\
        --salida data\\sintetico\\historial.csv

Los datos son inventados (ver ``tests/fixtures/generador_sintetico.py``) y cada fila
lleva ``origen_datos = SINTETICO``. La salida debe quedar dentro de ``data/``, que
git no versiona. Con ``--con-errores`` se siembran cuatro problemas de calidad para
ver cómo los detecta la auditoría.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tests"))

from fixtures.generador_sintetico import (  # noqa: E402
    HISTORIALES_FIJOS,
    generar_historial,
    sembrar_problemas,
)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Genera un historial de matrícula SINTÉTICO (CSV o Excel)."
    )
    analizador.add_argument("--salida", type=Path, required=True, help="Archivo .csv o .xlsx.")
    analizador.add_argument(
        "--semilla", type=int, required=True, help="Semilla del generador (cualquier entero)."
    )
    analizador.add_argument(
        "--estudiantes", type=int, default=300, help="Número de estudiantes (por omisión, 300)."
    )
    analizador.add_argument(
        "--con-errores", action="store_true", help="Siembra problemas de calidad conocidos."
    )
    argumentos = analizador.parse_args(argv)

    salida: Path = argumentos.salida
    destino = salida if salida.is_absolute() else Path.cwd() / salida
    if not destino.resolve().is_relative_to((RAIZ / "data").resolve()):
        print("Error: la salida debe estar dentro de la carpeta data/.", file=sys.stderr)
        return 1
    if destino.suffix.lower() not in {".csv", ".xlsx"}:
        print("Error: la salida debe terminar en .csv o .xlsx.", file=sys.stderr)
        return 1
    if destino.exists():
        print(f"Error: ya existe {destino}; elija otro nombre.", file=sys.stderr)
        return 1
    if argumentos.estudiantes < len(HISTORIALES_FIJOS):
        print(
            f"Error: se necesitan al menos {len(HISTORIALES_FIJOS)} estudiantes.", file=sys.stderr
        )
        return 1

    tabla = generar_historial(argumentos.estudiantes, argumentos.semilla)
    if argumentos.con_errores:
        tabla, sembrados = sembrar_problemas(tabla)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.suffix.lower() == ".csv":
        tabla.to_csv(destino, index=False, encoding="utf-8")
    else:
        tabla.to_excel(destino, index=False)

    print("DATOS SINTÉTICOS: inventados para pruebas; no usar como resultado.")
    print(f"Archivo: {destino}")
    print(f"Estudiantes: {tabla['codigo_estudiante'].nunique()}; filas: {len(tabla)}")
    if argumentos.con_errores:
        print(
            "Problemas sembrados: vacío obligatorio en la fila "
            f"{sembrados.fila_nula_obligatoria}, fuera de rango en la "
            f"{sembrados.fila_fuera_de_rango}, tipo inválido en la "
            f"{sembrados.fila_tipo_invalido} y fila duplicada en la {sembrados.fila_duplicada}."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
