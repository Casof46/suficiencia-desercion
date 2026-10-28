"""El paquete se instala e importa correctamente (criterio 4 de H2.0)."""

from __future__ import annotations

import importlib
import importlib.metadata
from pathlib import Path

import pytest

import suficiencia

CAPAS = ("domain", "application", "experimentation", "persistence", "ui")


def test_version_del_paquete_coincide_con_los_metadatos_instalados() -> None:
    assert suficiencia.__version__ == importlib.metadata.version("suficiencia")


def test_el_paquete_importado_es_el_del_repositorio(raiz: Path) -> None:
    """Evita probar una copia antigua instalada en otro lugar."""
    ubicacion = Path(suficiencia.__file__).resolve()
    assert ubicacion.is_relative_to(raiz / "src" / "suficiencia")


@pytest.mark.parametrize("capa", CAPAS)
def test_cada_capa_se_importa(capa: str) -> None:
    modulo = importlib.import_module(f"suficiencia.{capa}")
    assert modulo.__doc__, f"La capa {capa} debe documentar su responsabilidad."


def test_no_existen_subpaquetes_fuera_de_las_cinco_capas(raiz: Path) -> None:
    """Un subpaquete nuevo debe añadirse a las capas y a los contratos de .importlinter."""
    paquete = raiz / "src" / "suficiencia"
    subpaquetes = {p.name for p in paquete.iterdir() if (p / "__init__.py").is_file()}
    assert subpaquetes == set(CAPAS)


def test_la_raiz_del_paquete_solo_contiene_la_linea_de_comandos(raiz: Path) -> None:
    """La lógica vive en las capas; en la raíz solo está la línea de comandos (H2.1)."""
    paquete = raiz / "src" / "suficiencia"
    modulos = {p.stem for p in paquete.glob("*.py")}
    assert modulos == {"__init__", "cli"}
