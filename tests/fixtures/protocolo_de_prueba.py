"""Ayudas de prueba para H2.6: el protocolo ficticio y un procedimiento de multiplicidad ficticio.

EJEMPLO FICTICIO. Nada de este módulo es un criterio, un umbral ni un procedimiento
de multiplicidad del proyecto: existe solo para comprobar el motor (DP-08 abierta).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from suficiencia.domain.evaluacion.protocolo import (
    ContenidoProtocolo,
    HistorialProtocolo,
    aprobar,
    contenido_desde_datos,
    guardar_borrador,
)
from suficiencia.domain.evaluacion.suficiencia import (
    EstadoEscenario,
    EvaluacionEscenario,
    ResultadoEscenario,
)
from suficiencia.domain.puertos import RepositorioRegistros
from suficiencia.domain.trazabilidad.registros import TipoRegistro

ARCHIVO_PROTOCOLO_FICTICIO = (
    Path(__file__).resolve().parents[2] / "config" / "ejemplos" / "protocolo_ficticio.yaml"
)
PROCEDIMIENTO_FICTICIO = "procedimiento_ficticio"


def datos_protocolo_ficticio() -> dict[str, Any]:
    datos = yaml.safe_load(ARCHIVO_PROTOCOLO_FICTICIO.read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


def contenido_ficticio(**cambios: Any) -> ContenidoProtocolo:
    datos = datos_protocolo_ficticio()
    datos.update(cambios)
    return contenido_desde_datos(datos)


class SinAjusteFicticio:
    """EJEMPLO FICTICIO: confirma todos los escenarios que cumplen. No es una propuesta."""

    def confirmar(
        self,
        evaluaciones: tuple[EvaluacionEscenario, ...],
        resultados: Mapping[str, ResultadoEscenario],
    ) -> frozenset[str]:
        return frozenset(e.escenario for e in evaluaciones if e.estado is EstadoEscenario.CUMPLE)


PROCEDIMIENTOS_FICTICIOS = {PROCEDIMIENTO_FICTICIO: SinAjusteFicticio()}


def historial(repositorio: RepositorioRegistros) -> HistorialProtocolo:
    return HistorialProtocolo.desde_registros(
        [g.contenido for g in repositorio.listar(TipoRegistro.PROTOCOLO)]
    )


def aprobar_protocolo_ficticio(
    repositorio: RepositorioRegistros, contenido: ContenidoProtocolo | None = None
) -> int:
    """Guarda y aprueba el protocolo ficticio directamente en el registro; devuelve la versión."""
    contenido = contenido or contenido_ficticio()
    borrador = guardar_borrador(historial(repositorio), contenido, None)
    repositorio.agregar(borrador)
    aprobacion = aprobar(
        historial(repositorio), borrador.version, borrador.huella, "Equipo (prueba)", [], None
    )
    repositorio.agregar(aprobacion.aprobacion)
    return borrador.version
