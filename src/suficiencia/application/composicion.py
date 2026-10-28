"""Composición: construye los servicios con sus implementaciones concretas.

Es el único lugar de la aplicación que elige qué adaptador de persistencia o de
experimentación implementa cada puerto. La línea de comandos y la futura interfaz
obtienen aquí los servicios y no importan otras capas (contratos de ``.importlinter``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import suficiencia
from suficiencia.application._base import ServicioCasosDeUso
from suficiencia.application.servicio_datos import ServicioDatos
from suficiencia.application.servicio_escenarios import ServicioEscenarios
from suficiencia.application.servicio_evaluacion_final import ServicioEvaluacionFinal
from suficiencia.application.servicio_experimentos import ServicioExperimentos
from suficiencia.application.servicio_interpretabilidad import ServicioInterpretabilidad
from suficiencia.application.servicio_protocolo import ServicioProtocolo
from suficiencia.application.servicio_proyecto import ServicioProyecto
from suficiencia.application.servicio_reportes import ServicioReportes
from suficiencia.domain.errores import ErrorSuficiencia
from suficiencia.domain.puertos import FuenteVariables
from suficiencia.persistence.configuracion import FuenteConfiguracionYaml
from suficiencia.persistence.escenarios_yaml import FuenteCatalogoYaml, FuenteVariablesYaml


@dataclass(frozen=True)
class Servicios:
    """Servicios de aplicación listos para usar."""

    proyecto: ServicioProyecto
    escenarios: ServicioEscenarios
    casos_de_uso: tuple[ServicioCasosDeUso, ...]

    def servicio_de(self, codigo: str) -> ServicioCasosDeUso:
        """Devuelve el servicio que atiende el caso de uso indicado."""
        for servicio in self.casos_de_uso:
            if any(caso.codigo == codigo for caso in servicio.CASOS_DE_USO):
                return servicio
        raise ErrorSuficiencia(
            f"No existe el caso de uso {codigo}.",
            "Use un código entre CU-01 y CU-12; `suficiencia estado` los lista.",
        )


def _fuente_variables(archivo: Path, por_omision: bool) -> FuenteVariables:
    return FuenteVariablesYaml(archivo, por_omision=por_omision)


def crear_servicios(raiz: Path) -> Servicios:
    """Construye los servicios para el proyecto ubicado en ``raiz``."""
    escenarios = ServicioEscenarios(
        raiz=raiz, fuente_catalogo=FuenteCatalogoYaml, fuente_variables=_fuente_variables
    )
    casos_de_uso: tuple[ServicioCasosDeUso, ...] = (
        ServicioDatos(),
        escenarios,
        ServicioProtocolo(),
        ServicioExperimentos(),
        ServicioEvaluacionFinal(),
        ServicioInterpretabilidad(),
        ServicioReportes(),
    )
    proyecto = ServicioProyecto(
        raiz=raiz,
        version_paquete=suficiencia.__version__,
        servicios=casos_de_uso,
        fuente_configuracion=FuenteConfiguracionYaml,
    )
    return Servicios(proyecto=proyecto, escenarios=escenarios, casos_de_uso=casos_de_uso)
