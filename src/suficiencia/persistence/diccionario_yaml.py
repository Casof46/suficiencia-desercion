"""Lectura del diccionario de datos en YAML (RF-M1-02, RF-M1-05).

El diccionario del proyecto depende de DP-03 y DP-15 y todavía no existe. El de
``config/ejemplos/diccionario_sintetico.yaml`` es ficticio y lo declara.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from suficiencia.domain.datos.diccionario import DefinicionVariable, Diccionario, Rol, TipoDato
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.modelo import Bloque, VariablesDeclaradas

VERSION_DICCIONARIO_SOPORTADA = 1
_CLAVES = {"version_diccionario", "nombre", "ficticio", "clave", "variables"}
_CAMPOS_VARIABLE = {
    "nombre",
    "tipo",
    "rol",
    "obligatoria",
    "bloque",
    "ventana_minima",
    "minimo",
    "maximo",
    "valores",
    "patron",
}


def _error(archivo: Path, causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"{archivo}: {causa}",
        "Corrija el diccionario; el ejemplo válido está en "
        "config/ejemplos/diccionario_sintetico.yaml.",
    )


def _enum(archivo: Path, clase: type[TipoDato] | type[Rol], valor: Any, campo: str) -> Any:
    for miembro in clase:
        if miembro.value == valor:
            return miembro
    permitidos = ", ".join(m.value for m in clase)
    raise _error(archivo, f"'{campo}' = {valor!r} no es válido; use uno de: {permitidos}.")


def _numero(archivo: Path, valor: Any, campo: str) -> float | None:
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise _error(archivo, f"'{campo}' debe ser un número.")
    return float(valor)


def _variable(archivo: Path, posicion: int, entrada: Any) -> DefinicionVariable:
    if not isinstance(entrada, dict):
        raise _error(archivo, f"la variable n.º {posicion} debe ser un diccionario.")
    desconocidos = set(entrada) - _CAMPOS_VARIABLE
    if desconocidos:
        raise _error(
            archivo, f"la variable n.º {posicion} tiene campos desconocidos {sorted(desconocidos)}."
        )
    for obligatorio in ("nombre", "tipo", "rol", "obligatoria"):
        if obligatorio not in entrada:
            raise _error(archivo, f"a la variable n.º {posicion} le falta '{obligatorio}'.")
    if not isinstance(entrada["nombre"], str):
        raise _error(archivo, f"el nombre de la variable n.º {posicion} debe ser un texto.")
    if not isinstance(entrada["obligatoria"], bool):
        raise _error(archivo, f"'obligatoria' de '{entrada['nombre']}' debe ser true o false.")
    valores = entrada.get("valores")
    if valores is not None and (
        not isinstance(valores, list) or not all(isinstance(v, str) for v in valores)
    ):
        raise _error(archivo, f"'valores' de '{entrada['nombre']}' debe ser una lista de textos.")
    bloque = entrada.get("bloque")
    ventana = entrada.get("ventana_minima")
    patron = entrada.get("patron")
    if patron is not None and not isinstance(patron, str):
        raise _error(archivo, f"'patron' de '{entrada['nombre']}' debe ser un texto.")
    return DefinicionVariable(
        nombre=entrada["nombre"],
        tipo=_enum(archivo, TipoDato, entrada["tipo"], "tipo"),
        rol=_enum(archivo, Rol, entrada["rol"], "rol"),
        obligatoria=entrada["obligatoria"],
        bloque=Bloque.desde_codigo(bloque) if bloque is not None else None,
        ventana_minima=str(ventana) if ventana is not None else None,
        minimo=_numero(archivo, entrada.get("minimo"), "minimo"),
        maximo=_numero(archivo, entrada.get("maximo"), "maximo"),
        valores=tuple(valores) if valores is not None else None,
        patron=patron,
    )


def cargar_diccionario(archivo: Path) -> Diccionario:
    if not archivo.is_file():
        raise ConfiguracionInvalida(f"No existe el archivo {archivo}.", "Revise la ruta indicada.")
    try:
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise _error(archivo, f"no es YAML válido ({error}).") from error
    if not isinstance(datos, dict):
        raise _error(archivo, "debe contener un diccionario YAML.")
    desconocidas = set(datos) - _CLAVES
    faltantes = _CLAVES - set(datos)
    if desconocidas:
        raise _error(archivo, f"claves desconocidas {sorted(desconocidas)}.")
    if faltantes:
        raise _error(archivo, f"faltan las claves {sorted(faltantes)}.")
    if datos["version_diccionario"] != VERSION_DICCIONARIO_SOPORTADA:
        raise _error(archivo, f"version_diccionario debe ser {VERSION_DICCIONARIO_SOPORTADA}.")
    if not isinstance(datos["ficticio"], bool):
        raise _error(archivo, "'ficticio' debe ser true o false.")
    if not isinstance(datos["nombre"], str) or not datos["nombre"].strip():
        raise _error(archivo, "'nombre' debe ser un texto no vacío.")
    clave = datos["clave"]
    if not isinstance(clave, list) or not all(isinstance(c, str) for c in clave):
        raise _error(archivo, "'clave' debe ser una lista de nombres de columna.")
    variables = datos["variables"]
    if not isinstance(variables, list):
        raise _error(archivo, "'variables' debe ser una lista.")
    try:
        return Diccionario(
            nombre=datos["nombre"],
            ficticio=datos["ficticio"],
            variables=tuple(_variable(archivo, i, v) for i, v in enumerate(variables, start=1)),
            clave=tuple(clave),
        )
    except ConfiguracionInvalida as error:
        if str(archivo) in error.causa:
            raise
        raise _error(archivo, error.causa) from error


class FuenteVariablesDiccionario:
    """Implementa ``FuenteVariables`` con los rasgos de un diccionario (H2.3).

    Sin diccionario del proyecto, la causa es DP-03.
    """

    def __init__(self, archivo: Path, *, por_omision: bool = False) -> None:
        self.archivo = archivo
        self.por_omision = por_omision

    def cargar(self) -> VariablesDeclaradas:
        if self.por_omision and not self.archivo.is_file():
            raise DecisionPendiente(
                "DP-03", f"el diccionario de variables del proyecto ({self.archivo})"
            )
        diccionario = cargar_diccionario(self.archivo)
        return VariablesDeclaradas(
            variables=diccionario.variables_de_escenario(), ficticio=diccionario.ficticio
        )
