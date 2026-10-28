"""Puertos del dominio: interfaces que implementan las capas externas.

El dominio define qué necesita y las capas de persistencia y experimentación lo
implementan (sección 5, reglas de diseño). Así el motor puede probarse con
implementaciones de prueba, sin archivos ni modelos.

Solo se definen los puertos cuya forma no depende de decisiones abiertas:

- :class:`FuenteConfiguracion`: implementado en H2.1 por
  ``persistence.configuracion.FuenteConfiguracionYaml``.
- :class:`AlmacenArtefactos`: interfaz fijada en H2.1; su implementación llega
  con la trazabilidad (H2.7).

Los demás puertos que nombra la especificación se definen en el hito que los usa,
para no fijar firmas antes de tiempo:

- ``RepositorioExperimentos``: H2.7, según DP-16 (SQLite o archivos).
- ``EntrenadorModelos`` y ``Explicador``: fases posteriores a la Fase 2.
"""

from __future__ import annotations

from typing import Protocol

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
