"""Servicio de evaluación final y comparación con la referencia (M4): CU-08 y CU-12.

Desde H2.6: las comprobaciones que CU-08 hace antes de abrir la prueba (pasos 2
y 3): protocolo aprobado vigente y configuraciones idénticas a las congeladas
(RF-M4-05, RF-M4-09, RF-M4-12; PI-09). La evaluación final misma, que abre la
prueba, y la comparación con R0 llegan en fases posteriores.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    ResultadoVerificacionEvaluacionFinal,
    SolicitudVerificarEvaluacionFinal,
)
from suficiencia.application.servicio_experimentos import configuraciones_congeladas
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.evaluacion.congelamiento import (
    configuracion_desde_datos,
    preparar_evaluacion_final,
)
from suficiencia.domain.puertos import RepositorioRegistros


class ServicioEvaluacionFinal(ServicioCasosDeUso):
    """Evaluación final, regla de suficiencia y comparación con la referencia (M4)."""

    NOMBRE: ClassVar[str] = "evaluacion_final"
    DESCRIPCION: ClassVar[str] = (
        "Evaluación final, regla de suficiencia y comparación con la referencia (M4)."
    )
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-08",
            "Ejecutar evaluación final y regla de suficiencia",
            "una fase posterior a la Fase 2",
            avance="comprobaciones previas a abrir la prueba y motor de la regla con "
            "criterios ficticios (H2.6)",
        ),
        DefinicionCasoDeUso(
            "CU-12",
            "Ejecutar la evaluación comparativa frente a la referencia",
            "una fase posterior a la Fase 2",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        repositorio: Callable[[Path], RepositorioRegistros],
        archivo_registro: Callable[[], Path],
        leer_yaml: Callable[[Path], Any],
    ) -> None:
        self._raiz = raiz
        self._repositorio = repositorio
        self._archivo_registro = archivo_registro
        self._leer_yaml = leer_yaml

    def verificar_precondiciones(
        self, solicitud: SolicitudVerificarEvaluacionFinal
    ) -> ResultadoVerificacionEvaluacionFinal:
        """Comprueba protocolo vigente y huellas sin abrir la prueba (CU-08, pasos 2 y 3).

        Raises:
            SinProtocoloVigente: sin protocolo aprobado vigente (PU-05).
            HuellaNoCoincide: si una configuración no es la congelada (PI-09).
        """
        configuraciones = [
            configuracion_desde_datos(
                self._leer_yaml(archivo if archivo.is_absolute() else self._raiz / archivo)
            )
            for archivo in solicitud.archivos
        ]
        repositorio = self._repositorio(self._archivo_registro())
        preparacion = preparar_evaluacion_final(
            historial_protocolo(repositorio),
            configuraciones,
            configuraciones_congeladas(repositorio),
        )
        return ResultadoVerificacionEvaluacionFinal(
            version_protocolo=preparacion.version_protocolo,
            huella_protocolo=preparacion.huella_protocolo,
            configuraciones=dict(preparacion.configuraciones),
            ficticio=preparacion.ficticio,
        )
