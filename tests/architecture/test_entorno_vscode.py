"""Configuración de VS Code del repositorio (`.vscode/`).

Las tareas y la depuración usan solo el entorno del proyecto (`.venv`), se
ejecutan en la carpeta del repositorio y no cambian la configuración de red del
visor, que sigue limitada a este equipo por `.streamlit/config.toml` (D-98).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

INTERPRETE = "${workspaceFolder}\\.venv\\Scripts\\python.exe"


def _json(raiz: Path, nombre: str) -> Any:
    return json.loads((raiz / ".vscode" / nombre).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "nombre", ["settings.json", "tasks.json", "launch.json", "extensions.json"]
)
def test_los_archivos_de_vscode_son_json_valido(raiz: Path, nombre: str) -> None:
    assert _json(raiz, nombre)


def test_las_tareas_usan_el_entorno_del_proyecto_y_archivos_existentes(raiz: Path) -> None:
    tareas = _json(raiz, "tasks.json")["tasks"]
    assert tareas
    for tarea in tareas:
        assert tarea["command"] == INTERPRETE, tarea["label"]
        assert tarea["options"]["cwd"] == "${workspaceFolder}", tarea["label"]
        argumentos = tarea["args"]
        assert not any(a.startswith("--server") for a in argumentos), tarea["label"]
        if argumentos[0].endswith(".py"):
            assert (raiz / argumentos[0]).is_file(), tarea["label"]
        if argumentos[:3] == ["-m", "streamlit", "run"]:
            assert (raiz / argumentos[3]).is_file(), tarea["label"]


def test_la_depuracion_y_el_editor_usan_el_mismo_interprete(raiz: Path) -> None:
    assert _json(raiz, "settings.json")["python.defaultInterpreterPath"] == INTERPRETE
    for configuracion in _json(raiz, "launch.json")["configurations"]:
        assert configuracion["python"] == INTERPRETE, configuracion["name"]
        assert not any(a.startswith("--server") for a in configuracion.get("args", []))
