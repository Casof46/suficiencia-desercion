"""Filtro de identificadores para reportes y exportaciones (RNF-05, PI-04).

Toda exportación pasa por este filtro: si alguna columna es un identificador
directo, la exportación se detiene. No se eliminan columnas en silencio, para
que el problema se corrija en su origen.
"""

from __future__ import annotations

from collections.abc import Iterable

from suficiencia.domain.errores import ErrorSuficiencia

NOMBRES_IDENTIFICADORES = frozenset(
    {
        "codigo_estudiante",
        "codigo_alumno",
        "dni",
        "documento",
        "numero_documento",
        "pasaporte",
        "carne_extranjeria",
        "nombre",
        "nombres",
        "apellido",
        "apellidos",
        "nombre_completo",
        "correo",
        "email",
        "telefono",
        "celular",
        "direccion",
    }
)
"""Nombres de columna que se tratan siempre como identificadores directos."""


class IdentificadorEnExportacion(ErrorSuficiencia):
    def __init__(self, columnas: tuple[str, ...]) -> None:
        self.columnas = columnas
        super().__init__(
            f"La exportación contiene columnas identificadoras: {', '.join(columnas)}.",
            "Elimínelas o seudonimícelas antes de exportar; los reportes no pueden "
            "contener identificadores directos (RNF-05).",
        )


def _normalizar(nombre: str) -> str:
    return nombre.strip().lower().replace(" ", "_").replace("-", "_")


def columnas_identificadoras(
    columnas: Iterable[str], identificadores_declarados: Iterable[str] = ()
) -> tuple[str, ...]:
    """Columnas que son identificadores: las declaradas en el diccionario y las de la lista fija."""
    prohibidas = NOMBRES_IDENTIFICADORES | {_normalizar(c) for c in identificadores_declarados}
    return tuple(c for c in columnas if _normalizar(str(c)) in prohibidas)


def exigir_sin_identificadores(
    columnas: Iterable[str], identificadores_declarados: Iterable[str] = ()
) -> None:
    encontradas = columnas_identificadoras(columnas, identificadores_declarados)
    if encontradas:
        raise IdentificadorEnExportacion(encontradas)
