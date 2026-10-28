"""Lectura de ``config/escenarios.yaml`` y de archivos de variables (H2.2).

Implementa los puertos ``FuenteCatalogoVentanas`` y ``FuenteVariables``. La
configuración del repositorio deja las fechas índice en ``null`` (DP-01d) y no
trae variables reales (DP-03). Los ejemplos de ``config/ejemplos/`` se declaran
``ficticio: true`` y nunca representan decisiones ni datos reales.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.modelo import (
    CODIGOS_VENTANA,
    Bloque,
    CatalogoDeclarado,
    CatalogoVentanas,
    Variable,
    VariablesDeclaradas,
    generar_conjuntos,
    validar_variables,
)

VERSION_ESCENARIOS_SOPORTADA = 1
VERSION_VARIABLES_SOPORTADA = 1
_CLAVES_ESCENARIOS = {"version_escenarios", "ficticio", "bloques", "conjuntos", "fechas_indice"}
_CLAVES_VARIABLES = {"version_variables", "ficticio", "variables"}
_CLAVES_VARIABLE = {"nombre", "bloque", "ventana_minima"}


def _error(archivo: Path, causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"{archivo}: {causa}",
        "Corrija el archivo; los ejemplos válidos están en config/ejemplos/.",
    )


def _leer_yaml(archivo: Path, claves: set[str]) -> dict[str, Any]:
    if not archivo.is_file():
        raise ConfiguracionInvalida(
            f"No existe el archivo {archivo}.",
            "Revise la ruta indicada.",
        )
    try:
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise _error(archivo, f"no es YAML válido ({error}).") from error
    if not isinstance(datos, dict):
        raise _error(archivo, "debe contener un diccionario YAML.")
    desconocidas = set(datos) - claves
    faltantes = claves - set(datos)
    if desconocidas:
        raise _error(archivo, f"claves desconocidas {sorted(desconocidas)}.")
    if faltantes:
        raise _error(archivo, f"faltan las claves {sorted(faltantes)}.")
    if not isinstance(datos["ficticio"], bool):
        raise _error(archivo, "'ficticio' debe ser true o false.")
    return datos


def cargar_catalogo(archivo: Path) -> CatalogoDeclarado:
    """Lee el catálogo de ventanas.

    Comprueba además que los bloques y los conjuntos declarados coincidan con los
    definidos en la especificación (RF-M2-02): no pueden cambiarse desde aquí.
    """
    datos = _leer_yaml(archivo, _CLAVES_ESCENARIOS)
    if datos["version_escenarios"] != VERSION_ESCENARIOS_SOPORTADA:
        raise _error(archivo, f"version_escenarios debe ser {VERSION_ESCENARIOS_SOPORTADA}.")

    esperados_bloques = {b.value: b.nombre for b in Bloque}
    if datos["bloques"] != esperados_bloques:
        raise _error(
            archivo,
            f"los bloques deben ser exactamente {esperados_bloques} (DEF de la especificación).",
        )
    esperados_conjuntos = [c.codigo for c in generar_conjuntos()]
    if datos["conjuntos"] != esperados_conjuntos:
        raise _error(
            archivo,
            f"los conjuntos deben ser exactamente {esperados_conjuntos}, en ese orden (RF-M2-02).",
        )

    fechas = datos["fechas_indice"]
    if not isinstance(fechas, dict) or list(fechas) != list(CODIGOS_VENTANA):
        raise _error(archivo, "fechas_indice debe declarar T0, T1, T2 y T3 en ese orden.")
    for codigo, fecha in fechas.items():
        if fecha is not None and (not isinstance(fecha, str) or not fecha.strip()):
            raise _error(archivo, f"la fecha índice de {codigo} debe ser un texto o null.")
    return CatalogoDeclarado(
        catalogo=CatalogoVentanas.desde_fechas_indice(fechas), ficticio=datos["ficticio"]
    )


def cargar_variables(archivo: Path) -> VariablesDeclaradas:
    """Lee las variables candidatas con su bloque y su ventana mínima."""
    datos = _leer_yaml(archivo, _CLAVES_VARIABLES)
    if datos["version_variables"] != VERSION_VARIABLES_SOPORTADA:
        raise _error(archivo, f"version_variables debe ser {VERSION_VARIABLES_SOPORTADA}.")
    entradas = datos["variables"]
    if not isinstance(entradas, list) or not entradas:
        raise _error(archivo, "'variables' debe ser una lista no vacía.")
    variables = []
    for posicion, entrada in enumerate(entradas, start=1):
        if not isinstance(entrada, dict) or set(entrada) != _CLAVES_VARIABLE:
            raise _error(
                archivo,
                f"la variable n.º {posicion} debe tener exactamente "
                "nombre, bloque y ventana_minima.",
            )
        if not all(isinstance(entrada[clave], str) for clave in _CLAVES_VARIABLE):
            raise _error(archivo, f"los campos de la variable n.º {posicion} deben ser textos.")
        variables.append(
            Variable(
                nombre=entrada["nombre"],
                bloque=Bloque.desde_codigo(entrada["bloque"]),
                ventana_minima=entrada["ventana_minima"],
            )
        )
    return VariablesDeclaradas(variables=validar_variables(variables), ficticio=datos["ficticio"])


class FuenteCatalogoYaml:
    """Implementa ``FuenteCatalogoVentanas`` con un archivo YAML."""

    def __init__(self, archivo: Path) -> None:
        self.archivo = archivo

    def cargar(self) -> CatalogoDeclarado:
        return cargar_catalogo(self.archivo)


class FuenteVariablesYaml:
    """Implementa ``FuenteVariables`` con un archivo YAML.

    Si falta el archivo por omisión, la causa es que las variables reales aún no
    están definidas: DP-03 sigue abierta. Si falta un archivo indicado
    explícitamente, es un error de ruta.
    """

    def __init__(self, archivo: Path, *, por_omision: bool = False) -> None:
        self.archivo = archivo
        self.por_omision = por_omision

    def cargar(self) -> VariablesDeclaradas:
        if self.por_omision and not self.archivo.is_file():
            raise DecisionPendiente(
                "DP-03",
                f"el archivo de variables con su bloque y ventana mínima ({self.archivo})",
            )
        return cargar_variables(self.archivo)
