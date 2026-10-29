"""El script de generación solo escribe dentro de data/ (H2.3)."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest


def _main(raiz: Path) -> Callable[[list[str]], int]:
    especificacion = importlib.util.spec_from_file_location(
        "generar_sintetico", raiz / "scripts" / "generar_sintetico.py"
    )
    assert especificacion is not None
    assert especificacion.loader is not None
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return cast(Callable[[list[str]], int], modulo.main)


def test_el_script_rechaza_una_salida_fuera_de_data(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    salida = tmp_path / "fuera.csv"
    assert _main(raiz)(["--salida", str(salida), "--semilla", "1"]) == 1
    assert not salida.exists()
    assert "dentro de la carpeta data/" in capsys.readouterr().err


def test_el_script_exige_la_semilla(raiz: Path) -> None:
    with pytest.raises(SystemExit):
        _main(raiz)(["--salida", "data/x.csv"])
