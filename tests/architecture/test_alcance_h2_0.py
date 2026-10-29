"""Alcance de los hitos construidos y fijación de dependencias.

Nació en H2.0 (criterios 3 y 10). Cuando un hito autorizado incorpora una
biblioteca de la lista, la quita de ``POSTERGADAS`` y registra el cambio en
docs/arquitectura/. H2.1 incorporó pydantic (decisión D-20) y H2.3, pandas, NumPy y
openpyxl (decisión D-41).
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

# Bibliotecas que ningún hito construido usa todavía (decisión D-04 de H2.0).
POSTERGADAS = {
    "streamlit",
    "plotly",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    "shap",
    "lime",
    "pyarrow",
    "joblib",
    "imbalanced-learn",
    "optuna",
    "sqlalchemy",
    "fastapi",
}


def _normalizar(nombre: str) -> str:
    return re.sub(r"[-_.]+", "-", nombre).lower()


def _nombre_requisito(especificacion: str) -> str:
    coincidencia = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", especificacion)
    assert coincidencia is not None, especificacion
    return _normalizar(coincidencia.group(1))


def _pyproject(raiz: Path) -> dict[str, object]:
    with (raiz / "pyproject.toml").open("rb") as archivo:
        return tomllib.load(archivo)


def _directas(raiz: Path) -> set[str]:
    proyecto = _pyproject(raiz)["project"]
    assert isinstance(proyecto, dict)
    nombres = {_nombre_requisito(d) for d in proyecto["dependencies"]}
    for grupo in proyecto.get("optional-dependencies", {}).values():
        nombres |= {_nombre_requisito(d) for d in grupo}
    return nombres


def _fijadas(raiz: Path) -> dict[str, str]:
    texto = (raiz / "requirements.lock").read_text(encoding="utf-8")
    return {
        _normalizar(nombre): version
        for nombre, version in re.findall(r"^([A-Za-z0-9._-]+)==([^\s;\\]+)", texto, re.M)
    }


def test_toda_dependencia_directa_esta_fijada_en_el_lock(raiz: Path) -> None:
    faltantes = _directas(raiz) - set(_fijadas(raiz))
    assert faltantes == set(), f"Regenerar requirements.lock; faltan: {sorted(faltantes)}"


def test_el_lock_fija_versiones_exactas_con_hashes(raiz: Path) -> None:
    texto = (raiz / "requirements.lock").read_text(encoding="utf-8")
    bloques = [b for b in re.split(r"\n(?=[A-Za-z0-9])", texto) if re.match(r"[A-Za-z0-9]", b)]
    assert bloques, "requirements.lock no contiene paquetes"
    for bloque in bloques:
        assert "==" in bloque.splitlines()[0], bloque.splitlines()[0]
        assert "--hash=sha256:" in bloque, f"Sin hash: {bloque.splitlines()[0]}"


def test_no_se_incorporan_bibliotecas_de_hitos_posteriores(raiz: Path) -> None:
    presentes = (_directas(raiz) | set(_fijadas(raiz))) & POSTERGADAS
    assert presentes == set(), f"Bibliotecas de hitos posteriores: {sorted(presentes)}"


def test_solo_el_repositorio_de_registros_usa_sqlite(raiz: Path) -> None:
    """DP-16 se decidió por SQLite (29-10-2026) solo para el registro de trazabilidad."""
    usos = []
    for archivo in (raiz / "src").rglob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            modulos: list[str] = []
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos = [nodo.module]
            if any(m.split(".")[0] == "sqlite3" for m in modulos):
                usos.append(archivo.relative_to(raiz).as_posix())
    assert sorted(set(usos)) == ["src/suficiencia/persistence/repositorio_sqlite.py"]


def test_version_minima_de_python(raiz: Path) -> None:
    proyecto = _pyproject(raiz)["project"]
    assert isinstance(proyecto, dict)
    assert proyecto["requires-python"] == ">=3.11"
