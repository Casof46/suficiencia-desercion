"""Puertos del dominio: interfaces que implementan las capas externas.

El dominio define qué necesita y las capas de persistencia y experimentación lo
implementan (sección 5, reglas de diseño). Así el motor puede probarse con
implementaciones de prueba, sin archivos ni modelos.

Solo se definen los puertos cuya forma no depende de decisiones abiertas:

- :class:`FuenteConfiguracion`: implementado en H2.1 por
  ``persistence.configuracion.FuenteConfiguracionYaml``.
- :class:`AlmacenArtefactos`: interfaz fijada en H2.1; su implementación llega
  con la trazabilidad (H2.7).
- :class:`FuenteCatalogoVentanas` y :class:`FuenteVariables`: H2.2, implementados
  por ``persistence.escenarios_yaml``. Desde H2.3, ``persistence.diccionario_yaml``
  ofrece otra implementación de ``FuenteVariables`` a partir del diccionario.
- :class:`Seudonimizador`: H2.3, implementado provisionalmente por
  ``persistence.seudonimizacion.SeudonimizadorHmac`` hasta que se decida DP-14.

Los demás puertos que nombra la especificación se definen en el hito que los usa,
para no fijar firmas antes de tiempo:

- ``RepositorioExperimentos``: H2.7, según DP-16 (SQLite o archivos).
- ``EntrenadorModelos`` y ``Explicador``: fases posteriores a la Fase 2.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from suficiencia.domain.escenarios.modelo import CatalogoDeclarado, VariablesDeclaradas
from suficiencia.domain.huella import Huella
from suficiencia.domain.proyecto import ConfiguracionProyecto


class FuenteConfiguracion(Protocol):
    """Entrega la configuración validada del proyecto."""

    def cargar(self) -> ConfiguracionProyecto:
        """Devuelve la configuración.

        Raises:
            ConfiguracionInvalida: si la configuración falta o no es válida.
        """
        ...


class AlmacenArtefactos(Protocol):
    """Guarda contenidos inmutables identificados por su huella (RNF-16)."""

    def guardar(self, nombre: str, contenido: bytes) -> Huella:
        """Guarda el contenido y devuelve su huella. Guardar dos veces lo mismo no lo duplica."""
        ...

    def leer(self, huella: Huella) -> bytes:
        """Devuelve el contenido con esa huella."""
        ...

    def existe(self, huella: Huella) -> bool:
        """Indica si hay un contenido guardado con esa huella."""
        ...


class FuenteCatalogoVentanas(Protocol):
    """Entrega el catálogo de ventanas con sus fechas índice."""

    def cargar(self) -> CatalogoDeclarado:
        """Devuelve el catálogo y si su origen es un ejemplo ficticio.

        Raises:
        DecisionPendiente: si falta alguna fecha índice (DP-01d).
        ConfiguracionInvalida: si la configuración no es válida.
        """
        ...


class FuenteVariables(Protocol):
    """Entrega las variables candidatas con su bloque y su ventana mínima."""

    def cargar(self) -> VariablesDeclaradas:
        """Devuelve las variables y si su origen es un ejemplo ficticio.

        Raises:
        DecisionPendiente: si las variables reales todavía no están definidas (DP-03).
        ConfiguracionInvalida: si la definición no es válida.
        """
        ...


class Seudonimizador(Protocol):
    """Reemplaza las columnas identificadoras por un seudónimo (RF-M1-04)."""

    def seudonimizar(self, tabla: pd.DataFrame, identificadores: tuple[str, ...]) -> pd.DataFrame:
        """Devuelve una tabla nueva sin los identificadores y con la columna ``seudonimo``."""
        ...
