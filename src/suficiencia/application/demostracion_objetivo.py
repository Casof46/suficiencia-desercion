"""Historiales FICTICIOS escritos a mano para mostrar cómo se etiqueta cada caso (H2.4).

No son datos de ninguna persona ni de ninguna institución: son secuencias de
códigos inventadas para ver, con la definición ficticia de
``config/ejemplos/objetivo_ficticio.yaml``, qué estado produce cada situación
del desglose de DP-01 (pausas, reingresos, traslados, seguimiento incompleto...).
Un guion ("-") marca un periodo sin registro dentro de lo observable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFINICION_DEMOSTRACION = Path("config/ejemplos/objetivo_ficticio.yaml")
SIN_REGISTRO = "-"

_CODIGOS = {
    "M": "matriculado",
    "A": "no_matriculado",
    "P": "reserva",
    "R": "retiro_total",
    "T": "traslado",
}


@dataclass(frozen=True)
class CasoFicticio:
    nombre: str
    secuencia: str
    """Una letra por periodo: M matriculado, A no matriculado, P reserva, R retiro
    total, T traslado, - sin registro."""
    periodos_observables: int

    def estados(self) -> dict[int, str]:
        return {
            periodo: _CODIGOS[letra]
            for periodo, letra in enumerate(self.secuencia, start=1)
            if letra != SIN_REGISTRO
        }

    def historial(self) -> tuple[str, ...]:
        return tuple(
            SIN_REGISTRO if letra == SIN_REGISTRO else _CODIGOS[letra] for letra in self.secuencia
        )


CASOS = (
    CasoFicticio("Siempre matriculado", "MMMMMMMM", 8),
    CasoFicticio("Deja de matricularse en el periodo 3", "MMAAAAAA", 8),
    CasoFicticio("Pausa de un periodo y vuelve", "MPMMMMMM", 8),
    CasoFicticio("Pausa larga sin volver", "MPPPAAAA", 8),
    CasoFicticio("Reingresa dentro del horizonte", "MAAMMMMM", 8),
    CasoFicticio("Retiro de todos los cursos y no vuelve", "MRAAAAAA", 8),
    CasoFicticio("Traslado a otra institución", "MMT", 8),
    CasoFicticio("Periodo sin registro", "MM-MMMMM", 8),
    CasoFicticio("Cohorte reciente: horizonte sin completar", "MMMM", 4),
    CasoFicticio("Ausencia al final, sin poder confirmarla", "MMMMMA", 6),
)
