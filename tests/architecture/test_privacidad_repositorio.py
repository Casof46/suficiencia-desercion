"""Privacidad y control de archivos (criterio 7 de H2.0; pruebas PA-03 y PA-04).

PA-03: la configuración de Streamlit desactiva la telemetría (RNF-06).
PA-04: los datos, artefactos y secretos quedan fuera del control de versiones (RNF-07).

Las comprobaciones de ``.gitignore`` usan el propio ``git`` en un repositorio
temporal, para que la prueba evalúe las reglas exactamente como lo hará git.
Si git no está instalado, esas pruebas se omiten y lo indican.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

GIT = shutil.which("git")
requiere_git = pytest.mark.skipif(GIT is None, reason="git no está instalado")

# Rutas que NUNCA deben versionarse (datos, bases locales, modelos, secretos, entornos, cachés).
DEBEN_IGNORARSE = [
    "data/raw/matricula_2024.xlsx",
    "data/processed/dataset.parquet",
    "data/interim/seudonimizado.csv",
    "workspace/registro.sqlite",
    "workspace/experimentos/abc/modelo.joblib",
    "reports/reporte.xlsx",
    "notas_institucionales.xlsx",
    "docs/anexo_estudiantes.csv",
    "tests/fixtures/extraccion_real.xls",
    "src/suficiencia/datos.csv",
    "local.db",
    "modelo_final.pkl",
    ".env",
    ".env.local",
    "credentials.json",
    "clave_privada.pem",
    ".streamlit/secrets.toml",
    ".venv/Lib/site-packages/x.py",
    "venv/bin/python",
    "src/suficiencia/__pycache__/x.cpython-312.pyc",
    ".pytest_cache/v/cache/nodeids",
    ".mypy_cache/3.12/x.json",
    ".hypothesis/examples/x",
    "~$plantilla.xlsx",
]

# Archivos del repositorio que SÍ deben versionarse.
DEBEN_VERSIONARSE = [
    "pyproject.toml",
    "requirements.lock",
    ".gitignore",
    ".importlinter",
    ".streamlit/config.toml",
    "config/proyecto.yaml",
    "config/escenarios.yaml",
    "config/ejemplos/escenarios_ficticio.yaml",
    "config/ejemplos/variables_ficticias.yaml",
    "data/README.md",
    "README.md",
    "src/suficiencia/__init__.py",
    "src/suficiencia/persistence/configuracion.py",
    "tests/conftest.py",
    "docs/gestion/acta_cierre_fase_1_propuesta.md",
    "scripts/verificar.py",
]

# Extensiones prohibidas entre los archivos versionados de un repositorio real.
EXTENSIONES_PROHIBIDAS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xlsm",
    ".xls",
    ".ods",
    ".parquet",
    ".feather",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".duckdb",
    ".joblib",
    ".pkl",
    ".pickle",
    ".onnx",
    ".pem",
    ".key",
    ".env",
}


def test_pa03_streamlit_no_recopila_estadisticas_de_uso(raiz: Path) -> None:
    with (raiz / ".streamlit" / "config.toml").open("rb") as archivo:
        configuracion = tomllib.load(archivo)
    assert configuracion.get("browser", {}).get("gatherUsageStats") is False


def _git(*argumentos: str, carpeta: Path) -> subprocess.CompletedProcess[str]:
    assert GIT is not None
    return subprocess.run(
        [GIT, *argumentos], cwd=carpeta, capture_output=True, text=True, check=False
    )


@pytest.fixture
def repo_temporal(raiz: Path, tmp_path: Path) -> Path:
    """Repositorio git vacío que solo contiene el .gitignore del proyecto."""
    _git("init", "--quiet", carpeta=tmp_path)
    shutil.copy(raiz / ".gitignore", tmp_path / ".gitignore")
    return tmp_path


@requiere_git
@pytest.mark.parametrize("ruta", DEBEN_IGNORARSE)
def test_pa04_rutas_sensibles_quedan_ignoradas(repo_temporal: Path, ruta: str) -> None:
    resultado = _git("check-ignore", "--no-index", "-q", ruta, carpeta=repo_temporal)
    assert resultado.returncode == 0, f"{ruta} no está excluida por .gitignore"


@requiere_git
@pytest.mark.parametrize("ruta", DEBEN_VERSIONARSE)
def test_pa04_archivos_del_proyecto_no_quedan_ignorados(repo_temporal: Path, ruta: str) -> None:
    resultado = _git("check-ignore", "--no-index", "-q", ruta, carpeta=repo_temporal)
    assert resultado.returncode == 1, f"{ruta} quedaría excluido por .gitignore"


@requiere_git
def test_pa04_ningun_archivo_sensible_esta_versionado(raiz: Path) -> None:
    """En un repositorio real, revisa los archivos ya versionados o preparados."""
    if _git("rev-parse", "--is-inside-work-tree", carpeta=raiz).returncode != 0:
        pytest.skip("La carpeta del proyecto todavía no es un repositorio git.")
    versionados = _git("ls-files", carpeta=raiz).stdout.splitlines()
    prohibidos = [
        ruta
        for ruta in versionados
        if Path(ruta).suffix.lower() in EXTENSIONES_PROHIBIDAS
        or (ruta.startswith("data/") and ruta != "data/README.md")
        or ruta.startswith(("workspace/", "reports/"))
    ]
    assert prohibidos == []
