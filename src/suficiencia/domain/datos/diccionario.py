"""Diccionario de datos: tipo, rol, obligatoriedad y dominio de cada columna (RF-M1-02).

Cada variable con rol ``rasgo`` (candidata a predictor) tiene exactamente un
bloque y una ventana mínima (RF-M1-05, PU-16). Las demás columnas no pueden
tenerlos: así una columna del objetivo o un identificador nunca llega a un
escenario por error.

El diccionario real depende de DP-03 y DP-15. Hasta entonces solo existen
diccionarios de ejemplo declarados ``ficticio``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.modelo import Bloque, Variable, orden_ventana

COLUMNA_SEUDONIMO = "seudonimo"
"""Columna que reemplaza a los identificadores tras la seudonimización."""

VALOR_ORIGEN_SINTETICO = "SINTETICO"


class TipoDato(Enum):
    ENTERO = "entero"
    DECIMAL = "decimal"
    TEXTO = "texto"
    CODIGO = "codigo"
    CATEGORIA = "categoria"
    BOOLEANO = "booleano"
    FECHA = "fecha"


class Rol(Enum):
    """Rol de una columna.

    La especificación nombra identificador, rasgo, objetivo, cohorte y fecha.
    H2.3 añade ``periodo`` (ciclo del historial de matrícula, RF-M1-11) y
    ``origen`` (marca de datos sintéticos), decisión D-43.
    """

    IDENTIFICADOR = "identificador"
    RASGO = "rasgo"
    OBJETIVO = "objetivo"
    COHORTE = "cohorte"
    FECHA = "fecha"
    PERIODO = "periodo"
    ORIGEN = "origen"


_TIPOS_CON_RANGO = {TipoDato.ENTERO, TipoDato.DECIMAL}
_TIPOS_CON_PATRON = {TipoDato.TEXTO, TipoDato.CODIGO}


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Diccionario de datos: {causa}",
        "Corrija el diccionario; el ejemplo válido está en config/ejemplos/.",
    )


@dataclass(frozen=True)
class DefinicionVariable:
    """Una columna del dataset según el diccionario."""

    nombre: str
    tipo: TipoDato
    rol: Rol
    obligatoria: bool
    bloque: Bloque | None = None
    ventana_minima: str | None = None
    minimo: float | None = None
    maximo: float | None = None
    valores: tuple[str, ...] | None = None
    patron: str | None = None

    def __post_init__(self) -> None:
        nombre = self.nombre
        if not nombre.strip():
            raise _invalida("hay una variable sin nombre.")
        if nombre == COLUMNA_SEUDONIMO:
            raise _invalida(f"'{COLUMNA_SEUDONIMO}' es un nombre reservado.")

        es_rasgo = self.rol is Rol.RASGO
        if es_rasgo and (self.bloque is None or self.ventana_minima is None):
            raise _invalida(f"la variable '{nombre}' es un rasgo y necesita bloque y ventana.")
        if not es_rasgo and (self.bloque is not None or self.ventana_minima is not None):
            raise _invalida(
                f"la variable '{nombre}' tiene rol {self.rol.value}; "
                "solo los rasgos llevan bloque y ventana."
            )
        if self.ventana_minima is not None:
            try:
                orden_ventana(self.ventana_minima)
            except ConfiguracionInvalida as error:
                raise _invalida(f"variable '{nombre}': {error.causa}") from error

        if (self.minimo is not None or self.maximo is not None) and (
            self.tipo not in _TIPOS_CON_RANGO
        ):
            raise _invalida(f"'{nombre}': solo las variables numéricas tienen mínimo y máximo.")
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            raise _invalida(f"'{nombre}': el mínimo es mayor que el máximo.")
        if (self.tipo is TipoDato.CATEGORIA) != (self.valores is not None):
            raise _invalida(f"'{nombre}': las categorías, y solo ellas, declaran 'valores'.")
        if self.valores is not None and not self.valores:
            raise _invalida(f"'{nombre}': 'valores' no puede estar vacío.")
        if self.patron is not None:
            if self.tipo not in _TIPOS_CON_PATRON:
                raise _invalida(f"'{nombre}': solo los textos y códigos tienen 'patron'.")
            try:
                re.compile(self.patron)
            except re.error as error:
                raise _invalida(f"'{nombre}': el patrón no es válido ({error}).") from error
        if self.rol is Rol.ORIGEN and self.valores != (VALOR_ORIGEN_SINTETICO,):
            raise _invalida(
                f"la columna de origen '{nombre}' debe ser una categoría con el único "
                f"valor {VALOR_ORIGEN_SINTETICO}."
            )


@dataclass(frozen=True)
class Diccionario:
    """Diccionario completo: variables y columnas que identifican cada fila."""

    nombre: str
    ficticio: bool
    variables: tuple[DefinicionVariable, ...]
    clave: tuple[str, ...]

    def __post_init__(self) -> None:
        nombres = [v.nombre for v in self.variables]
        repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
        if repetidos:
            raise _invalida(f"variables repetidas: {', '.join(repetidos)}.")
        if not self.variables:
            raise _invalida("no declara ninguna variable.")
        if not self.clave:
            raise _invalida("'clave' debe nombrar las columnas que identifican cada fila.")
        desconocidas = [c for c in self.clave if c not in nombres]
        if desconocidas:
            raise _invalida(f"la clave usa columnas no declaradas: {', '.join(desconocidas)}.")
        if len(self.de_rol(Rol.ORIGEN)) > 1:
            raise _invalida("solo puede haber una columna de origen.")
        if len(self.de_rol(Rol.COHORTE)) > 1:
            raise _invalida("solo puede haber una columna de cohorte.")

    def de_rol(self, rol: Rol) -> tuple[DefinicionVariable, ...]:
        return tuple(v for v in self.variables if v.rol is rol)

    @property
    def columnas(self) -> tuple[str, ...]:
        return tuple(v.nombre for v in self.variables)

    @property
    def identificadores(self) -> tuple[str, ...]:
        return tuple(v.nombre for v in self.de_rol(Rol.IDENTIFICADOR))

    @property
    def columna_origen(self) -> str | None:
        origen = self.de_rol(Rol.ORIGEN)
        return origen[0].nombre if origen else None

    def clave_seudonimizada(self) -> tuple[str, ...]:
        """La clave tras la seudonimización: los identificadores pasan a ser el seudónimo."""
        clave: list[str] = []
        for columna in self.clave:
            nueva = COLUMNA_SEUDONIMO if columna in self.identificadores else columna
            if nueva not in clave:
                clave.append(nueva)
        return tuple(clave)

    def variables_de_escenario(self) -> tuple[Variable, ...]:
        """Los rasgos, con su bloque y ventana mínima, para construir escenarios (M2)."""
        return tuple(
            Variable(v.nombre, v.bloque, v.ventana_minima)
            for v in self.de_rol(Rol.RASGO)
            if v.bloque is not None and v.ventana_minima is not None
        )
