"""Lectura de la definición del objetivo en YAML (RF-M1-06; desglose de DP-01).

La definición del proyecto (``config/objetivo/definicion.yaml``) depende de DP-01 y
DP-18 y todavía no existe. ``config/ejemplos/objetivo_ficticio.yaml`` es un ejemplo
inventado y lo declara. Todos los campos son obligatorios: un valor ``null``
significa que la decisión sigue pendiente, y el programa se detiene nombrándola.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

import yaml

from suficiencia.domain.datos.objetivo import (
    Categoria,
    DefinicionObjetivo,
    Efecto,
    FechadoEvento,
    InicioHorizonte,
    PeriodosExtraordinarios,
    PoblacionInicial,
    Reingreso,
    Seguimiento,
    Unidad,
)
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente

VERSION_OBJETIVO_SOPORTADA = 1
ARCHIVO_DEL_PROYECTO = Path("config/objetivo/definicion.yaml")

# Sección del YAML, subcódigo de DP-01 o DP-18 que decide su valor y campos que contiene.
_SECCIONES: dict[str, tuple[str, set[str] | None]] = {
    "evento": ("DP-01a", {"periodos_sin_matricula"}),
    "unidad": ("DP-01b", {"tipo", "columna_carrera"}),
    "poblacion": ("DP-01c", {"inicial", "cohortes"}),
    "horizonte": ("DP-01e", {"periodos", "desde"}),
    "fechado_evento": ("DP-01f", None),
    "pausas": ("DP-01g", {"tratamiento", "limite_periodos"}),
    "retiro_en_periodo": ("DP-01h", None),
    "traslados": ("DP-01i", {"interno", "externo"}),
    "reingreso": ("DP-01j", None),
    "periodos_extraordinarios": ("DP-01k", {"tratamiento", "periodos"}),
    "desenlaces_excluidos": ("DP-01l", None),
    "seguimiento": ("DP-01m", {"exigir", "periodo_sin_registro"}),
    "catalogo_estados": ("DP-01", None),
    "no_etiquetables": ("DP-18", {"tratamiento", "nivel_analisis_sensibilidad"}),
}
_CLAVES = {"version_objetivo", "nombre", "ficticio", *_SECCIONES}

E = TypeVar("E", bound=Enum)


def _error(archivo: Path, causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"{archivo}: {causa}",
        "Corrija la definición del objetivo; el ejemplo válido está en "
        "config/ejemplos/objetivo_ficticio.yaml.",
    )


class _Lector:
    def __init__(self, archivo: Path, datos: dict[str, Any]) -> None:
        self.archivo = archivo
        self.datos = datos

    def seccion(self, nombre: str) -> Any:
        codigo, campos = _SECCIONES[nombre]
        if nombre not in self.datos:
            raise _error(self.archivo, f"falta la sección '{nombre}' ({codigo}).")
        valor = self.datos[nombre]
        if valor is None:
            raise DecisionPendiente(codigo, f"'{nombre}' de la definición del objetivo")
        if campos is None:
            return valor
        if not isinstance(valor, dict):
            raise _error(self.archivo, f"'{nombre}' debe tener los campos {sorted(campos)}.")
        desconocidos = set(valor) - campos
        if desconocidos:
            raise _error(
                self.archivo, f"'{nombre}' tiene campos desconocidos {sorted(desconocidos)}."
            )
        return valor

    def campo(self, seccion: str, campo: str, admite_nulo: bool = False) -> Any:
        valores = self.seccion(seccion)
        if campo not in valores:
            raise _error(self.archivo, f"a '{seccion}' le falta '{campo}'.")
        valor = valores[campo]
        if valor is None and not admite_nulo:
            raise DecisionPendiente(_SECCIONES[seccion][0], f"'{seccion}.{campo}'")
        return valor

    def opcion(self, clase: type[E], valor: Any, donde: str) -> E:
        for miembro in clase:
            if miembro.value == valor:
                return miembro
        permitidos = ", ".join(m.value for m in clase)
        raise _error(self.archivo, f"'{donde}' = {valor!r} no es válido; use uno de: {permitidos}.")

    def efecto(self, valor: Any, donde: str) -> Efecto:
        return self.opcion(Efecto, valor, donde)

    def entero(self, valor: Any, donde: str) -> int:
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise _error(self.archivo, f"'{donde}' debe ser un número entero.")
        return valor


def definicion_desde_datos(archivo: Path, datos: Any) -> DefinicionObjetivo:
    """Valida el contenido ya leído del YAML y construye la definición."""
    if not isinstance(datos, dict):
        raise _error(archivo, "el archivo debe contener un diccionario YAML.")
    desconocidas = set(datos) - _CLAVES
    if desconocidas:
        raise _error(archivo, f"claves desconocidas {sorted(desconocidas)}.")
    if datos.get("version_objetivo") != VERSION_OBJETIVO_SOPORTADA:
        raise _error(archivo, f"'version_objetivo' debe ser {VERSION_OBJETIVO_SOPORTADA}.")
    if not isinstance(datos.get("nombre"), str):
        raise _error(archivo, "'nombre' debe ser un texto.")
    if not isinstance(datos.get("ficticio"), bool):
        raise _error(archivo, "'ficticio' debe ser true o false.")
    lector = _Lector(archivo, datos)

    unidad = lector.opcion(Unidad, lector.campo("unidad", "tipo"), "unidad.tipo")
    columna_carrera = lector.campo("unidad", "columna_carrera", admite_nulo=True)
    if columna_carrera is not None and not isinstance(columna_carrera, str):
        raise _error(archivo, "'unidad.columna_carrera' debe ser el nombre de una columna.")

    cohortes_valor = lector.campo("poblacion", "cohortes")
    cohortes: frozenset[str] | None
    if cohortes_valor == "todas":
        cohortes = None
    elif isinstance(cohortes_valor, list) and all(isinstance(c, str) for c in cohortes_valor):
        cohortes = frozenset(cohortes_valor)
    else:
        raise _error(archivo, "'poblacion.cohortes' debe ser 'todas' o una lista de cohortes.")

    pausas = lector.efecto(lector.campo("pausas", "tratamiento"), "pausas.tratamiento")
    limite_pausas: int | None = None
    if pausas is Efecto.NEUTRAL:
        limite = lector.campo("pausas", "limite_periodos")
        if limite != "sin_limite":
            limite_pausas = lector.entero(limite, "pausas.limite_periodos")
    elif "limite_periodos" in lector.seccion("pausas"):
        raise _error(archivo, "'pausas.limite_periodos' solo se usa con tratamiento 'neutral'.")

    extraordinarios = lector.campo("periodos_extraordinarios", "periodos")
    if not isinstance(extraordinarios, list):
        raise _error(archivo, "'periodos_extraordinarios.periodos' debe ser una lista (o []).")
    lista_extraordinarios = frozenset(
        lector.entero(p, "periodos_extraordinarios.periodos") for p in extraordinarios
    )

    catalogo_valor = lector.seccion("catalogo_estados")
    if not isinstance(catalogo_valor, dict) or not catalogo_valor:
        raise _error(archivo, "'catalogo_estados' debe asociar cada código a una categoría.")
    catalogo = {
        str(codigo): lector.opcion(Categoria, categoria, f"catalogo_estados.{codigo}")
        for codigo, categoria in catalogo_valor.items()
    }

    nivel = lector.campo("no_etiquetables", "nivel_analisis_sensibilidad")
    if isinstance(nivel, bool) or not isinstance(nivel, (int, float)):
        raise _error(archivo, "'no_etiquetables.nivel_analisis_sensibilidad' debe ser un número.")

    try:
        return DefinicionObjetivo(
            nombre=datos["nombre"],
            ficticio=datos["ficticio"],
            periodos_sin_matricula=lector.entero(
                lector.campo("evento", "periodos_sin_matricula"), "evento.periodos_sin_matricula"
            ),
            unidad=unidad,
            columna_carrera=columna_carrera,
            poblacion_inicial=lector.opcion(
                PoblacionInicial, lector.campo("poblacion", "inicial"), "poblacion.inicial"
            ),
            cohortes=cohortes,
            horizonte_periodos=lector.entero(
                lector.campo("horizonte", "periodos"), "horizonte.periodos"
            ),
            horizonte_desde=lector.opcion(
                InicioHorizonte, lector.campo("horizonte", "desde"), "horizonte.desde"
            ),
            fechado=lector.opcion(
                FechadoEvento, lector.seccion("fechado_evento"), "fechado_evento"
            ),
            pausas=pausas,
            limite_pausas=limite_pausas,
            retiro_en_periodo=lector.efecto(
                lector.seccion("retiro_en_periodo"), "retiro_en_periodo"
            ),
            traslado_interno=lector.efecto(
                lector.campo("traslados", "interno"), "traslados.interno"
            ),
            traslado_externo=lector.efecto(
                lector.campo("traslados", "externo"), "traslados.externo"
            ),
            reingreso=lector.opcion(Reingreso, lector.seccion("reingreso"), "reingreso"),
            periodos_extraordinarios=lector.opcion(
                PeriodosExtraordinarios,
                lector.campo("periodos_extraordinarios", "tratamiento"),
                "periodos_extraordinarios.tratamiento",
            ),
            lista_extraordinarios=lista_extraordinarios,
            desenlaces_excluidos=lector.efecto(
                lector.seccion("desenlaces_excluidos"), "desenlaces_excluidos"
            ),
            seguimiento=lector.opcion(
                Seguimiento, lector.campo("seguimiento", "exigir"), "seguimiento.exigir"
            ),
            registro_faltante=lector.efecto(
                lector.campo("seguimiento", "periodo_sin_registro"),
                "seguimiento.periodo_sin_registro",
            ),
            catalogo=catalogo,
            tratamiento_no_etiquetables=str(lector.campo("no_etiquetables", "tratamiento")),
            nivel_sensibilidad=float(nivel),
        )
    except ConfiguracionInvalida as error:
        raise _error(archivo, error.causa) from error


def cargar_definicion_objetivo(archivo: Path) -> DefinicionObjetivo:
    """Lee y valida una definición del objetivo.

    Raises:
        DecisionPendiente: si el archivo del proyecto no existe todavía o un campo es
            ``null`` (DP-01 o DP-18).
        ConfiguracionInvalida: si el archivo no tiene el formato esperado.
    """
    if not archivo.exists():
        if archivo.as_posix().endswith(ARCHIVO_DEL_PROYECTO.as_posix()):
            raise DecisionPendiente(
                "DP-01", f"la definición del objetivo del proyecto ({ARCHIVO_DEL_PROYECTO})"
            )
        raise ConfiguracionInvalida(
            f"No existe el archivo {archivo}.", "Revise la ruta de la definición del objetivo."
        )
    try:
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise _error(archivo, f"no es un YAML válido ({error.__class__.__name__}).") from error
    return definicion_desde_datos(archivo, datos)
