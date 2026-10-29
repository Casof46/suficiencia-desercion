"""Partición cronológica por cohortes y sello de la prueba (M2; RF-M2-06, RF-M2-07).

Toda cohorte de prueba es posterior a toda cohorte de desarrollo y de piloto
(REC-01, PI-07). Las cohortes concretas son DP-05; el piloto lo habilitó DP-08h y
sus cohortes también las fija DP-05. DP-05 debe incluir además un plan de
contingencia, definido antes de ver resultados, por si las cohortes con
seguimiento completo no alcanzan (condición con la que el equipo aceptó REC-01).

La partición de prueba queda sellada: el único modo de obtener sus filas es
``SelloPrueba.leer``, que solo lo permite a la operación de evaluación final y
registra cada intento, permitido o no (RF-M2-07, RF-M6-06, PI-02). Antes de la
evaluación final, de la prueba solo se conoce el tamaño (RF-M2-09).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from suficiencia.domain.errores import ConfiguracionInvalida, ErrorSuficiencia
from suficiencia.domain.trazabilidad.registros import RegistroAcceso

OPERACION_EVALUACION_FINAL = "evaluacion_final"
COLUMNA_PARTICION = "particion"


class AccesoPruebaDenegado(ErrorSuficiencia):
    """Una operación distinta de la evaluación final intentó leer la prueba."""

    def __init__(self, operacion: str) -> None:
        super().__init__(
            f"La operación '{operacion}' intentó leer la partición de prueba, que está sellada. "
            "El intento quedó registrado.",
            "Solo la evaluación final (CU-08) puede leer la prueba, una vez y con el protocolo "
            "aprobado. Use la partición de desarrollo.",
        )


def _texto(valor: object, campo: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ConfiguracionInvalida(
            f"'particion.{campo}' no puede estar vacío.",
            "Complete la partición en la configuración de poblaciones (DP-05).",
        )


@dataclass(frozen=True)
class DefinicionParticion:
    """Cohortes de cada partición (DP-05) y plan de contingencia (REC-01).

    Los códigos de cohorte deben ordenarse cronológicamente como texto (por
    ejemplo, ``2014-1`` < ``2014-2`` < ``2015-1``), como en el diccionario.
    """

    desarrollo: frozenset[str]
    prueba: frozenset[str]
    piloto: frozenset[str]
    excluidas: frozenset[str]
    plan_contingencia: str

    def __post_init__(self) -> None:
        if not self.desarrollo or not self.prueba:
            raise ConfiguracionInvalida(
                "La partición necesita al menos una cohorte de desarrollo y una de prueba.",
                "Complete 'particion' en la configuración de poblaciones (DP-05).",
            )
        grupos = {
            "desarrollo": self.desarrollo,
            "prueba": self.prueba,
            "piloto": self.piloto,
            "excluidas": self.excluidas,
        }
        nombres = list(grupos)
        for i, primero in enumerate(nombres):
            for segundo in nombres[i + 1 :]:
                comunes = grupos[primero] & grupos[segundo]
                if comunes:
                    raise ConfiguracionInvalida(
                        f"Las cohortes {', '.join(sorted(comunes))} están en {primero} y en "
                        f"{segundo}.",
                        "Cada cohorte va a una sola partición.",
                    )
        anteriores = self.desarrollo | self.piloto
        if max(anteriores) >= min(self.prueba):
            raise ConfiguracionInvalida(
                f"La cohorte de prueba {min(self.prueba)} no es posterior a la cohorte "
                f"{max(anteriores)} de desarrollo o piloto.",
                "Toda cohorte de prueba debe ser posterior a las de desarrollo y piloto "
                "(validación cronológica, REC-01; PI-07).",
            )
        _texto(self.plan_contingencia, "plan_contingencia")


class SelloPrueba:
    """Guarda el acceso a las filas de prueba (RF-M2-07)."""

    def __init__(
        self,
        cargar: Callable[[], pd.DataFrame],
        registrar: Callable[[RegistroAcceso], object],
    ) -> None:
        self._cargar = cargar
        self._registrar = registrar

    def leer(self, operacion: str, motivo: str) -> pd.DataFrame:
        """Devuelve las filas de prueba solo a la evaluación final; registra todo intento.

        Raises:
            AccesoPruebaDenegado: si la operación no es la evaluación final.
        """
        permitido = operacion == OPERACION_EVALUACION_FINAL
        self._registrar(RegistroAcceso(operacion=operacion, motivo=motivo, permitido=permitido))
        if not permitido:
            raise AccesoPruebaDenegado(operacion)
        return self._cargar().copy()


@dataclass(frozen=True)
class Particion:
    """Unidades de desarrollo visibles; de la prueba, solo el tamaño y el sello."""

    definicion: DefinicionParticion
    desarrollo: pd.DataFrame
    tamano_prueba: int
    piloto: int
    excluidas: int
    sello: SelloPrueba


@dataclass(frozen=True)
class Division:
    """Resultado de dividir: lo que se persiste antes de sellar."""

    desarrollo: pd.DataFrame
    prueba: pd.DataFrame
    piloto: pd.DataFrame
    excluidas: pd.DataFrame


def dividir(
    unidades: pd.DataFrame, columna_cohorte: str, definicion: DefinicionParticion
) -> Division:
    """Asigna cada unidad a su partición según su cohorte (RF-M2-06).

    Raises:
        ConfiguracionInvalida: si una cohorte de los datos no está asignada a ninguna
            partición o una cohorte declarada no tiene unidades.
    """
    cohortes = unidades[columna_cohorte].astype(str)
    declaradas = (
        definicion.desarrollo | definicion.prueba | definicion.piloto | definicion.excluidas
    )
    sin_asignar = sorted(set(cohortes) - declaradas)
    if sin_asignar:
        raise ConfiguracionInvalida(
            f"Las cohortes {', '.join(sin_asignar)} no están asignadas a ninguna partición.",
            "Asigne cada cohorte a desarrollo, prueba, piloto o excluidas (DP-05).",
        )
    vacias = sorted(declaradas - set(cohortes))
    if vacias:
        raise ConfiguracionInvalida(
            f"Las cohortes {', '.join(vacias)} están declaradas pero no tienen unidades.",
            "Revise los códigos de cohorte de la partición (DP-05).",
        )
    return Division(
        desarrollo=unidades[cohortes.isin(definicion.desarrollo)].reset_index(drop=True),
        prueba=unidades[cohortes.isin(definicion.prueba)].reset_index(drop=True),
        piloto=unidades[cohortes.isin(definicion.piloto)].reset_index(drop=True),
        excluidas=unidades[cohortes.isin(definicion.excluidas)].reset_index(drop=True),
    )


def sellar(division: Division, definicion: DefinicionParticion, sello: SelloPrueba) -> Particion:
    """Entrega la partición con la prueba sellada: fuera del sello solo queda su tamaño."""
    return Particion(
        definicion=definicion,
        desarrollo=division.desarrollo,
        tamano_prueba=len(division.prueba),
        piloto=len(division.piloto),
        excluidas=len(division.excluidas),
        sello=sello,
    )
