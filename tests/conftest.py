"""Configuración común de las pruebas.

Todas las pruebas se ejecutan sin acceso a la red: cualquier intento de abrir una
conexión de red desde el proceso de pruebas falla de inmediato (RNF-04).
Esto no afecta a procesos hijos (por ejemplo, ``git``), que no abren conexiones.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings

# Pruebas basadas en propiedades reproducibles: la misma secuencia de casos en cada
# ejecución y en cada equipo, sin base de ejemplos guardados. Hypothesis igual crea
# una carpeta .hypothesis/ de caché, que está excluida de git.
settings.register_profile("suficiencia", derandomize=True, database=None, deadline=None)
settings.load_profile("suficiencia")

RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent


class AccesoARedBloqueado(RuntimeError):
    """Una prueba intentó usar la red."""


def _bloquear(*_args: Any, **_kwargs: Any) -> Any:
    raise AccesoARedBloqueado("Las pruebas de este proyecto no pueden usar la red (RNF-04).")


@pytest.fixture(autouse=True)
def sin_red(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Bloquea las conexiones de red durante cada prueba."""
    monkeypatch.setattr(socket.socket, "connect", _bloquear)
    monkeypatch.setattr(socket.socket, "connect_ex", _bloquear)
    monkeypatch.setattr(socket, "create_connection", _bloquear)
    monkeypatch.setattr(socket, "getaddrinfo", _bloquear)
    yield


@pytest.fixture
def raiz() -> Path:
    """Raíz del repositorio."""
    return RAIZ_REPOSITORIO
