"""Lectura y validación de ``config/proyecto.yaml``.

Es el único código funcional del hito H2.0. Valida la estructura del archivo y
rechaza claves desconocidas, para que un error tipográfico no pase inadvertido.
No asigna valores por defecto a parámetros que la especificación deja pendientes:
``semilla_global`` y ``tolerancia_metricas`` pueden ser ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

VERSION_CONFIGURACION_SOPORTADA = 1
_RUTAS_REQUERIDAS = ("datos", "espacio_trabajo", "reportes")
_CLAVES_RAIZ = {"version_configuracion", "proyecto", "rutas", "reproducibilidad"}
_CLAVES_PROYECTO = {"nombre", "version_especificacion"}
_CLAVES_REPRODUCIBILIDAD = {"semilla_global", "tolerancia_metricas"}


class ErrorConfiguracion(ValueError):
    """La configuración del proyecto no existe o no es válida."""


@dataclass(frozen=True)
class ConfiguracionProyecto:
    """Configuración validada del proyecto."""

    raiz: Path
    nombre: str
    version_especificacion: str
    rutas: dict[str, Path]
    semilla_global: int | None
    tolerancia_metricas: float | None


def _seccion(datos: dict[str, Any], nombre: str, permitidas: set[str]) -> dict[str, Any]:
    valor = datos.get(nombre)
    if not isinstance(valor, dict):
        raise ErrorConfiguracion(f"Falta la sección '{nombre}' o no es un diccionario.")
    desconocidas = set(valor) - permitidas
    if desconocidas:
        raise ErrorConfiguracion(
            f"Claves desconocidas en '{nombre}': {sorted(desconocidas)}. "
            "Revise si hay un error tipográfico."
        )
    return valor


def _ruta_relativa(nombre: str, valor: Any, raiz: Path) -> Path:
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorConfiguracion(f"La ruta '{nombre}' debe ser un texto no vacío.")
    relativa = PurePosixPath(valor.replace("\\", "/"))
    if relativa.is_absolute() or ".." in relativa.parts or ":" in valor:
        raise ErrorConfiguracion(
            f"La ruta '{nombre}' debe ser relativa y estar dentro del repositorio: {valor!r}."
        )
    return raiz.joinpath(*relativa.parts)


def cargar_configuracion(archivo: Path) -> ConfiguracionProyecto:
    """Lee y valida la configuración del proyecto.

    La raíz del proyecto es la carpeta que contiene ``config/``.

    Raises:
        ErrorConfiguracion: si el archivo no existe, no es YAML válido o su
            estructura no coincide con la esperada.
    """
    if not archivo.is_file():
        raise ErrorConfiguracion(f"No existe el archivo de configuración: {archivo}")
    try:
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ErrorConfiguracion(f"El archivo {archivo} no es YAML válido: {error}") from error
    if not isinstance(datos, dict):
        raise ErrorConfiguracion("La configuración debe ser un diccionario YAML.")

    desconocidas = set(datos) - _CLAVES_RAIZ
    if desconocidas:
        raise ErrorConfiguracion(f"Claves desconocidas en la raíz: {sorted(desconocidas)}.")
    version = datos.get("version_configuracion")
    if version != VERSION_CONFIGURACION_SOPORTADA:
        raise ErrorConfiguracion(
            f"version_configuracion debe ser {VERSION_CONFIGURACION_SOPORTADA}; "
            f"se encontró {version!r}."
        )

    raiz = archivo.resolve().parent.parent
    proyecto = _seccion(datos, "proyecto", _CLAVES_PROYECTO)
    rutas_yaml = _seccion(datos, "rutas", set(_RUTAS_REQUERIDAS))
    reproducibilidad = _seccion(datos, "reproducibilidad", _CLAVES_REPRODUCIBILIDAD)

    faltantes = [clave for clave in _RUTAS_REQUERIDAS if clave not in rutas_yaml]
    if faltantes:
        raise ErrorConfiguracion(f"Faltan rutas obligatorias: {faltantes}.")
    rutas = {clave: _ruta_relativa(clave, rutas_yaml[clave], raiz) for clave in _RUTAS_REQUERIDAS}

    nombre = proyecto.get("nombre")
    version_especificacion = proyecto.get("version_especificacion")
    if not isinstance(nombre, str) or not nombre.strip():
        raise ErrorConfiguracion("proyecto.nombre debe ser un texto no vacío.")
    if not isinstance(version_especificacion, str) or not version_especificacion.strip():
        raise ErrorConfiguracion("proyecto.version_especificacion debe ser un texto no vacío.")

    semilla = reproducibilidad.get("semilla_global")
    if semilla is not None and (isinstance(semilla, bool) or not isinstance(semilla, int)):
        raise ErrorConfiguracion("reproducibilidad.semilla_global debe ser un entero o null.")
    tolerancia = reproducibilidad.get("tolerancia_metricas")
    if tolerancia is not None and (
        isinstance(tolerancia, bool) or not isinstance(tolerancia, (int, float)) or tolerancia < 0
    ):
        raise ErrorConfiguracion(
            "reproducibilidad.tolerancia_metricas debe ser un número no negativo o null."
        )

    return ConfiguracionProyecto(
        raiz=raiz,
        nombre=nombre,
        version_especificacion=version_especificacion,
        rutas=rutas,
        semilla_global=semilla,
        tolerancia_metricas=float(tolerancia) if tolerancia is not None else None,
    )
