"""Restricciones de dependencias entre capas (criterio 6 de H2.0; base de PA-01).

Qué se comprueba:

1. Los contratos de ``.importlinter`` se cumplen en el paquete real.
2. Control negativo con los contratos REALES: se copia ``.importlinter`` sobre un
   paquete temporal con las mismas cinco capas y se comprueba que cada violación
   prevista rompe un contrato y que los usos legítimos no lo rompen. Sin esto, un
   contrato mal escrito pasaría siempre, sobre todo mientras las capas estén vacías.
3. Todas las capas del paquete aparecen en el contrato de capas.

Límites (qué NO cubre import-linter): imports dinámicos (``importlib``,
``__import__``), imports dentro de cadenas o ``exec``, dependencias transitivas a
través de bibliotecas de terceros y el uso de archivos o servicios sin import.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path

import pytest
from importlinter.cli import lint_imports

CAPAS = ("ui", "application", "experimentation", "persistence", "domain")
PAQUETE_PRUEBA = "control_negativo"


def _ejecutar(config: Path) -> int:
    return lint_imports(config_filename=str(config), no_cache=True, no_logo=True)


def test_los_contratos_del_repositorio_se_cumplen(
    raiz: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(raiz)
    assert _ejecutar(raiz / ".importlinter") == 0


def test_el_contrato_de_capas_incluye_todas_las_capas(raiz: Path) -> None:
    config = configparser.ConfigParser()
    config.read(raiz / ".importlinter", encoding="utf-8")
    capas = config["importlinter:contract:capas"]["layers"]
    for capa in CAPAS:
        assert f"suficiencia.{capa}" in capas


def test_la_configuracion_de_contratos_es_ascii(raiz: Path) -> None:
    """import-linter lee ``.importlinter`` con la codificación regional del sistema.

    En Windows no es UTF-8: las tildes se mostraban mal y algunas letras, como
    "Á" o "Í", harían fallar la lectura (defecto D-19, hallado en Windows).
    """
    contenido = (raiz / ".importlinter").read_bytes()
    no_ascii = sorted({byte for byte in contenido if byte > 0x7F})
    assert not no_ascii, f"Bytes no ASCII en .importlinter: {no_ascii}"


@pytest.fixture
def paquete_prueba(raiz: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Paquete temporal con las cinco capas y los contratos reales del repositorio."""
    paquete = tmp_path / PAQUETE_PRUEBA
    paquete.mkdir()
    (paquete / "__init__.py").write_text("", encoding="utf-8")
    for capa in CAPAS:
        (paquete / capa).mkdir()
        (paquete / capa / "__init__.py").write_text("", encoding="utf-8")
    contratos = (raiz / ".importlinter").read_text(encoding="utf-8")
    assert "suficiencia" in contratos
    config = tmp_path / ".importlinter"
    config.write_text(contratos.replace("suficiencia", PAQUETE_PRUEBA), encoding="utf-8")
    monkeypatch.syspath_prepend(os.fspath(tmp_path))
    monkeypatch.chdir(tmp_path)
    return config


def _modulo(config: Path, capa: str, nombre: str, codigo: str) -> None:
    ruta = config.parent / PAQUETE_PRUEBA / capa / f"{nombre}.py"
    ruta.write_text(codigo.replace("PAQ", PAQUETE_PRUEBA), encoding="utf-8")


VIOLACIONES = [
    pytest.param("domain", "from PAQ.ui import pantalla\n", id="dominio-importa-interfaz"),
    pytest.param("domain", "import streamlit\n", id="dominio-importa-streamlit"),
    pytest.param("domain", "from sklearn import linear_model\n", id="dominio-importa-sklearn"),
    pytest.param("domain", "import sqlite3\n", id="dominio-importa-sqlite3"),
    pytest.param(
        "domain", "def f():\n    import yaml\n", id="dominio-importa-yaml-dentro-de-funcion"
    ),
    pytest.param("ui", "from PAQ.domain import regla\n", id="interfaz-importa-dominio-directo"),
    pytest.param(
        "ui", "from PAQ.persistence import repo\n", id="interfaz-importa-persistencia-directo"
    ),
    pytest.param(
        "persistence",
        "from PAQ.experimentation import m\n",
        id="persistencia-importa-experimentacion",
    ),
    pytest.param(
        "experimentation",
        "from PAQ.application import s\n",
        id="experimentacion-importa-aplicacion",
    ),
    pytest.param("application", "import streamlit\n", id="aplicacion-importa-streamlit"),
    pytest.param("persistence", "import plotly\n", id="persistencia-importa-plotly"),
]


@pytest.mark.parametrize(("capa", "codigo"), VIOLACIONES)
def test_control_negativo_cada_violacion_rompe_un_contrato(
    paquete_prueba: Path, capa: str, codigo: str
) -> None:
    """Los módulos externos no necesitan estar instalados: se analiza el código fuente."""
    for nombre_capa, nombre in (("ui", "pantalla"), ("domain", "regla"), ("persistence", "repo")):
        _modulo(paquete_prueba, nombre_capa, nombre, "VALOR = 1\n")
    _modulo(paquete_prueba, "experimentation", "m", "VALOR = 1\n")
    _modulo(paquete_prueba, "application", "s", "VALOR = 1\n")
    _modulo(paquete_prueba, capa, "violacion", codigo)
    assert _ejecutar(paquete_prueba) != 0


def test_usos_legitimos_no_rompen_los_contratos(paquete_prueba: Path) -> None:
    """ui -> application -> (persistence | experimentation) -> domain es el flujo previsto."""
    _modulo(paquete_prueba, "domain", "regla", "VALOR = 1\n")
    _modulo(paquete_prueba, "persistence", "repo", "from PAQ.domain import regla\n")
    _modulo(paquete_prueba, "experimentation", "m", "from PAQ.domain import regla\n")
    _modulo(
        paquete_prueba,
        "application",
        "servicio",
        "from PAQ.domain import regla\nfrom PAQ.persistence import repo\n"
        "from PAQ.experimentation import m\n",
    )
    _modulo(
        paquete_prueba, "ui", "pagina", "import streamlit\nfrom PAQ.application import servicio\n"
    )
    _modulo(paquete_prueba, "persistence", "lector", "import yaml\nimport sqlite3\n")
    assert _ejecutar(paquete_prueba) == 0
