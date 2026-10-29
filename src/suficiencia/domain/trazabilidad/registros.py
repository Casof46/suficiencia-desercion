"""Registros de trazabilidad (M6): experimentos, decisiones y accesos a la prueba.

Los registros solo se agregan; nunca se editan ni se borran (invariante de M6).
Cada registro guarda la huella de su contenido encadenada con la del anterior:
si alguien modifica un registro fuera del programa, la verificación lo detecta.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from suficiencia.domain.errores import ConfiguracionInvalida

HUELLA_INICIAL = "0" * 64
"""Huella "anterior" del primer registro de cada tipo."""

_CODIGO_DECISION = re.compile(r"DP-\d{2}[a-m]?")


class TipoRegistro(Enum):
    EXPERIMENTO = "experimentos"
    DECISION = "decisiones"
    ACCESO = "accesos"


class ModoExperimento(Enum):
    """Modos de la especificación (CU-06)."""

    EXPLORATORIO = "exploratorio"
    CONFIRMATORIO = "confirmatorio"


class EstadoCorrida(Enum):
    EXITOSA = "exitosa"
    FALLIDA = "fallida"
    DESCARTADA = "descartada"


def _invalido(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(causa, "Corrija los datos del registro y repita la operación.")


def _texto(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise _invalido(f"El campo '{campo}' del registro no puede estar vacío.")
    return valor.strip()


@dataclass(frozen=True)
class Entorno:
    """Entorno de ejecución (RNF-17): Python, sistema, bloqueo de dependencias,
    commit y paralelismo."""

    python: str
    sistema: str
    huella_bloqueo: str | None
    commit: str | None
    cambios_sin_commit: bool | None
    nucleos: int | None
    hilos: dict[str, str]
    paquetes: dict[str, str]


@dataclass(frozen=True)
class RegistroExperimento:
    """Una corrida, exitosa o no (RF-M6-01, RF-M3-11)."""

    identificador: str
    modo: ModoExperimento
    estado: EstadoCorrida
    version_protocolo: str | None
    configuracion: dict[str, Any]
    semillas: dict[str, int]
    huella_datos: str | None
    entorno: Entorno
    resultados: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        _texto(self.identificador, "identificador")
        if self.modo is ModoExperimento.CONFIRMATORIO and not self.version_protocolo:
            raise _invalido("Un experimento confirmatorio necesita la versión del protocolo.")
        if self.estado is EstadoCorrida.FALLIDA and not self.error:
            raise _invalido("Una corrida fallida debe registrar su error.")
        for nombre, semilla in self.semillas.items():
            if isinstance(semilla, bool) or not isinstance(semilla, int):
                raise _invalido(f"La semilla '{nombre}' debe ser un entero.")

    def contenido(self) -> dict[str, Any]:
        datos = asdict(self)
        datos["modo"] = self.modo.value
        datos["estado"] = self.estado.value
        return datos


@dataclass(frozen=True)
class RegistroDecision:
    """Decisión metodológica DP-xx (RF-M6-05)."""

    codigo: str
    decision: str
    justificacion: str
    responsable: str
    observaciones: str | None = None

    def __post_init__(self) -> None:
        if not _CODIGO_DECISION.fullmatch(self.codigo):
            raise _invalido(
                f"'{self.codigo}' no es un código de decisión (formato DP-01 o DP-01d)."
            )
        _texto(self.decision, "decision")
        _texto(self.justificacion, "justificacion")
        _texto(self.responsable, "responsable")

    def contenido(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegistroAcceso:
    """Intento de acceso a la partición de prueba, permitido o no (RF-M2-07, RF-M6-06)."""

    operacion: str
    motivo: str
    permitido: bool

    def __post_init__(self) -> None:
        _texto(self.operacion, "operacion")
        _texto(self.motivo, "motivo")

    def contenido(self) -> dict[str, Any]:
        return asdict(self)


def json_canonico(contenido: dict[str, Any]) -> str:
    """JSON con claves ordenadas y sin espacios: el mismo contenido da el mismo texto."""
    return json.dumps(contenido, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def huella_encadenada(huella_anterior: str, fecha: str, contenido_json: str) -> str:
    """Huella SHA-256 de un registro, que incluye la del registro anterior."""
    mensaje = f"{huella_anterior}\n{fecha}\n{contenido_json}".encode()
    return hashlib.sha256(mensaje).hexdigest()


@dataclass(frozen=True)
class RegistroGuardado:
    """Un registro tal como quedó guardado."""

    tipo: TipoRegistro
    numero: int
    fecha: str
    contenido: dict[str, Any]
    huella_anterior: str
    huella: str


@dataclass(frozen=True)
class ProblemaIntegridad:
    tipo: TipoRegistro
    numero: int
    descripcion: str


def verificar_cadena(
    tipo: TipoRegistro, registros: list[RegistroGuardado]
) -> tuple[ProblemaIntegridad, ...]:
    """Recalcula la cadena de huellas de un tipo de registro y devuelve las roturas."""
    problemas: list[ProblemaIntegridad] = []
    anterior = HUELLA_INICIAL
    esperado = 1
    for registro in registros:
        if registro.numero != esperado:
            problemas.append(
                ProblemaIntegridad(tipo, registro.numero, f"falta el registro n.º {esperado}")
            )
            esperado = registro.numero
        if registro.huella_anterior != anterior:
            problemas.append(
                ProblemaIntegridad(tipo, registro.numero, "no continúa la cadena de huellas")
            )
        calculada = huella_encadenada(
            registro.huella_anterior, registro.fecha, json_canonico(registro.contenido)
        )
        if calculada != registro.huella:
            problemas.append(
                ProblemaIntegridad(tipo, registro.numero, "su contenido fue modificado")
            )
        anterior = registro.huella
        esperado += 1
    return tuple(problemas)
