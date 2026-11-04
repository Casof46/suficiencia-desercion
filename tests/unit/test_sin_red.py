"""Las pruebas se ejecutan sin red (criterio 5 de H2.0, RNF-04).

El bloqueo lo aplica la fixture automática ``sin_red`` de ``tests/conftest.py``.
Estas pruebas comprueban que el bloqueo está activo y que solo la interfaz local
del equipo queda permitida (la usa asyncio en Windows).
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


def test_una_conexion_directa_a_otro_equipo_esta_bloqueada() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(RuntimeError, match="no pueden usar la red"):
            sock.connect(("192.0.2.1", 80))
        with pytest.raises(RuntimeError, match="no pueden usar la red"):
            sock.connect_ex(("192.0.2.1", 80))


def test_la_interfaz_local_queda_permitida() -> None:
    # Es lo que hace asyncio en Windows: un par de sockets conectados por 127.0.0.1.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
            cliente.connect(servidor.getsockname())
            conexion, _ = servidor.accept()
            with conexion:
                cliente.sendall(b"ok")
                assert conexion.recv(2) == b"ok"
    respaldo = getattr(socket, "_fallback_socketpair", None)
    if respaldo is not None:
        a, b = respaldo()
        a.close()
        b.close()
