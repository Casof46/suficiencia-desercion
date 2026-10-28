"""Conceptos de M2: bloques, ventanas, conjuntos de información, variables y escenarios.

Lo que fija la especificación como definido (DEF) está en el código: los cuatro
bloques, las cuatro ventanas y su orden, y los ocho conjuntos (RF-M2-02). Lo que
depende de decisiones abiertas entra como parámetro obligatorio sin valor por
defecto: la fecha índice de cada ventana (DP-01d) y el bloque y la ventana mínima
de cada variable (DP-03).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from itertools import combinations

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente


class Bloque(Enum):
    """Bloques de información (DEF)."""

    ACADEMICO = "A"
    FINANCIERO = "F"
    SOCIOECONOMICO = "S"
    CONDUCTUAL = "B"

    @property
    def nombre(self) -> str:
        return _NOMBRES_BLOQUE[self]

    @classmethod
    def desde_codigo(cls, codigo: str) -> Bloque:
        for bloque in cls:
            if bloque.value == codigo:
                return bloque
        raise ConfiguracionInvalida(
            f"El bloque {codigo!r} no existe.",
            "Use uno de los códigos A, F, S o B.",
        )


_NOMBRES_BLOQUE = {
    Bloque.ACADEMICO: "Académico",
    Bloque.FINANCIERO: "Financiero",
    Bloque.SOCIOECONOMICO: "Socioeconómico",
    Bloque.CONDUCTUAL: "Conductual",
}

BLOQUE_BASE = Bloque.ACADEMICO
"""Todo conjunto incluye el bloque académico (RF-M2-02)."""

CODIGOS_VENTANA = ("T0", "T1", "T2", "T3")
"""Ventanas en orden temporal (DEF)."""


def orden_ventana(codigo: str) -> int:
    """Posición de la ventana en el tiempo: T0 es 0 y T3 es 3."""
    if codigo not in CODIGOS_VENTANA:
        raise ConfiguracionInvalida(
            f"La ventana {codigo!r} no existe.",
            "Use una de las ventanas T0, T1, T2 o T3.",
        )
    return CODIGOS_VENTANA.index(codigo)


@dataclass(frozen=True)
class Ventana:
    """Ventana temporal con su fecha índice (RF-M2-01).

    La fecha índice es el momento en que la información de la ventana queda
    consolidada. Depende de DP-01d y no tiene valor por defecto. Se guarda como
    texto porque DP-01d todavía no decide si será una fecha del calendario o un
    momento relativo del ciclo académico.
    """

    codigo: str
    fecha_indice: str

    def __post_init__(self) -> None:
        orden_ventana(self.codigo)
        if not self.fecha_indice.strip():
            raise DecisionPendiente("DP-01d", f"la fecha índice de la ventana {self.codigo}")

    @property
    def orden(self) -> int:
        return orden_ventana(self.codigo)


@dataclass(frozen=True)
class CatalogoVentanas:
    """Las cuatro ventanas, en orden y cada una con su fecha índice (PU-18)."""

    ventanas: tuple[Ventana, ...]

    def __post_init__(self) -> None:
        codigos = tuple(ventana.codigo for ventana in self.ventanas)
        if codigos != CODIGOS_VENTANA:
            raise ConfiguracionInvalida(
                f"El catálogo de ventanas debe ser T0, T1, T2 y T3 en ese orden; "
                f"se recibió {', '.join(codigos) or 'ninguna'}.",
                "Declare las cuatro ventanas una sola vez y en orden temporal.",
            )

    @classmethod
    def desde_fechas_indice(cls, fechas: dict[str, str | None]) -> CatalogoVentanas:
        """Construye el catálogo. Una fecha índice ausente detiene la construcción."""
        ventanas = []
        for codigo, fecha in fechas.items():
            if fecha is None:
                raise DecisionPendiente("DP-01d", f"la fecha índice de la ventana {codigo}")
            ventanas.append(Ventana(codigo, fecha))
        return cls(tuple(ventanas))


@dataclass(frozen=True)
class ConjuntoInformacion:
    """Combinación de bloques; siempre incluye el bloque académico."""

    bloques: frozenset[Bloque]

    def __post_init__(self) -> None:
        if BLOQUE_BASE not in self.bloques:
            raise ConfiguracionInvalida(
                "Todo conjunto de información debe incluir el bloque académico (A).",
                "Revise la definición de los conjuntos (RF-M2-02).",
            )

    @property
    def codigo(self) -> str:
        """Código legible, por ejemplo ``A+F+B``, en el orden A, F, S, B."""
        return "+".join(b.value for b in Bloque if b in self.bloques)


def generar_conjuntos() -> tuple[ConjuntoInformacion, ...]:
    """Los ocho conjuntos candidatos de RF-M2-02, de menor a mayor tamaño.

    A, A+F, A+S, A+B, A+F+S, A+F+B, A+S+B y A+F+S+B.
    """
    opcionales = [b for b in Bloque if b is not BLOQUE_BASE]
    conjuntos = []
    for tamano in range(len(opcionales) + 1):
        for combinacion in combinations(opcionales, tamano):
            conjuntos.append(ConjuntoInformacion(frozenset({BLOQUE_BASE, *combinacion})))
    return tuple(conjuntos)


@dataclass(frozen=True)
class Variable:
    """Variable candidata con su bloque y la primera ventana en que está disponible.

    El bloque y la ventana mínima de las variables reales dependen de DP-03.
    """

    nombre: str
    bloque: Bloque
    ventana_minima: str

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ConfiguracionInvalida(
                "Hay una variable sin nombre.", "Asigne un nombre a cada variable."
            )
        orden_ventana(self.ventana_minima)

    def disponible_en(self, ventana: Ventana) -> bool:
        """Disponible en Tj si su ventana mínima Tk cumple k <= j (invariante de M2)."""
        return orden_ventana(self.ventana_minima) <= ventana.orden


def validar_variables(variables: Iterable[Variable]) -> tuple[Variable, ...]:
    """Rechaza nombres repetidos y devuelve las variables como tupla."""
    lista = tuple(variables)
    vistos: set[str] = set()
    repetidos: set[str] = set()
    for variable in lista:
        if variable.nombre in vistos:
            repetidos.add(variable.nombre)
        vistos.add(variable.nombre)
    if repetidos:
        raise ConfiguracionInvalida(
            f"Variables repetidas: {', '.join(sorted(repetidos))}.",
            "Cada variable debe aparecer una sola vez.",
        )
    return lista


@dataclass(frozen=True)
class Escenario:
    """Combinación ventana × conjunto con sus variables y su factibilidad (RF-M2-03)."""

    ventana: Ventana
    conjunto: ConjuntoInformacion
    variables: tuple[str, ...]
    bloques_sin_variables: tuple[Bloque, ...]

    @property
    def codigo(self) -> str:
        return f"{self.ventana.codigo}|{self.conjunto.codigo}"

    @property
    def factible(self) -> bool:
        """No factible si algún bloque del conjunto no tiene variables en la ventana."""
        return not self.bloques_sin_variables


@dataclass(frozen=True)
class CatalogoDeclarado:
    """Catálogo de ventanas leído de la configuración, con su origen."""

    catalogo: CatalogoVentanas
    ficticio: bool


@dataclass(frozen=True)
class VariablesDeclaradas:
    """Variables leídas de la configuración, con su origen."""

    variables: tuple[Variable, ...]
    ficticio: bool
