"""Servicio de escenarios, poblaciones, particiones y exploración (M2): CU-04 y CU-11.

Desde H2.2 construye y verifica la matriz de 32 escenarios (parte de CU-04). Las
poblaciones y la partición cronológica (resto de CU-04) y CU-11 llegan en H2.5.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    EscenarioResumen,
    ResultadoEscenarios,
    SolicitudGenerarEscenarios,
    VentanaResumen,
)
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.construccion import construir_escenarios, verificar_sin_fuga
from suficiencia.domain.puertos import FuenteCatalogoVentanas, FuenteVariables

ARCHIVO_ESCENARIOS = Path("config") / "escenarios.yaml"
ARCHIVO_VARIABLES = Path("config") / "diccionario" / "variables.yaml"


class ServicioEscenarios(ServicioCasosDeUso):
    """Escenarios, poblaciones, particiones y análisis exploratorio (M2)."""

    NOMBRE: ClassVar[str] = "escenarios"
    DESCRIPCION: ClassVar[str] = (
        "Escenarios, poblaciones, particiones y análisis exploratorio (M2)."
    )
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-04",
            "Generar escenarios, poblaciones y particiones",
            "H2.5 (poblaciones y particiones)",
            avance="los 32 escenarios y el verificador anti-fuga (H2.2): `suficiencia escenarios`",
        ),
        DefinicionCasoDeUso("CU-11", "Ejecutar el análisis exploratorio de viabilidad", "H2.5"),
    )

    def __init__(
        self,
        raiz: Path,
        fuente_catalogo: Callable[[Path], FuenteCatalogoVentanas],
        fuente_variables: Callable[[Path, bool], FuenteVariables],
        fuente_diccionario: Callable[[Path], FuenteVariables],
    ) -> None:
        self._raiz = raiz
        self._fuente_catalogo = fuente_catalogo
        self._fuente_variables = fuente_variables
        self._fuente_diccionario = fuente_diccionario

    def generar_escenarios(self, solicitud: SolicitudGenerarEscenarios) -> ResultadoEscenarios:
        """Construye los 32 escenarios y comprueba que ninguno tenga fuga temporal.

        Raises:
            DecisionPendiente: si faltan las fechas índice (DP-01d) o las variables (DP-03).
            ConfiguracionInvalida: si algún archivo no es válido.
            FugaTemporal: si algún escenario usa una variable antes de su ventana.
        """
        catalogo = self._fuente_catalogo(
            solicitud.configuracion or self._raiz / ARCHIVO_ESCENARIOS
        ).cargar()
        if solicitud.variables is not None and solicitud.diccionario is not None:
            raise ConfiguracionInvalida(
                "Se indicaron a la vez un archivo de variables y un diccionario.",
                "Use solo uno de los dos.",
            )
        if solicitud.diccionario is not None:
            variables = self._fuente_diccionario(solicitud.diccionario).cargar()
        else:
            por_omision = solicitud.variables is None
            variables = self._fuente_variables(
                solicitud.variables or self._raiz / ARCHIVO_VARIABLES, por_omision
            ).cargar()

        escenarios = construir_escenarios(catalogo.catalogo, variables.variables)
        verificar_sin_fuga(escenarios, variables.variables)

        return ResultadoEscenarios(
            ficticio=catalogo.ficticio or variables.ficticio,
            ventanas=tuple(
                VentanaResumen(codigo=v.codigo, fecha_indice=v.fecha_indice)
                for v in catalogo.catalogo.ventanas
            ),
            escenarios=tuple(
                EscenarioResumen(
                    codigo=e.codigo,
                    ventana=e.ventana.codigo,
                    conjunto=e.conjunto.codigo,
                    factible=e.factible,
                    variables=e.variables,
                    bloques_sin_variables=tuple(b.value for b in e.bloques_sin_variables),
                )
                for e in escenarios
            ),
            variables_evaluadas=len(variables.variables),
            sin_fuga=True,
        )
