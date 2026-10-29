"""Registro de trazabilidad en SQLite (DP-16, decidida el 29 de octubre de 2026).

Una tabla por tipo de registro. Las tablas tienen disparadores que rechazan
cualquier modificación o borrado: solo se puede agregar. Además, cada registro
guarda su huella encadenada con la del anterior, de modo que una edición hecha
fuera del programa (por ejemplo, quitando los disparadores) se detecta al
verificar.

Es el único módulo del proyecto que usa sqlite3.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.trazabilidad.registros import (
    HUELLA_INICIAL,
    RegistroAcceso,
    RegistroDecision,
    RegistroExperimento,
    RegistroGuardado,
    TipoRegistro,
    huella_encadenada,
    json_canonico,
)

ARCHIVO_REGISTRO = "registro.sqlite"
VERSION_ESQUEMA = 1

_TIPO_DE = {
    RegistroExperimento: TipoRegistro.EXPERIMENTO,
    RegistroDecision: TipoRegistro.DECISION,
    RegistroAcceso: TipoRegistro.ACCESO,
}


def _esquema() -> str:
    sentencias = [f"PRAGMA user_version = {VERSION_ESQUEMA};"]
    for tipo in TipoRegistro:
        tabla = tipo.value
        sentencias.append(
            f"""
            CREATE TABLE IF NOT EXISTS {tabla} (
                numero INTEGER PRIMARY KEY,
                fecha TEXT NOT NULL,
                contenido TEXT NOT NULL,
                huella_anterior TEXT NOT NULL,
                huella TEXT NOT NULL UNIQUE
            );
            CREATE TRIGGER IF NOT EXISTS {tabla}_sin_modificar BEFORE UPDATE ON {tabla}
            BEGIN SELECT RAISE(ABORT, 'El registro solo admite agregar'); END;
            CREATE TRIGGER IF NOT EXISTS {tabla}_sin_borrar BEFORE DELETE ON {tabla}
            BEGIN SELECT RAISE(ABORT, 'El registro solo admite agregar'); END;
            """
        )
    return "\n".join(sentencias)


class RepositorioSqlite:
    """Implementa el puerto ``RepositorioRegistros``.

    Abre y cierra la conexión en cada operación: así el archivo no queda
    bloqueado entre comandos (importante en Windows).
    """

    def __init__(self, archivo: Path) -> None:
        self.archivo = archivo

    def _conectar(self) -> sqlite3.Connection:
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        conexion = sqlite3.connect(self.archivo)
        conexion.executescript(_esquema())
        return conexion

    def agregar(
        self, registro: RegistroExperimento | RegistroDecision | RegistroAcceso
    ) -> RegistroGuardado:
        tipo = _TIPO_DE[type(registro)]
        contenido = registro.contenido()
        texto = json_canonico(contenido)
        fecha = datetime.now(UTC).isoformat(timespec="seconds")
        with closing(self._conectar()) as conexion, conexion:
            fila = conexion.execute(
                f"SELECT huella FROM {tipo.value} ORDER BY numero DESC LIMIT 1"
            ).fetchone()
            anterior = fila[0] if fila else HUELLA_INICIAL
            huella = huella_encadenada(anterior, fecha, texto)
            cursor = conexion.execute(
                f"INSERT INTO {tipo.value} (fecha, contenido, huella_anterior, huella) "
                "VALUES (?, ?, ?, ?)",
                (fecha, texto, anterior, huella),
            )
            numero = int(cursor.lastrowid or 0)
        return RegistroGuardado(tipo, numero, fecha, contenido, anterior, huella)

    def listar(self, tipo: TipoRegistro) -> list[RegistroGuardado]:
        if not self.archivo.exists():
            return []
        with closing(self._conectar()) as conexion:
            filas = conexion.execute(
                f"SELECT numero, fecha, contenido, huella_anterior, huella FROM {tipo.value} "
                "ORDER BY numero"
            ).fetchall()
        guardados = []
        for numero, fecha, contenido, anterior, huella in filas:
            try:
                datos = json.loads(contenido)
            except json.JSONDecodeError as error:
                raise ConfiguracionInvalida(
                    f"El registro n.º {numero} de {tipo.value} está dañado.",
                    "Ejecute `suficiencia registro verificar` y no siga usando este registro.",
                ) from error
            guardados.append(RegistroGuardado(tipo, numero, fecha, datos, anterior, huella))
        return guardados
