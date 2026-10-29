"""Seudonimización de identificadores (RF-M1-04, PU-08).

Reemplaza las columnas con rol identificador por un seudónimo calculado con
HMAC-SHA256 y una clave secreta: el mismo identificador produce siempre el mismo
seudónimo con la misma clave, y sin la clave no puede recalcularse. No se guarda
ninguna tabla de correspondencia.

Es un mecanismo **provisional**: el método definitivo y la custodia de la clave
dependen de DP-14. La seudonimización no equivale a anonimización: los datos
seudonimizados siguen siendo datos personales.

La clave nunca se escribe en archivos ni en registros. Proviene de la variable
de entorno ``SUFICIENCIA_CLAVE_SEUDONIMO`` o se genera al azar para una sola
ejecución (clave efímera; los seudónimos no se pueden reproducir después).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

import pandas as pd

from suficiencia.domain.datos.diccionario import COLUMNA_SEUDONIMO
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente

VARIABLE_ENTORNO_CLAVE = "SUFICIENCIA_CLAVE_SEUDONIMO"
LONGITUD_MINIMA_CLAVE = 32
LONGITUD_SEUDONIMO = 24
"""Caracteres hexadecimales del seudónimo (96 bits)."""


class SeudonimizadorHmac:
    """Implementa el puerto ``Seudonimizador`` con HMAC-SHA256."""

    def __init__(self, clave: bytes) -> None:
        if len(clave) < LONGITUD_MINIMA_CLAVE:
            raise ConfiguracionInvalida(
                f"La clave de seudonimización es demasiado corta (mínimo "
                f"{LONGITUD_MINIMA_CLAVE} caracteres).",
                "Use una clave larga y aleatoria, o la opción de clave efímera.",
            )
        self._clave = clave

    @classmethod
    def con_clave_efimera(cls) -> SeudonimizadorHmac:
        return cls(secrets.token_bytes(LONGITUD_MINIMA_CLAVE))

    @classmethod
    def desde_entorno(cls) -> SeudonimizadorHmac:
        valor = os.environ.get(VARIABLE_ENTORNO_CLAVE)
        if not valor:
            raise DecisionPendiente(
                "DP-14",
                f"la clave de seudonimización (variable de entorno {VARIABLE_ENTORNO_CLAVE}; "
                "con datos sintéticos puede usarse una clave efímera)",
            )
        return cls(valor.encode("utf-8"))

    def seudonimo(self, valores: tuple[str, ...]) -> str:
        mensaje = "\x1f".join(valores).encode("utf-8")
        return hmac.new(self._clave, mensaje, hashlib.sha256).hexdigest()[:LONGITUD_SEUDONIMO]

    def seudonimizar(self, tabla: pd.DataFrame, identificadores: tuple[str, ...]) -> pd.DataFrame:
        """Devuelve una tabla nueva sin los identificadores y con la columna ``seudonimo``.

        Si una fila no tiene identificador, su seudónimo queda vacío y la auditoría
        lo marca como error. La tabla original no se modifica.
        """
        presentes = [c for c in identificadores if c in tabla.columns]
        resultado = tabla.drop(columns=presentes)
        if not presentes:
            return resultado
        textos = tabla[presentes].astype("string").apply(lambda s: s.str.strip())
        seudonimos = [
            None
            if any(pd.isna(v) or v == "" for v in fila)
            else self.seudonimo(tuple(str(v) for v in fila))
            for fila in textos.itertuples(index=False, name=None)
        ]
        resultado.insert(0, COLUMNA_SEUDONIMO, pd.Series(seudonimos, index=tabla.index))
        return resultado
