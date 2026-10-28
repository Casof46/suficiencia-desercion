"""La configuración del proyecto puede leerse y se valida (criterio 3 de H2.0)."""

from __future__ import annotations

from pathlib import Path

import pytest

from suficiencia.persistence.configuracion import (
    ConfiguracionProyecto,
    ErrorConfiguracion,
    cargar_configuracion,
)

CONFIG_VALIDA = """\
version_configuracion: 1
proyecto:
  nombre: "Proyecto de prueba"
  version_especificacion: "0.4"
rutas:
  datos: data
  espacio_trabajo: workspace
  reportes: reports
reproducibilidad:
  semilla_global: null
  tolerancia_metricas: null
"""


def _escribir(tmp_path: Path, contenido: str) -> Path:
    carpeta = tmp_path / "config"
    carpeta.mkdir()
    archivo = carpeta / "proyecto.yaml"
    archivo.write_text(contenido, encoding="utf-8")
    return archivo


def test_la_configuracion_del_repositorio_se_lee(raiz: Path) -> None:
    config = cargar_configuracion(raiz / "config" / "proyecto.yaml")
    assert isinstance(config, ConfiguracionProyecto)
    assert config.raiz == raiz
    assert config.version_especificacion == "0.4"
    assert set(config.rutas) == {"datos", "espacio_trabajo", "reportes"}
    for ruta in config.rutas.values():
        assert ruta.is_relative_to(raiz)


def test_la_configuracion_no_fija_valores_pendientes(raiz: Path) -> None:
    """Semilla y tolerancia siguen pendientes (RF-M3-06, RNF-03): no se inventan."""
    config = cargar_configuracion(raiz / "config" / "proyecto.yaml")
    assert config.semilla_global is None
    assert config.tolerancia_metricas is None


def test_configuracion_minima_valida(tmp_path: Path) -> None:
    config = cargar_configuracion(_escribir(tmp_path, CONFIG_VALIDA))
    assert config.rutas["datos"] == tmp_path / "data"


def test_archivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(ErrorConfiguracion, match="No existe"):
        cargar_configuracion(tmp_path / "config" / "proyecto.yaml")


def test_yaml_invalido(tmp_path: Path) -> None:
    with pytest.raises(ErrorConfiguracion, match="YAML"):
        cargar_configuracion(_escribir(tmp_path, "rutas: [sin cerrar"))


def test_clave_desconocida(tmp_path: Path) -> None:
    contenido = CONFIG_VALIDA.replace("semilla_global", "semila_global")
    with pytest.raises(ErrorConfiguracion, match="desconocidas"):
        cargar_configuracion(_escribir(tmp_path, contenido))


def test_falta_una_ruta_obligatoria(tmp_path: Path) -> None:
    contenido = CONFIG_VALIDA.replace("  reportes: reports\n", "")
    with pytest.raises(ErrorConfiguracion, match="Faltan rutas"):
        cargar_configuracion(_escribir(tmp_path, contenido))


@pytest.mark.parametrize("ruta", ["/datos", "../fuera", "C:/datos", "data/../../fuera"])
def test_rutas_fuera_del_repositorio(tmp_path: Path, ruta: str) -> None:
    contenido = CONFIG_VALIDA.replace("datos: data", f"datos: '{ruta}'")
    with pytest.raises(ErrorConfiguracion, match="relativa"):
        cargar_configuracion(_escribir(tmp_path, contenido))


@pytest.mark.parametrize("valor", ["true", "1.5", "'42'"])
def test_semilla_con_tipo_invalido(tmp_path: Path, valor: str) -> None:
    contenido = CONFIG_VALIDA.replace("semilla_global: null", f"semilla_global: {valor}")
    with pytest.raises(ErrorConfiguracion, match="semilla_global"):
        cargar_configuracion(_escribir(tmp_path, contenido))


def test_tolerancia_negativa(tmp_path: Path) -> None:
    contenido = CONFIG_VALIDA.replace("tolerancia_metricas: null", "tolerancia_metricas: -0.1")
    with pytest.raises(ErrorConfiguracion, match="tolerancia_metricas"):
        cargar_configuracion(_escribir(tmp_path, contenido))


def test_version_de_configuracion_no_soportada(tmp_path: Path) -> None:
    contenido = CONFIG_VALIDA.replace("version_configuracion: 1", "version_configuracion: 2")
    with pytest.raises(ErrorConfiguracion, match="version_configuracion"):
        cargar_configuracion(_escribir(tmp_path, contenido))
