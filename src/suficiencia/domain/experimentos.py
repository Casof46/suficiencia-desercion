"""Configuración de los experimentos de desarrollo (M3; F3.1).

Reúne lo que el desarrollo necesita decidir y todavía no está decidido, siempre
como datos obligatorios sin valor por omisión:

- **Validación interna cronológica** (DP-07): folds rolling-origin por cohortes.
  Cada fold valida con una cohorte posterior a todas las de su ajuste y su
  calibración (RF-M3-03, PI-07). Los folds dependen solo de las cohortes de
  desarrollo, así que todos los escenarios usan los mismos (PI-08).
- **Lectura de las variables en el corte** (DP-03): ver ``escenarios.matrices``.
- **Preprocesamiento** (DP-12): perfiles con nombre (imputación, indicador de
  faltante, escalado y tratamiento de categorías). Se ajustan dentro de cada fold
  en la capa de experimentación (RF-M3-02).

Un valor ``null`` detiene el programa nombrando la decisión pendiente.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.matrices import (
    DefinicionMatrices,
    definicion_matrices_desde_datos,
)


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Configuración de experimentos: {causa}",
        "Corrija la configuración; el ejemplo válido está en "
        "config/ejemplos/experimentos_ficticio.yaml.",
    )


def _campo(datos: Mapping[str, Any], clave: str, decision: str, donde: str) -> Any:
    if clave not in datos:
        raise _invalida(f"falta '{clave}' en {donde} ({decision}).")
    if datos[clave] is None:
        raise DecisionPendiente(decision, f"'{clave}' en {donde}")
    return datos[clave]


def _enum(tipo: type[Any], valor: Any, campo: str) -> Any:
    try:
        return tipo(valor)
    except ValueError:
        opciones = ", ".join(e.value for e in tipo)
        raise _invalida(f"'{campo}' = {valor!r} no es válido. Opciones: {opciones}.") from None


def _entero(valor: Any, campo: str, minimo: int) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
        raise _invalida(f"'{campo}' debe ser un entero mayor o igual que {minimo}.")
    return valor


def _sin_extra(datos: Mapping[str, Any], validas: set[str], donde: str) -> None:
    extra = sorted(set(datos) - validas)
    if extra:
        raise _invalida(f"campos desconocidos en {donde}: {', '.join(extra)}.")


# --- Validación cronológica (DP-07) ------------------------------------------------


class Esquema(Enum):
    EXPANSIVO = "expansivo"
    DESLIZANTE = "deslizante"


@dataclass(frozen=True)
class DefinicionValidacion:
    """Folds rolling-origin por cohortes.

    ``cohortes_iniciales`` es cuántas cohortes de desarrollo hay antes de la primera
    cohorte de validación. Con ``cohorte_calibracion``, la cohorte inmediatamente
    anterior a la de validación se reserva para la búsqueda de hiperparámetros y la
    calibración, y no se usa para ajustar. Con el esquema deslizante, ``ancho`` es
    cuántas cohortes de ajuste se usan; con el expansivo, se usan todas las
    anteriores y ``ancho`` no se admite.
    """

    esquema: Esquema
    cohortes_iniciales: int
    cohorte_calibracion: bool
    ancho: int | None

    def __post_init__(self) -> None:
        reservadas = 1 if self.cohorte_calibracion else 0
        if self.cohortes_iniciales - reservadas < 1:
            raise _invalida("el primer fold no tendría ninguna cohorte de ajuste.")
        if self.esquema is Esquema.EXPANSIVO and self.ancho is not None:
            raise _invalida("el esquema expansivo no lleva 'ancho'.")
        if self.esquema is Esquema.DESLIZANTE:
            if self.ancho is None:
                raise _invalida("el esquema deslizante necesita 'ancho'.")
            if self.ancho > self.cohortes_iniciales - reservadas:
                raise _invalida("el primer fold no tendría tantas cohortes de ajuste como 'ancho'.")


_CAMPOS_VALIDACION = {"esquema", "cohortes_iniciales", "cohorte_calibracion", "ancho"}


def definicion_validacion_desde_datos(datos: Any) -> DefinicionValidacion:
    if datos is None:
        raise DecisionPendiente("DP-07", "la sección 'validacion' de la configuración")
    if not isinstance(datos, Mapping):
        raise _invalida("'validacion' debe ser un conjunto de campos.")
    _sin_extra(datos, _CAMPOS_VALIDACION, "validacion")
    esquema = _enum(Esquema, _campo(datos, "esquema", "DP-07", "validacion"), "esquema")
    calibracion = _campo(datos, "cohorte_calibracion", "DP-07", "validacion")
    if not isinstance(calibracion, bool):
        raise _invalida("'cohorte_calibracion' debe ser sí o no.")
    ancho = None
    if esquema is Esquema.DESLIZANTE:
        ancho = _entero(_campo(datos, "ancho", "DP-07", "validacion"), "ancho", 1)
    elif "ancho" in datos:
        raise _invalida("el esquema expansivo no lleva 'ancho'.")
    return DefinicionValidacion(
        esquema=esquema,
        cohortes_iniciales=_entero(
            _campo(datos, "cohortes_iniciales", "DP-07", "validacion"), "cohortes_iniciales", 1
        ),
        cohorte_calibracion=calibracion,
        ancho=ancho,
    )


@dataclass(frozen=True)
class Fold:
    """Un fold de la validación cronológica."""

    numero: int
    ajuste: tuple[str, ...]
    calibracion: tuple[str, ...]
    validacion: str


def construir_folds(
    cohortes_desarrollo: Sequence[str], definicion: DefinicionValidacion
) -> tuple[Fold, ...]:
    """Folds rolling-origin sobre las cohortes de desarrollo (RF-M3-03).

    Las cohortes se ordenan cronológicamente como texto (``2010-1`` < ``2010-2``).

    Raises:
        ConfiguracionInvalida: si no alcanza para ningún fold.
    """
    cohortes = sorted(set(cohortes_desarrollo))
    cantidad = len(cohortes) - definicion.cohortes_iniciales
    if cantidad < 1:
        raise _invalida(
            f"con {len(cohortes)} cohortes de desarrollo y {definicion.cohortes_iniciales} "
            "iniciales no queda ninguna cohorte de validación."
        )
    folds = []
    for numero in range(1, cantidad + 1):
        posicion = definicion.cohortes_iniciales + numero - 1  # índice desde 0
        anteriores = cohortes[:posicion]
        calibracion = tuple(anteriores[-1:]) if definicion.cohorte_calibracion else ()
        disponibles = anteriores[:-1] if definicion.cohorte_calibracion else anteriores
        ajuste = (
            disponibles[-definicion.ancho :]
            if definicion.esquema is Esquema.DESLIZANTE and definicion.ancho is not None
            else disponibles
        )
        folds.append(
            Fold(
                numero=numero,
                ajuste=tuple(ajuste),
                calibracion=calibracion,
                validacion=cohortes[posicion],
            )
        )
    return tuple(folds)


# --- Preprocesamiento (DP-12) ------------------------------------------------------


class ImputacionNumerica(Enum):
    MEDIANA = "mediana"
    MEDIA = "media"


class Escalado(Enum):
    ESTANDAR = "estandar"
    NINGUNO = "ninguno"


class ImputacionCategorica(Enum):
    MAS_FRECUENTE = "mas_frecuente"
    CATEGORIA_FALTANTE = "categoria_faltante"


@dataclass(frozen=True)
class PerfilPreprocesamiento:
    """Preprocesamiento de un tipo de modelo; se ajusta solo con el ajuste de cada fold.

    Las variables numéricas y lógicas se imputan y, si corresponde, se escalan; con
    ``indicador_faltante`` se añade una columna 0/1 por variable con faltantes en el
    ajuste. Las categóricas se imputan y se codifican en columnas 0/1 (one-hot); una
    categoría que no estaba en el ajuste queda en cero.
    """

    nombre: str
    imputacion_numerica: ImputacionNumerica
    indicador_faltante: bool
    escalado: Escalado
    imputacion_categorica: ImputacionCategorica


_CAMPOS_PERFIL = {"imputacion_numerica", "indicador_faltante", "escalado", "imputacion_categorica"}


def _perfil(nombre: str, datos: Any) -> PerfilPreprocesamiento:
    donde = f"el perfil '{nombre}'"
    if datos is None:
        raise DecisionPendiente("DP-12", donde)
    if not isinstance(datos, Mapping):
        raise _invalida(f"{donde} debe ser un conjunto de campos.")
    _sin_extra(datos, _CAMPOS_PERFIL, donde)
    indicador = _campo(datos, "indicador_faltante", "DP-12", donde)
    if not isinstance(indicador, bool):
        raise _invalida(f"'indicador_faltante' de {donde} debe ser sí o no.")
    return PerfilPreprocesamiento(
        nombre=nombre,
        imputacion_numerica=_enum(
            ImputacionNumerica,
            _campo(datos, "imputacion_numerica", "DP-12", donde),
            "imputacion_numerica",
        ),
        indicador_faltante=indicador,
        escalado=_enum(Escalado, _campo(datos, "escalado", "DP-12", donde), "escalado"),
        imputacion_categorica=_enum(
            ImputacionCategorica,
            _campo(datos, "imputacion_categorica", "DP-12", donde),
            "imputacion_categorica",
        ),
    )


# --- Configuración completa --------------------------------------------------------


@dataclass(frozen=True)
class ConfiguracionExperimentos:
    nombre: str
    ficticio: bool
    validacion: DefinicionValidacion
    matrices: DefinicionMatrices
    perfiles: Mapping[str, PerfilPreprocesamiento]


_CLAVES = {
    "version_experimentos",
    "nombre",
    "ficticio",
    "validacion",
    "matrices",
    "preprocesamiento",
}
VERSION_SOPORTADA = 1


def configuracion_experimentos_desde_datos(datos: Any) -> ConfiguracionExperimentos:
    """Lee la configuración de experimentos (YAML ya cargado).

    Raises:
        DecisionPendiente: si una sección o un campo vale ``null``.
        ConfiguracionInvalida: si la estructura no es válida.
    """
    if not isinstance(datos, Mapping):
        raise _invalida("el archivo debe ser un conjunto de campos.")
    _sin_extra(datos, _CLAVES, "el archivo")
    faltan = sorted(_CLAVES - set(datos))
    if faltan:
        raise _invalida(f"faltan los campos: {', '.join(faltan)}.")
    if datos["version_experimentos"] != VERSION_SOPORTADA:
        raise _invalida(f"'version_experimentos' debe ser {VERSION_SOPORTADA}.")
    if not isinstance(datos["nombre"], str) or not datos["nombre"].strip():
        raise _invalida("'nombre' no puede estar vacío.")
    if not isinstance(datos["ficticio"], bool):
        raise _invalida("'ficticio' debe ser sí o no.")
    preprocesamiento = datos["preprocesamiento"]
    if preprocesamiento is None:
        raise DecisionPendiente("DP-12", "la sección 'preprocesamiento' de la configuración")
    if not isinstance(preprocesamiento, Mapping) or set(preprocesamiento) != {"perfiles"}:
        raise _invalida("'preprocesamiento' debe tener exactamente el campo 'perfiles'.")
    perfiles = preprocesamiento["perfiles"]
    if not isinstance(perfiles, Mapping) or not perfiles:
        raise _invalida("'preprocesamiento.perfiles' debe definir al menos un perfil.")
    return ConfiguracionExperimentos(
        nombre=datos["nombre"].strip(),
        ficticio=datos["ficticio"],
        validacion=definicion_validacion_desde_datos(datos["validacion"]),
        matrices=definicion_matrices_desde_datos(datos["matrices"]),
        perfiles={str(n): _perfil(str(n), p) for n, p in perfiles.items()},
    )
