"""Alcance del hito H2.0 (criterio 10) y fijación de dependencias (criterio 3).

Estas pruebas protegen las decisiones temporales de H2.0. Cuando un hito
autorizado incorpore una biblioteca de la lista, debe actualizar esta prueba y
registrar el cambio en docs/arquitectura/.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

# Bibliotecas de fases posteriores que H2.0 no instala (decisión D-04).
POSTERGADAS = {
    "streamlit",
    "plotly",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    "shap",
    "lime",
    "pandas",
    "numpy",
    "pyarrow",
    "openpyxl",
    "pydantic",
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


def test_h2_0_no_incorpora_bibliotecas_de_fases_posteriores(raiz: Path) -> None:
    presentes = (_directas(raiz) | set(_fijadas(raiz))) & POSTERGADAS
    assert presentes == set(), f"Bibliotecas no autorizadas en H2.0: {sorted(presentes)}"


def test_ningun_modulo_usa_sqlite_mientras_dp16_este_pendiente(raiz: Path) -> None:
    """DP-16 (SQLite o archivos para el registro) sigue abierta."""
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
                usos.append(str(archivo.relative_to(raiz)))
    assert usos == []


def test_version_minima_de_python(raiz: Path) -> None:
    proyecto = _pyproject(raiz)["project"]
    assert isinstance(proyecto, dict)
    assert proyecto["requires-python"] == ">=3.11"
