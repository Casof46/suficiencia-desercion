"""Interpretabilidad de las configuraciones congeladas (M5; RF-M5-01 a 05; F3.6).

- **Alcance** (DP-11): qué se explica (solo la configuración del escenario suficiente o
  todas las congeladas), con qué niveles (global, por bloque, local), sobre qué
  partición y con qué tamaños de muestra. Todo es dato obligatorio.
- **Explicador según el modelo** (RF-M5-03): lineal para la regresión logística,
  de árboles para Random Forest, XGBoost y LightGBM, y kernel con muestra de fondo
  para SVM.
- **Agregación** (RF-M5-04): la contribución de una variable es la suma de las de sus
  columnas preprocesadas (por ejemplo, las columnas 0/1 de una categoría); la
  importancia global de una variable es el promedio del valor absoluto de su
  contribución; la de un bloque es la suma exacta de las de sus variables (PU-21).
- **Trazabilidad** (RF-M5-05): la partición, las muestras y la semilla se calculan
  aquí y quedan en el registro de cada explicación (PI-13).

Las explicaciones describen asociaciones del modelo, no causas (invariante de M5).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Interpretabilidad: {causa}",
        "Corrija la configuración; el ejemplo válido está en "
        "config/ejemplos/experimentos_ficticio.yaml.",
    )


def _campo(datos: Mapping[str, Any], clave: str, donde: str) -> Any:
    if clave not in datos:
        raise _invalida(f"falta '{clave}' en {donde} (DP-11).")
    if datos[clave] is None:
        raise DecisionPendiente("DP-11", f"'{clave}' en {donde}")
    return datos[clave]


def _entero(valor: Any, campo: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        raise _invalida(f"'{campo}' debe ser un entero mayor o igual que 1.")
    return valor


# --- Alcance (DP-11) -----------------------------------------------------------------


class AlcanceInterpretabilidad(Enum):
    ESCENARIO_SUFICIENTE = "escenario_suficiente"
    TODAS_CONGELADAS = "todas_congeladas"


class NivelExplicacion(Enum):
    GLOBAL = "global"
    BLOQUE = "bloque"
    LOCAL = "local"


class ParticionExplicacion(Enum):
    """Filas que se explican. Solo el desarrollo: explicar con la prueba sería otro
    acceso a ella (PI-15)."""

    DESARROLLO = "desarrollo"


@dataclass(frozen=True)
class DefinicionLocal:
    """Explicaciones locales SHAP y LIME (RF-M5-02)."""

    registros: int
    variables: int
    lime_muestras: int


@dataclass(frozen=True)
class DefinicionInterpretabilidad:
    alcance: AlcanceInterpretabilidad
    niveles: tuple[NivelExplicacion, ...]
    particion: ParticionExplicacion
    muestra_fondo: int
    muestra_explicar: int
    kernel_muestras: int
    local: DefinicionLocal | None


_CLAVES = {
    "alcance",
    "niveles",
    "particion",
    "muestra_fondo",
    "muestra_explicar",
    "kernel_muestras",
    "local",
}


def definicion_interpretabilidad_desde_datos(datos: Any) -> DefinicionInterpretabilidad:
    """Lee la sección ``interpretabilidad`` (DP-11).

    Raises:
        DecisionPendiente: si la sección o un campo vale ``null``.
        ConfiguracionInvalida: si la estructura no es válida.
    """
    if datos is None:
        raise DecisionPendiente("DP-11", "la sección 'interpretabilidad' de la configuración")
    if not isinstance(datos, Mapping):
        raise _invalida("'interpretabilidad' debe ser un conjunto de campos.")
    extra = sorted(set(datos) - _CLAVES)
    if extra:
        raise _invalida(f"campos desconocidos en 'interpretabilidad': {', '.join(extra)}.")
    donde = "interpretabilidad"
    try:
        alcance = AlcanceInterpretabilidad(_campo(datos, "alcance", donde))
    except ValueError:
        opciones = ", ".join(a.value for a in AlcanceInterpretabilidad)
        raise _invalida(f"'alcance' debe ser uno de: {opciones}.") from None
    try:
        particion = ParticionExplicacion(_campo(datos, "particion", donde))
    except ValueError:
        raise _invalida(
            "'particion' debe ser desarrollo: explicar con la prueba sería un nuevo acceso a ella."
        ) from None
    leidos = _campo(datos, "niveles", donde)
    if not isinstance(leidos, list) or not leidos:
        raise _invalida("'niveles' debe ser una lista con al menos un nivel.")
    try:
        niveles = tuple(NivelExplicacion(n) for n in leidos)
    except ValueError:
        opciones = ", ".join(n.value for n in NivelExplicacion)
        raise _invalida(f"cada nivel debe ser uno de: {opciones}.") from None
    if len(set(niveles)) != len(niveles):
        raise _invalida("'niveles' tiene niveles repetidos.")
    if NivelExplicacion.BLOQUE in niveles and NivelExplicacion.GLOBAL not in niveles:
        raise _invalida(
            "la importancia por bloque se calcula con la global: incluya también 'global'."
        )
    local = None
    if NivelExplicacion.LOCAL in niveles:
        datos_local = _campo(datos, "local", donde)
        if not isinstance(datos_local, Mapping):
            raise _invalida("'local' debe ser un conjunto de campos.")
        extra = sorted(set(datos_local) - {"registros", "variables", "lime_muestras"})
        if extra:
            raise _invalida(f"campos desconocidos en 'local': {', '.join(extra)}.")
        local = DefinicionLocal(
            registros=_entero(_campo(datos_local, "registros", "local"), "local.registros"),
            variables=_entero(_campo(datos_local, "variables", "local"), "local.variables"),
            lime_muestras=_entero(
                _campo(datos_local, "lime_muestras", "local"), "local.lime_muestras"
            ),
        )
    elif "local" in datos:
        raise _invalida("'local' solo se indica si 'niveles' incluye local.")
    definicion = DefinicionInterpretabilidad(
        alcance=alcance,
        niveles=niveles,
        particion=particion,
        muestra_fondo=_entero(_campo(datos, "muestra_fondo", donde), "muestra_fondo"),
        muestra_explicar=_entero(_campo(datos, "muestra_explicar", donde), "muestra_explicar"),
        kernel_muestras=_entero(_campo(datos, "kernel_muestras", donde), "kernel_muestras"),
        local=local,
    )
    if local is not None and local.registros > definicion.muestra_explicar:
        raise _invalida("'local.registros' no puede superar 'muestra_explicar'.")
    return definicion


# --- Explicador según el modelo (RF-M5-03) -------------------------------------------


class TipoExplicador(Enum):
    LINEAL = "lineal"
    ARBOLES = "arboles"
    KERNEL = "kernel"


class Escala(Enum):
    """Unidad de las contribuciones SHAP: la salida del modelo antes de la calibración."""

    LOG_ODDS = "log_odds"
    PROBABILIDAD = "probabilidad"
    MARGEN = "margen"


_EXPLICADORES = {
    "lr": (TipoExplicador.LINEAL, Escala.LOG_ODDS),
    "rf": (TipoExplicador.ARBOLES, Escala.PROBABILIDAD),
    "xgboost": (TipoExplicador.ARBOLES, Escala.LOG_ODDS),
    "lightgbm": (TipoExplicador.ARBOLES, Escala.LOG_ODDS),
    "svm": (TipoExplicador.KERNEL, Escala.MARGEN),
}


def explicador_para(familia: str) -> tuple[TipoExplicador, Escala]:
    """Explicador SHAP y escala de sus contribuciones para una familia (RF-M5-03).

    Raises:
        ConfiguracionInvalida: si la familia no es una de las cinco.
    """
    try:
        return _EXPLICADORES[familia]
    except KeyError:
        raise _invalida(f"no hay explicador para la familia '{familia}'.") from None


# --- Muestras (RF-M5-05) -------------------------------------------------------------


@dataclass(frozen=True)
class Muestras:
    """Posiciones de las filas de la partición declarada que usa una explicación."""

    fondo: tuple[int, ...]
    explicar: tuple[int, ...]
    locales: tuple[int, ...]
    """Posiciones dentro de ``explicar`` de los registros con explicación local."""


def elegir_muestras(total: int, fondo: int, explicar: int, locales: int, semilla: int) -> Muestras:
    """Elige sin reemplazo las filas de fondo, las que se explican y las locales.

    Con la misma semilla y el mismo total, siempre las mismas. Si una muestra pide más
    filas de las que hay, usa todas.

    Raises:
        ConfiguracionInvalida: si la partición no tiene filas.
    """
    if total < 1:
        raise _invalida("la partición declarada no tiene filas que explicar.")
    generador = np.random.default_rng(semilla)

    def elegir(cuantas: int) -> tuple[int, ...]:
        if cuantas >= total:
            return tuple(range(total))
        return tuple(sorted(int(i) for i in generador.choice(total, size=cuantas, replace=False)))

    fondo_elegido = elegir(fondo)
    explicar_elegido = elegir(explicar)
    cuantas_locales = min(locales, len(explicar_elegido))
    locales_elegidos = tuple(
        sorted(
            int(i)
            for i in generador.choice(len(explicar_elegido), size=cuantas_locales, replace=False)
        )
    )
    return Muestras(fondo_elegido, explicar_elegido, locales_elegidos)


# --- Agregación (RF-M5-04) -----------------------------------------------------------


def valores_por_variable(
    valores: np.ndarray, variable_de_columna: Sequence[str], variables: Sequence[str]
) -> np.ndarray:
    """Suma las contribuciones de las columnas preprocesadas de cada variable.

    Devuelve una matriz filas × ``variables``. Una variable sin columnas (el
    preprocesamiento la descartó) contribuye cero.

    Raises:
        ConfiguracionInvalida: si las dimensiones no coinciden o una columna no
            pertenece a ninguna de las variables.
    """
    matriz = np.asarray(valores, dtype="float64")
    if matriz.ndim != 2 or matriz.shape[1] != len(variable_de_columna):
        raise _invalida("las contribuciones no tienen una columna por columna preprocesada.")
    posicion = {v: i for i, v in enumerate(variables)}
    desconocidas = sorted({v for v in variable_de_columna if v not in posicion})
    if desconocidas:
        raise _invalida(f"columnas de variables desconocidas: {', '.join(desconocidas)}.")
    salida = np.zeros((matriz.shape[0], len(variables)), dtype="float64")
    for columna, variable in enumerate(variable_de_columna):
        salida[:, posicion[variable]] += matriz[:, columna]
    return salida


def importancia_global(valores: np.ndarray, variables: Sequence[str]) -> dict[str, float]:
    """Promedio del valor absoluto de la contribución de cada variable (RF-M5-01)."""
    matriz = np.asarray(valores, dtype="float64")
    if matriz.ndim != 2 or matriz.shape[1] != len(variables) or matriz.shape[0] < 1:
        raise _invalida("se necesita al menos una fila y una columna por variable.")
    promedio = np.abs(matriz).mean(axis=0)
    return {v: float(promedio[i]) for i, v in enumerate(variables)}


def importancia_por_bloque(
    importancias: Mapping[str, float], bloque_de: Mapping[str, str], orden: Sequence[str]
) -> dict[str, float]:
    """Importancia de cada bloque: la suma exacta de las de sus variables (PU-21).

    Solo aparecen los bloques que tienen variables, en el orden de ``orden``.

    Raises:
        ConfiguracionInvalida: si una variable no tiene bloque o su bloque no está en
            ``orden``.
    """
    sin_bloque = sorted(v for v in importancias if v not in bloque_de)
    if sin_bloque:
        raise _invalida(f"variables sin bloque: {', '.join(sin_bloque)}.")
    fuera = sorted({bloque_de[v] for v in importancias} - set(orden))
    if fuera:
        raise _invalida(f"bloques desconocidos: {', '.join(fuera)}.")
    sumas: dict[str, float] = {}
    for bloque in orden:
        miembros = [importancias[v] for v in importancias if bloque_de[v] == bloque]
        if miembros:
            sumas[bloque] = float(sum(miembros))
    return sumas


def principales(contribuciones: Mapping[str, float], cuantas: int) -> tuple[tuple[str, float], ...]:
    """Las ``cuantas`` contribuciones de mayor valor absoluto; empates por orden de llegada."""
    ordenadas = sorted(enumerate(contribuciones.items()), key=lambda par: (-abs(par[1][1]), par[0]))
    return tuple((nombre, float(valor)) for _, (nombre, valor) in ordenadas[:cuantas])
