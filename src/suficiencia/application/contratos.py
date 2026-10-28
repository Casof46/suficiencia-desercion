"""Contratos de entrada y salida de los servicios de aplicación (RNF-14).

Son objetos inmutables que rechazan campos desconocidos. La línea de comandos, la
futura interfaz y una API futura usan estos mismos contratos.

Los contratos de cada caso de uso se definen en el hito que lo implementa: muchos
dependen de decisiones abiertas (por ejemplo, CU-03 de DP-01) y fijarlos ahora
obligaría a suponer valores (decisión D-21 de H2.1).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

PATRON_CASO_DE_USO = r"^CU-\d{2}$"


class Contrato(BaseModel):
    """Base de todos los contratos: inmutable y sin campos adicionales."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class CasoDeUso(Contrato):
    """Un caso de uso de la especificación (sección 3) y su disponibilidad."""

    codigo: str = Field(pattern=PATRON_CASO_DE_USO)
    nombre: str = Field(min_length=1)
    servicio: str = Field(min_length=1)
    hito: str = Field(min_length=1, description="Hito o fase en que se construye.")
    disponible: bool


class EstadoServicio(Contrato):
    """Qué casos de uso atiende un servicio y cuáles están disponibles."""

    servicio: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    casos_de_uso: tuple[CasoDeUso, ...]


class EstadoProyecto(Contrato):
    """Estado del motor: versión del paquete y servicios."""

    version_paquete: str
    servicios: tuple[EstadoServicio, ...]


class SolicitudCasoDeUso(Contrato):
    """Pide ejecutar un caso de uso por su código."""

    codigo: str = Field(pattern=PATRON_CASO_DE_USO)


class SolicitudValidarConfiguracion(Contrato):
    """Pide validar un archivo de configuración del proyecto.

    Sin ``archivo``, se valida ``config/proyecto.yaml`` de la raíz del proyecto.
    """

    archivo: Path | None = None


class ResultadoValidacionConfiguracion(Contrato):
    """Resultado de validar la configuración del proyecto."""

    valida: bool
    archivo: str
    nombre_proyecto: str | None = None
    version_especificacion: str | None = None
    semilla_global_definida: bool | None = None
    tolerancia_metricas_definida: bool | None = None
    error: str | None = None
