"""Las pruebas se ejecutan sin red (criterio 5 de H2.0, RNF-04).

El bloqueo lo aplica la fixture automática ``sin_red`` de ``tests/conftest.py``.
Estas pruebas comprueban que el bloqueo está activo.
"""

from __future__ import annotations

import socket

import pytest


def test_las_conexiones_de_red_estan_bloqueadas() -> None:
    # 192.0.2.1 es una dirección reservada para documentación: no corresponde a ningún servidor.
    with pytest.raises(RuntimeError, match="no pueden usar la red"):
        socket.create_connection(("192.0.2.1", 80), timeout=1)


def test_la_resolucion_de_nombres_esta_bloqueada() -> None:
    with pytest.raises(RuntimeError, match="no pueden usar la red"):
        socket.getaddrinfo("example.org", 443)
