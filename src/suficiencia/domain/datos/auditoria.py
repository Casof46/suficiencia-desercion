"""Validación contra el diccionario y auditoría de calidad (RF-M1-02, RF-M1-03, RF-M1-08).

Recibe una tabla ya seudonimizada en la que todas las celdas son texto, tal como
la entrega el lector. Convierte cada columna al tipo declarado y cuenta los
problemas. Un problema crítico (columna faltante o no declarada, tipo incorrecto,
valor fuera de dominio, obligatorio vacío o clave repetida) impide pasar a M2
(PU-14, PU-17).

Antes del sellado de la prueba, el informe no expone la distribución de la clase
(RF-M1-03): de las columnas con rol ``objetivo`` solo informa nulos y valores
inválidos, nunca categorías, conteos por valor, cardinalidad ni rangos. Los
problemas se señalan por número de fila, sin mostrar valores.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from suficiencia.domain.datos.diccionario import (
    COLUMNA_SEUDONIMO,
    VALOR_ORIGEN_SINTETICO,
    DefinicionVariable,
    Diccionario,
    Rol,
    TipoDato,
)
from suficiencia.domain.errores import ErrorSuficiencia

MAXIMO_FILAS_DE_EJEMPLO = 5
_ENTERO = re.compile(r"[+-]?\d+")
_DECIMAL = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?")
_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}( 00:00:00)?")
_VERDADERO = {"true", "1", "si", "sí", "verdadero"}
_FALSO = {"false", "0", "no", "falso"}


@dataclass(frozen=True)
class AuditoriaColumna:
    """Resultado de una columna. ``cardinalidad``, ``minimo`` y ``maximo`` son
    ``None`` para las columnas del objetivo."""

    nombre: str
    rol: str
    tipo: str
    nulos: int
    tipo_invalido: int
    fuera_de_dominio: int
    cardinalidad: int | None
    minimo: float | None
    maximo: float | None
    filas_con_problemas: tuple[int, ...]


@dataclass(frozen=True)
class InformeAuditoria:
    n_filas: int
    n_columnas: int
    columnas: tuple[AuditoriaColumna, ...]
    duplicados_clave: int
    filas_duplicadas: int
    sintetico: bool
    errores_criticos: tuple[str, ...]
    alertas: tuple[str, ...]

    @property
    def apto_para_m2(self) -> bool:
        return not self.errores_criticos


@dataclass(frozen=True)
class ResultadoAuditoria:
    informe: InformeAuditoria
    tabla: pd.DataFrame
    """Tabla con los tipos declarados; los valores inválidos quedan vacíos."""


class AuditoriaConErrores(ErrorSuficiencia):
    """La auditoría tiene errores críticos y el dataset no puede pasar a M2 (RF-M1-08)."""

    def __init__(self, informe: InformeAuditoria) -> None:
        self.informe = informe
        super().__init__(
            f"La auditoría tiene {len(informe.errores_criticos)} error(es) crítico(s): "
            + " ".join(informe.errores_criticos),
            "Corrija el archivo fuente o el diccionario e impórtelo de nuevo.",
        )


def exigir_apto(informe: InformeAuditoria) -> None:
    """Detiene el avance a M2 si la auditoría tiene errores críticos (PU-17)."""
    if not informe.apto_para_m2:
        raise AuditoriaConErrores(informe)


def _filas(mascara: pd.Series) -> tuple[int, ...]:
    """Números de fila (desde 1, sin contar el encabezado) donde la máscara es verdadera."""
    posiciones = [i + 1 for i, valor in enumerate(mascara.tolist()) if valor]
    return tuple(posiciones[:MAXIMO_FILAS_DE_EJEMPLO])


def _normalizar(serie: pd.Series) -> pd.Series:
    texto = serie.astype("string").str.strip()
    return texto.mask(texto == "")


def _convertir(
    texto: pd.Series[Any], variable: DefinicionVariable
) -> tuple[pd.Series[Any], pd.Series[bool]]:
    """Devuelve la serie con el tipo declarado y la máscara de valores de tipo inválido."""
    presente = texto.notna()
    tipo = variable.tipo
    convertida: pd.Series[Any]
    if tipo is TipoDato.ENTERO:
        valido = texto.str.fullmatch(_ENTERO.pattern).fillna(False).astype(bool)
        convertida = pd.to_numeric(texto.where(valido), errors="coerce").astype("Int64")
    elif tipo is TipoDato.DECIMAL:
        valido = texto.str.fullmatch(_DECIMAL.pattern).fillna(False).astype(bool)
        convertida = pd.to_numeric(texto.where(valido), errors="coerce").astype("Float64")
    elif tipo is TipoDato.BOOLEANO:
        minuscula = texto.str.lower()
        valido = minuscula.isin(_VERDADERO | _FALSO).fillna(False).astype(bool)
        convertida = minuscula.map(
            lambda v: True if v in _VERDADERO else (False if v in _FALSO else pd.NA)
        ).astype("boolean")
    elif tipo is TipoDato.FECHA:
        valido = texto.str.fullmatch(_FECHA.pattern).fillna(False).astype(bool)
        convertida = pd.to_datetime(
            texto.where(valido).str.slice(0, 10), format="%Y-%m-%d", errors="coerce"
        )
        valido = valido & convertida.notna()
    else:
        valido = presente
        convertida = texto
    return convertida, presente & ~valido


def _fuera_de_dominio(convertida: pd.Series, variable: DefinicionVariable) -> pd.Series:
    presente = convertida.notna()
    fuera = pd.Series(False, index=convertida.index)
    if variable.minimo is not None:
        fuera |= presente & (convertida < variable.minimo).fillna(False).astype(bool)
    if variable.maximo is not None:
        fuera |= presente & (convertida > variable.maximo).fillna(False).astype(bool)
    if variable.valores is not None:
        fuera |= presente & ~convertida.isin(variable.valores).fillna(False).astype(bool)
    if variable.patron is not None:
        coincide = convertida.str.fullmatch(variable.patron).fillna(False).astype(bool)
        fuera |= presente & ~coincide
    return fuera


def _auditar_columna(
    texto: pd.Series, variable: DefinicionVariable, criticos: list[str], alertas: list[str]
) -> tuple[AuditoriaColumna, pd.Series]:
    nombre = variable.nombre
    convertida, invalida = _convertir(texto, variable)
    fuera = _fuera_de_dominio(convertida, variable)
    nulos_mascara = texto.isna()
    nulos = int(nulos_mascara.sum())

    if nulos and variable.obligatoria:
        criticos.append(f"'{nombre}' es obligatoria y tiene {nulos} valor(es) vacío(s).")
    elif nulos:
        alertas.append(f"'{nombre}' tiene {nulos} valor(es) vacío(s).")
    if int(invalida.sum()):
        criticos.append(
            f"'{nombre}' tiene {int(invalida.sum())} valor(es) que no son de tipo "
            f"{variable.tipo.value}."
        )
    if int(fuera.sum()):
        criticos.append(f"'{nombre}' tiene {int(fuera.sum())} valor(es) fuera de su dominio.")

    validos = convertida.mask(fuera)
    es_objetivo = variable.rol is Rol.OBJETIVO
    numerica = variable.tipo in {TipoDato.ENTERO, TipoDato.DECIMAL}
    minimo = maximo = None
    if numerica and not es_objetivo and validos.notna().any():
        minimo, maximo = float(validos.min()), float(validos.max())
    columna = AuditoriaColumna(
        nombre=nombre,
        rol=variable.rol.value,
        tipo=variable.tipo.value,
        nulos=nulos,
        tipo_invalido=int(invalida.sum()),
        fuera_de_dominio=int(fuera.sum()),
        cardinalidad=None if es_objetivo else int(validos.nunique(dropna=True)),
        minimo=minimo,
        maximo=maximo,
        filas_con_problemas=_filas(invalida | fuera | (nulos_mascara & variable.obligatoria)),
    )
    return columna, validos


def auditar(tabla: pd.DataFrame, diccionario: Diccionario) -> ResultadoAuditoria:
    """Valida la tabla seudonimizada contra el diccionario y audita su calidad."""
    criticos: list[str] = []
    alertas: list[str] = []
    declaradas = [v for v in diccionario.variables if v.rol is not Rol.IDENTIFICADOR]
    esperadas = [v.nombre for v in declaradas]
    if diccionario.identificadores:
        esperadas.append(COLUMNA_SEUDONIMO)

    for columna in diccionario.identificadores:
        if columna in tabla.columns:
            criticos.append(
                f"La columna identificadora '{columna}' sigue presente: no se seudonimizó."
            )
    faltantes = [c for c in esperadas if c not in tabla.columns]
    for columna in faltantes:
        criticos.append(f"Falta la columna '{columna}' declarada en el diccionario.")
    for columna in tabla.columns:
        if columna not in esperadas and columna not in diccionario.identificadores:
            criticos.append(
                f"La columna '{columna}' no está en el diccionario. No se procesa: "
                "revise si contiene datos personales y declárela o elimínela."
            )

    tipada = pd.DataFrame(index=tabla.index)
    auditorias: list[AuditoriaColumna] = []
    if COLUMNA_SEUDONIMO in tabla.columns:
        seudonimo = _normalizar(tabla[COLUMNA_SEUDONIMO])
        vacios = int(seudonimo.isna().sum())
        if vacios:
            criticos.append(f"{vacios} fila(s) sin identificador: no tienen seudónimo.")
        tipada[COLUMNA_SEUDONIMO] = seudonimo
    for variable in declaradas:
        if variable.nombre not in tabla.columns:
            continue
        auditada, validos = _auditar_columna(
            _normalizar(tabla[variable.nombre]), variable, criticos, alertas
        )
        auditorias.append(auditada)
        tipada[variable.nombre] = validos

    clave = [c for c in diccionario.clave_seudonimizada() if c in tipada.columns]
    duplicados_clave = int(tipada.duplicated(subset=clave).sum()) if clave else 0
    if duplicados_clave:
        criticos.append(
            f"{duplicados_clave} fila(s) repiten la clave ({', '.join(clave)}) de otra fila."
        )
    filas_duplicadas = int(tabla.duplicated().sum())
    if filas_duplicadas:
        alertas.append(f"{filas_duplicadas} fila(s) son copias exactas de otra.")

    origen = diccionario.columna_origen
    sintetico = (
        origen is not None
        and origen in tipada.columns
        and len(tipada) > 0
        and bool((tipada[origen] == VALOR_ORIGEN_SINTETICO).fillna(False).all())
    )
    if len(tabla) == 0:
        criticos.append("La tabla no tiene filas.")

    informe = InformeAuditoria(
        n_filas=len(tabla),
        n_columnas=len(tabla.columns),
        columnas=tuple(auditorias),
        duplicados_clave=duplicados_clave,
        filas_duplicadas=filas_duplicadas,
        sintetico=sintetico,
        errores_criticos=tuple(criticos),
        alertas=tuple(alertas),
    )
    return ResultadoAuditoria(informe=informe, tabla=tipada)
