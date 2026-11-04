"""Configuración común de las pruebas.

Todas las pruebas se ejecutan sin acceso a la red: cualquier intento de abrir una
conexión de red desde el proceso de pruebas falla de inmediato (RNF-04).
Esto no afecta a procesos hijos (por ejemplo, ``git``), que no abren conexiones.

La única excepción es la interfaz local del propio equipo (127.0.0.1 y ::1), que no
sale del equipo. En Windows, asyncio la necesita para crear su par de sockets
interno (``socket.socketpair``); sin ella fallan las pruebas del visor (H2.D).
Resolver nombres y abrir conexiones con ``create_connection`` siguen bloqueados.
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


_CONECTAR = socket.socket.connect
_CONECTAR_EX = socket.socket.connect_ex


def _bloquear(*_args: Any, **_kwargs: Any) -> Any:
    raise AccesoARedBloqueado("Las pruebas de este proyecto no pueden usar la red (RNF-04).")


def _es_local(direccion: Any) -> bool:
    """Indica si la dirección es la interfaz local del equipo (127.x.x.x o ::1)."""
    if not isinstance(direccion, tuple) or not direccion:
        return False
    host = str(direccion[0])
    return host.startswith("127.") or host == "::1"


def _conectar(sock: socket.socket, direccion: Any) -> None:
    if not _es_local(direccion):
        _bloquear()
    _CONECTAR(sock, direccion)


def _conectar_ex(sock: socket.socket, direccion: Any) -> int:
    if not _es_local(direccion):
        _bloquear()
    return _CONECTAR_EX(sock, direccion)


@pytest.fixture(autouse=True)
def sin_red(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Bloquea las conexiones de red durante cada prueba, salvo la interfaz local."""
    monkeypatch.setattr(socket.socket, "connect", _conectar)
    monkeypatch.setattr(socket.socket, "connect_ex", _conectar_ex)
    monkeypatch.setattr(socket, "create_connection", _bloquear)
    monkeypatch.setattr(socket, "getaddrinfo", _bloquear)
    yield


@pytest.fixture
def raiz() -> Path:
    """Raíz del repositorio."""
    return RAIZ_REPOSITORIO
