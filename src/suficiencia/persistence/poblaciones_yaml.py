"""Lectura de la configuración de poblaciones y partición en YAML (RF-M2-05 a RF-M2-08).

La configuración del proyecto (``config/poblaciones.yaml``) depende de DP-01d,
DP-04, DP-05 y DP-17 y todavía no existe. El ejemplo de
``config/ejemplos/poblaciones_ficticio.yaml`` es inventado y lo declara. Todos los
campos son obligatorios; un valor ``null`` detiene el programa nombrando la
decisión pendiente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.particion import DefinicionParticion
from suficiencia.domain.escenarios.poblaciones import (
    ConfiguracionPoblaciones,
    Diseno,
    PeriodosIndice,
)

VERSION_POBLACIONES_SOPORTADA = 1
ARCHIVO_DEL_PROYECTO = Path("config/poblaciones.yaml")
_CLAVES = {
    "version_poblaciones",
    "nombre",
    "ficticio",
    "periodo_indice",
    "diseno_principal",
    "analisis_complementarios",
    "particion",
}
_CAMPOS_PARTICION = {
    "cohortes_desarrollo",
    "cohortes_prueba",
    "cohortes_piloto",
    "cohortes_excluidas",
    "plan_contingencia",
}


def _error(archivo: Path, causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"{archivo}: {causa}",
        "Corrija la configuración; el ejemplo válido está en "
        "config/ejemplos/poblaciones_ficticio.yaml.",
    )


def _requerido(archivo: Path, datos: dict[str, Any], clave: str, decision: str) -> Any:
    if clave not in datos:
        raise _error(archivo, f"falta '{clave}' ({decision}).")
    if datos[clave] is None:
        raise DecisionPendiente(decision, f"'{clave}' de la configuración de poblaciones")
    return datos[clave]


def _diseno(archivo: Path, valor: Any, donde: str) -> Diseno:
    for diseno in Diseno:
        if diseno.value == valor:
            return diseno
    raise _error(archivo, f"'{donde}' = {valor!r} no es válido; use D1, D2 o D3.")


def _cohortes(archivo: Path, particion: dict[str, Any], campo: str) -> frozenset[str]:
    valor = _requerido(archivo, particion, campo, "DP-05")
    if not isinstance(valor, list) or not all(isinstance(c, str) for c in valor):
        raise _error(archivo, f"'particion.{campo}' debe ser una lista de cohortes (o []).")
    return frozenset(valor)


def configuracion_desde_datos(archivo: Path, datos: Any) -> ConfiguracionPoblaciones:
    """Valida el contenido ya leído del YAML."""
    if not isinstance(datos, dict):
        raise _error(archivo, "el archivo debe contener un diccionario YAML.")
    desconocidas = set(datos) - _CLAVES
    if desconocidas:
        raise _error(archivo, f"claves desconocidas {sorted(desconocidas)}.")
    if datos.get("version_poblaciones") != VERSION_POBLACIONES_SOPORTADA:
        raise _error(archivo, f"'version_poblaciones' debe ser {VERSION_POBLACIONES_SOPORTADA}.")
    if not isinstance(datos.get("nombre"), str) or not isinstance(datos.get("ficticio"), bool):
        raise _error(archivo, "'nombre' debe ser un texto y 'ficticio', true o false.")

    indices = _requerido(archivo, datos, "periodo_indice", "DP-01d")
    if not isinstance(indices, dict):
        raise _error(archivo, "'periodo_indice' debe asociar cada ventana a un periodo.")
    for ventana, periodo in indices.items():
        if periodo is None:
            raise DecisionPendiente("DP-01d", f"el periodo índice de la ventana {ventana}")

    principal = _diseno(
        archivo, _requerido(archivo, datos, "diseno_principal", "DP-04"), "diseno_principal"
    )
    complementarios_valor = _requerido(archivo, datos, "analisis_complementarios", "DP-17")
    if not isinstance(complementarios_valor, list):
        raise _error(archivo, "'analisis_complementarios' debe ser una lista (o []).")
    complementarios = frozenset(
        _diseno(archivo, d, "analisis_complementarios") for d in complementarios_valor
    )

    particion = _requerido(archivo, datos, "particion", "DP-05")
    if not isinstance(particion, dict):
        raise _error(archivo, f"'particion' debe tener los campos {sorted(_CAMPOS_PARTICION)}.")
    desconocidos = set(particion) - _CAMPOS_PARTICION
    if desconocidos:
        raise _error(archivo, f"'particion' tiene campos desconocidos {sorted(desconocidos)}.")
    plan = _requerido(archivo, particion, "plan_contingencia", "DP-05")
    if not isinstance(plan, str):
        raise _error(archivo, "'particion.plan_contingencia' debe ser un texto.")

    try:
        return ConfiguracionPoblaciones(
            nombre=datos["nombre"],
            ficticio=datos["ficticio"],
            indices=PeriodosIndice(dict(indices)),
            diseno_principal=principal,
            complementarios=complementarios,
            particion=DefinicionParticion(
                desarrollo=_cohortes(archivo, particion, "cohortes_desarrollo"),
                prueba=_cohortes(archivo, particion, "cohortes_prueba"),
                piloto=_cohortes(archivo, particion, "cohortes_piloto"),
                excluidas=_cohortes(archivo, particion, "cohortes_excluidas"),
                plan_contingencia=plan,
            ),
        )
    except ConfiguracionInvalida as error:
        raise _error(archivo, error.causa) from error


def cargar_configuracion_poblaciones(archivo: Path) -> ConfiguracionPoblaciones:
    """Lee y valida la configuración de poblaciones y partición.

    Raises:
        DecisionPendiente: si el archivo del proyecto no existe o un campo es ``null``.
        ConfiguracionInvalida: si el archivo no tiene el formato esperado.
    """
    if not archivo.exists():
        if archivo.as_posix().endswith(ARCHIVO_DEL_PROYECTO.as_posix()):
            raise DecisionPendiente(
                "DP-04", f"la configuración de poblaciones y partición ({ARCHIVO_DEL_PROYECTO})"
            )
        raise ConfiguracionInvalida(
            f"No existe el archivo {archivo}.", "Revise la ruta de la configuración de poblaciones."
        )
    try:
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise _error(archivo, f"no es un YAML válido ({error.__class__.__name__}).") from error
    return configuracion_desde_datos(archivo, datos)
