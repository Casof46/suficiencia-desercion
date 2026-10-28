"""Servicio de protocolo confirmatorio y desviaciones (M4): CU-05.

En H2.1 solo declara sus casos de uso; ninguno tiene lógica todavía.
"""

from __future__ import annotations

from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso


class ServicioProtocolo(ServicioCasosDeUso):
    """Protocolo confirmatorio y desviaciones (M4)."""

    NOMBRE: ClassVar[str] = "protocolo"
    DESCRIPCION: ClassVar[str] = "Protocolo confirmatorio y desviaciones (M4)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso("CU-05", "Definir y aprobar el protocolo confirmatorio", "H2.6"),
    )
