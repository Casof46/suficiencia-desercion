"""Registrador de corridas (RF-M6-01, RF-M3-11; PI-03 y PI-12).

Ejecuta una función de experimento y registra la corrida, tanto si termina bien
como si falla. Las corridas fallidas quedan registradas junto con las exitosas,
con su error, y no detienen a quien ejecuta un lote. Lo usarán los experimentos
de fases posteriores; en H2.7 solo se prueba con funciones simuladas.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from suficiencia.domain.puertos import CapturadorEntorno, RepositorioRegistros
from suficiencia.domain.trazabilidad.registros import (
    EstadoCorrida,
    ModoExperimento,
    RegistroExperimento,
    RegistroGuardado,
)


def nuevo_identificador() -> str:
    marca = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    return f"EXP-{marca}-{secrets.token_hex(3)}"


class RegistradorCorridas:
    def __init__(self, repositorio: RepositorioRegistros, capturador: CapturadorEntorno) -> None:
        self._repositorio = repositorio
        self._capturador = capturador

    def ejecutar(
        self,
        funcion: Callable[[], dict[str, Any]],
        *,
        modo: ModoExperimento,
        configuracion: dict[str, Any],
        semillas: dict[str, int],
        huella_datos: str | None,
        version_protocolo: str | None,
    ) -> RegistroGuardado:
        """Ejecuta ``funcion`` y registra la corrida con su resultado o su error.

        El entorno se captura antes de ejecutar. Si la función falla, se registra
        el tipo y el mensaje del error, sin la traza (que podría incluir datos).
        """
        entorno = self._capturador.capturar()
        identificador = nuevo_identificador()
        try:
            resultados = funcion()
        except Exception as error:  # noqa: BLE001 - toda falla debe quedar registrada
            registro = RegistroExperimento(
                identificador=identificador,
                modo=modo,
                estado=EstadoCorrida.FALLIDA,
                version_protocolo=version_protocolo,
                configuracion=configuracion,
                semillas=semillas,
                huella_datos=huella_datos,
                entorno=entorno,
                error=f"{type(error).__name__}: {error}",
            )
        else:
            registro = RegistroExperimento(
                identificador=identificador,
                modo=modo,
                estado=EstadoCorrida.EXITOSA,
                version_protocolo=version_protocolo,
                configuracion=configuracion,
                semillas=semillas,
                huella_datos=huella_datos,
                entorno=entorno,
                resultados=resultados,
            )
        return self._repositorio.agregar(registro)
