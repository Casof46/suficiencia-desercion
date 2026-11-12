"""Configuraciones congeladas con huella (M4; RF-M4-12, RF-M4-09; PI-09).

Una configuración congelada fija todo lo que la evaluación final usará:
algoritmo, hiperparámetros, preprocesamiento, variables, umbral, calibración,
semilla y datos de reentrenamiento. Su huella se calcula sobre ese contenido en
forma canónica. Antes de abrir la prueba, la evaluación final comprueba que cada
configuración coincida con la huella con que se congeló (CU-08, pasos 2 y 3).

Congelar es un paso confirmatorio (CU-07): exige un protocolo aprobado vigente.
Este módulo no entrena modelos ni elige configuraciones; esas partes llegan en
fases posteriores (DP-06, DP-09, DP-10).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from suficiencia.domain.errores import ConfiguracionInvalida, ErrorSuficiencia
from suficiencia.domain.evaluacion.protocolo import HistorialProtocolo, exigir_vigente
from suficiencia.domain.huella import Huella
from suficiencia.domain.trazabilidad.registros import json_canonico


class RolConfiguracion(Enum):
    """Papel de la configuración en la evaluación final (sección 4 de la especificación)."""

    SELECCIONADA = "seleccionada"
    REFERENCIA_R0 = "referencia_r0"
    CONTROL = "control"


_CAMPOS = (
    "identificador",
    "rol",
    "escenario",
    "algoritmo",
    "hiperparametros",
    "preprocesamiento",
    "variables",
    "umbral",
    "calibracion",
    "semilla",
    "datos_reentrenamiento",
    "version_protocolo",
    "ficticio",
)


class HuellaNoCoincide(ErrorSuficiencia):
    """La configuración que se quiere evaluar no es la que se congeló (PI-09)."""

    def __init__(self, identificador: str) -> None:
        super().__init__(
            f"La configuración '{identificador}' no coincide con la huella con que se congeló.",
            "Evalúe la configuración tal como se congeló. Si debe cambiar, el cambio es "
            "una desviación del protocolo y exige congelarla de nuevo con otro identificador.",
        )


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Configuración para congelar: {causa}",
        "Complete todos los campos de la configuración (RF-M4-12).",
    )


@dataclass(frozen=True)
class ConfiguracionCongelable:
    """Todo lo que define una configuración para la evaluación final (RF-M4-12).

    Ningún campo tiene valor por omisión. Una calibración "ninguna" debe
    declararse explícitamente en ``calibracion``.
    """

    identificador: str
    rol: RolConfiguracion
    escenario: str
    algoritmo: str
    hiperparametros: Mapping[str, Any]
    preprocesamiento: Mapping[str, Any]
    variables: tuple[str, ...]
    umbral: float
    calibracion: Mapping[str, Any]
    semilla: int
    datos_reentrenamiento: str
    version_protocolo: int
    ficticio: bool

    def __post_init__(self) -> None:
        for campo in ("identificador", "escenario", "algoritmo", "datos_reentrenamiento"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise _invalida(f"'{campo}' no puede estar vacío.")
        if not self.variables or not all(isinstance(v, str) and v for v in self.variables):
            raise _invalida("'variables' debe listar al menos una variable.")
        if len(set(self.variables)) != len(self.variables):
            raise _invalida("'variables' repite una variable.")
        if (
            isinstance(self.umbral, bool)
            or not isinstance(self.umbral, (int, float))
            or not math.isfinite(self.umbral)
        ):
            raise _invalida("'umbral' debe ser un número finito.")
        if isinstance(self.semilla, bool) or not isinstance(self.semilla, int):
            raise _invalida("'semilla' debe ser un entero.")
        if isinstance(self.version_protocolo, bool) or not isinstance(self.version_protocolo, int):
            raise _invalida("'version_protocolo' debe ser un entero.")
        if not isinstance(self.ficticio, bool):
            raise _invalida("'ficticio' debe ser sí o no.")
        for campo in ("hiperparametros", "preprocesamiento", "calibracion"):
            if not isinstance(getattr(self, campo), Mapping):
                raise _invalida(f"'{campo}' debe ser un conjunto de campos.")

    def a_datos(self) -> dict[str, Any]:
        return {
            "identificador": self.identificador,
            "rol": self.rol.value,
            "escenario": self.escenario,
            "algoritmo": self.algoritmo,
            "hiperparametros": dict(self.hiperparametros),
            "preprocesamiento": dict(self.preprocesamiento),
            "variables": list(self.variables),
            "umbral": float(self.umbral),
            "calibracion": dict(self.calibracion),
            "semilla": self.semilla,
            "datos_reentrenamiento": self.datos_reentrenamiento,
            "version_protocolo": self.version_protocolo,
            "ficticio": self.ficticio,
        }

    def huella(self) -> Huella:
        """Huella del contenido canónico: cualquier cambio en cualquier campo la cambia."""
        return Huella.de_bytes(json_canonico(self.a_datos()).encode())


def configuracion_desde_datos(datos: Any) -> ConfiguracionCongelable:
    """Construye una configuración a partir de datos (archivo o registro)."""
    if not isinstance(datos, Mapping):
        raise _invalida("debe ser un conjunto de campos.")
    faltan = [c for c in _CAMPOS if c not in datos]
    if faltan:
        raise _invalida(f"faltan los campos: {', '.join(faltan)}.")
    extra = sorted(set(datos) - set(_CAMPOS))
    if extra:
        raise _invalida(f"campos desconocidos: {', '.join(extra)}.")
    nulos = [c for c in _CAMPOS if datos[c] is None]
    if nulos:
        raise _invalida(f"los campos {', '.join(nulos)} no tienen valor.")
    try:
        rol = RolConfiguracion(datos["rol"])
    except ValueError:
        opciones = ", ".join(r.value for r in RolConfiguracion)
        raise _invalida(f"'rol' = {datos['rol']!r} no es válido. Opciones: {opciones}.") from None
    if not isinstance(datos["variables"], (list, tuple)):
        raise _invalida("'variables' debe ser una lista.")
    return ConfiguracionCongelable(
        identificador=datos["identificador"],
        rol=rol,
        escenario=datos["escenario"],
        algoritmo=datos["algoritmo"],
        hiperparametros=datos["hiperparametros"],
        preprocesamiento=datos["preprocesamiento"],
        variables=tuple(datos["variables"]),
        umbral=datos["umbral"],
        calibracion=datos["calibracion"],
        semilla=datos["semilla"],
        datos_reentrenamiento=datos["datos_reentrenamiento"],
        version_protocolo=datos["version_protocolo"],
        ficticio=datos["ficticio"],
    )


@dataclass(frozen=True)
class RegistroCongelamiento:
    """Una configuración congelada, tal como se guarda en el registro."""

    configuracion: dict[str, Any]
    huella: str

    def __post_init__(self) -> None:
        Huella(self.huella)

    def contenido(self) -> dict[str, Any]:
        return {"configuracion": self.configuracion, "huella": self.huella}


def congelar(
    configuracion: ConfiguracionCongelable,
    historial: HistorialProtocolo,
    congeladas: Mapping[str, str],
) -> RegistroCongelamiento:
    """Prepara el registro de congelamiento (CU-07; RF-M4-12).

    ``congeladas`` asocia los identificadores ya congelados con su huella.

    Raises:
        SinProtocoloVigente: si no hay protocolo vigente o la configuración declara otra versión.
        ConfiguracionInvalida: si el identificador ya está congelado.
    """
    exigir_vigente(historial, str(configuracion.version_protocolo), "Congelar una configuración")
    if configuracion.identificador in congeladas:
        raise ConfiguracionInvalida(
            f"La configuración '{configuracion.identificador}' ya está congelada.",
            "Una configuración congelada no cambia. Use otro identificador; si reemplaza a "
            "la anterior, registre la desviación del protocolo.",
        )
    return RegistroCongelamiento(configuracion.a_datos(), configuracion.huella().valor)


@dataclass(frozen=True)
class PreparacionEvaluacionFinal:
    """Resultado de las comprobaciones previas a abrir la prueba (CU-08, pasos 2 y 3)."""

    version_protocolo: int
    huella_protocolo: str
    configuraciones: tuple[tuple[str, str], ...]
    ficticio: bool


def preparar_evaluacion_final(
    historial: HistorialProtocolo,
    configuraciones: Sequence[ConfiguracionCongelable],
    congeladas: Mapping[str, str],
) -> PreparacionEvaluacionFinal:
    """Comprueba lo que CU-08 exige antes de abrir la prueba.

    No abre la prueba ni evalúa nada: solo verifica.

    Raises:
        SinProtocoloVigente: sin protocolo aprobado vigente, o si una configuración
            declara una versión que no es la vigente (PU-05).
        ConfiguracionInvalida: si no hay configuraciones o alguna no se congeló.
        HuellaNoCoincide: si alguna difiere de su huella congelada (PI-09).
    """
    vigente = exigir_vigente(historial, None, "La evaluación final")
    if not configuraciones:
        raise ConfiguracionInvalida(
            "La evaluación final no recibió configuraciones.",
            "Entregue las configuraciones congeladas en CU-07.",
        )
    verificadas = []
    for configuracion in configuraciones:
        exigir_vigente(historial, str(configuracion.version_protocolo), "La evaluación final")
        congelada = congeladas.get(configuracion.identificador)
        if congelada is None:
            raise ConfiguracionInvalida(
                f"La configuración '{configuracion.identificador}' no está congelada.",
                "Congélela antes de la evaluación final (CU-07).",
            )
        if configuracion.huella().valor != congelada:
            raise HuellaNoCoincide(configuracion.identificador)
        verificadas.append((configuracion.identificador, congelada))
    return PreparacionEvaluacionFinal(
        version_protocolo=vigente.numero,
        huella_protocolo=vigente.huella.valor,
        configuraciones=tuple(verificadas),
        ficticio=vigente.contenido.ficticio or any(c.ficticio for c in configuraciones),
    )
