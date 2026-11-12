"""Protocolo confirmatorio versionado y desviaciones (M4; RF-M4-04, 05, 13; PU-05, PU-06).

El protocolo se guarda como una secuencia de registros de solo agregar: cada
borrador y cada aprobación es un registro nuevo. El estado de cada versión
(borrador, aprobado, reemplazado) se reconstruye leyendo esa secuencia. Por eso un
protocolo aprobado no puede editarse: cambiarlo exige un borrador de una versión
nueva y su aprobación, que reemplaza a la anterior.

Si ya existen experimentos confirmatorios cuando se aprueba una versión nueva, la
aprobación exige registrar una desviación con su justificación; la desviación
nombra los experimentos afectados (RF-M4-13).

Para aprobar, el protocolo debe contener lo decidido en cada decisión que la
especificación exige antes de CU-05: DP-06, 07, 08, 09, 10, 12, 17, 19 y 20. El
motor solo ejecuta el criterio de suficiencia (DP-08); el resto queda registrado
como texto hasta que lo usen fases posteriores.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente, ErrorSuficiencia
from suficiencia.domain.evaluacion.suficiencia import (
    CriterioSuficiencia,
    ProcedimientoMultiplicidad,
    ResultadoEscenario,
    ResultadoSuficiencia,
    aplicar_regla,
    criterio_desde_datos,
)
from suficiencia.domain.huella import Huella
from suficiencia.domain.trazabilidad.registros import ModoExperimento, json_canonico

DECISIONES_DEL_PROTOCOLO = (
    "DP-06",
    "DP-07",
    "DP-08",
    "DP-09",
    "DP-10",
    "DP-12",
    "DP-17",
    "DP-19",
    "DP-20",
)
"""Decisiones que deben estar resueltas antes de aprobar el protocolo (CU-05)."""

_CODIGO_DECISION = re.compile(r"DP-\d{2}[a-m]?")
_CLAVES_CONTENIDO = {"ficticio", "criterio_suficiencia", "decisiones"}


class EstadoProtocolo(Enum):
    BORRADOR = "borrador"
    APROBADO = "aprobado"
    REEMPLAZADO = "reemplazado"


class AccionProtocolo(Enum):
    BORRADOR = "borrador"
    APROBACION = "aprobacion"


class ProtocoloInmutable(ErrorSuficiencia):
    """Se intentó modificar una versión aprobada o reemplazada."""

    def __init__(self, version: int, estado: EstadoProtocolo) -> None:
        super().__init__(
            f"La versión {version} del protocolo está en estado «{estado.value}» y no puede "
            "modificarse.",
            "Para cambiarla, guarde un borrador de una versión nueva y apruébelo; si ya hay "
            "experimentos confirmatorios, la aprobación exigirá registrar una desviación.",
        )


class SinProtocoloVigente(ErrorSuficiencia):
    """Una operación confirmatoria no tiene protocolo aprobado vigente (RF-M4-05)."""

    def __init__(self, operacion: str, detalle: str) -> None:
        super().__init__(
            f"{operacion} requiere un protocolo aprobado vigente: {detalle}",
            "Apruebe el protocolo confirmatorio (CU-05) antes de cualquier operación "
            "confirmatoria. En modo exploratorio no se necesita.",
        )


class DesviacionRequerida(ErrorSuficiencia):
    """Se aprueba una versión nueva con experimentos confirmatorios ya registrados."""

    def __init__(self, afectados: Sequence[str]) -> None:
        super().__init__(
            f"Ya hay {len(afectados)} experimento(s) confirmatorio(s) con la versión anterior "
            "del protocolo; aprobar otra versión es una desviación.",
            "Registre la desviación con su descripción y su justificación al aprobar "
            "(RF-M4-13). Los experimentos afectados quedarán marcados.",
        )


def _invalido(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Protocolo: {causa}",
        "Corrija el protocolo; el ejemplo de las pruebas está en "
        "config/ejemplos/protocolo_ficticio.yaml.",
    )


def _texto(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise _invalido(f"'{campo}' no puede estar vacío.")
    return valor.strip()


# --- Contenido -------------------------------------------------------------------


@dataclass(frozen=True)
class ContenidoProtocolo:
    """Lo que el protocolo fija: el criterio ejecutable y lo decidido en cada DP-xx.

    ``ficticio`` declara si el protocolo es un ejemplo inventado. Un ejemplo
    ficticio nunca se aprueba en el registro del proyecto (lo impide el servicio).
    """

    ficticio: bool
    criterio: CriterioSuficiencia
    decisiones: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.ficticio, bool):
            raise _invalido("'ficticio' debe ser sí o no.")
        for codigo, texto in self.decisiones.items():
            if not _CODIGO_DECISION.fullmatch(codigo):
                raise _invalido(f"'{codigo}' no es un código de decisión (DP-01 o DP-08a).")
            _texto(texto, f"decisiones.{codigo}")

    def a_datos(self) -> dict[str, Any]:
        return {
            "ficticio": self.ficticio,
            "criterio_suficiencia": self.criterio.a_datos(),
            "decisiones": dict(sorted(self.decisiones.items())),
        }

    def huella(self) -> Huella:
        """Huella del contenido en forma canónica: no depende del orden ni del formato."""
        return Huella.de_bytes(json_canonico(self.a_datos()).encode())

    def decisiones_faltantes(self) -> tuple[str, ...]:
        return tuple(d for d in DECISIONES_DEL_PROTOCOLO if d not in self.decisiones)


def contenido_desde_datos(datos: Any) -> ContenidoProtocolo:
    """Construye el contenido del protocolo a partir de datos (YAML o registro).

    Raises:
        DecisionPendiente: si un campo del criterio vale ``null``.
        ConfiguracionInvalida: si la estructura no es válida.
    """
    if not isinstance(datos, Mapping):
        raise _invalido("el contenido debe ser un conjunto de campos.")
    extra = sorted(set(datos) - _CLAVES_CONTENIDO)
    if extra:
        raise _invalido(f"campos desconocidos: {', '.join(extra)}.")
    faltan = sorted(_CLAVES_CONTENIDO - set(datos))
    if faltan:
        raise _invalido(f"faltan los campos: {', '.join(faltan)}.")
    if datos["criterio_suficiencia"] is None:
        raise DecisionPendiente("DP-08", "el criterio de suficiencia del protocolo")
    decisiones = datos["decisiones"] if datos["decisiones"] is not None else {}
    if not isinstance(decisiones, Mapping):
        raise _invalido("'decisiones' debe asociar cada código DP-xx con lo decidido.")
    return ContenidoProtocolo(
        ficticio=datos["ficticio"],
        criterio=criterio_desde_datos(datos["criterio_suficiencia"]),
        decisiones={str(k): v for k, v in decisiones.items()},
    )


# --- Registros -------------------------------------------------------------------


@dataclass(frozen=True)
class RegistroProtocolo:
    """Un borrador o una aprobación de una versión del protocolo."""

    accion: AccionProtocolo
    version: int
    huella: str
    protocolo: dict[str, Any] | None
    responsable: str | None

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise _invalido("la versión debe ser un entero positivo.")
        Huella(self.huella)
        if self.accion is AccionProtocolo.BORRADOR and self.protocolo is None:
            raise _invalido("un borrador debe incluir el contenido.")
        if self.accion is AccionProtocolo.APROBACION:
            if self.protocolo is not None:
                raise _invalido("una aprobación no repite el contenido; lo identifica su huella.")
            _texto(self.responsable, "responsable")

    def contenido(self) -> dict[str, Any]:
        datos = asdict(self)
        datos["accion"] = self.accion.value
        return datos


@dataclass(frozen=True)
class RegistroDesviacion:
    """Cambio del protocolo después de iniciar los experimentos confirmatorios (RF-M4-13)."""

    version_anterior: int
    version_nueva: int
    descripcion: str
    justificacion: str
    responsable: str
    resultados_afectados: tuple[str, ...]

    def __post_init__(self) -> None:
        _texto(self.descripcion, "descripcion")
        _texto(self.justificacion, "justificacion")
        _texto(self.responsable, "responsable")
        if self.version_nueva <= self.version_anterior:
            raise _invalido("la versión nueva de una desviación debe ser posterior.")

    def contenido(self) -> dict[str, Any]:
        datos = asdict(self)
        datos["resultados_afectados"] = list(self.resultados_afectados)
        return datos


@dataclass(frozen=True)
class VersionProtocolo:
    numero: int
    estado: EstadoProtocolo
    contenido: ContenidoProtocolo
    huella: Huella
    responsable_aprobacion: str | None


@dataclass(frozen=True)
class HistorialProtocolo:
    """Versiones del protocolo reconstruidas a partir de sus registros."""

    versiones: tuple[VersionProtocolo, ...]

    @classmethod
    def desde_registros(cls, registros: Sequence[Mapping[str, Any]]) -> HistorialProtocolo:
        """Reconstruye las versiones a partir del contenido de los registros, en orden.

        Raises:
            ConfiguracionInvalida: si la secuencia no es coherente (por ejemplo, un
                borrador posterior a la aprobación de su versión).
        """
        borradores: dict[int, tuple[ContenidoProtocolo, Huella]] = {}
        aprobaciones: dict[int, str] = {}
        ultima = 0
        for datos in registros:
            registro = RegistroProtocolo(
                accion=AccionProtocolo(datos["accion"]),
                version=datos["version"],
                huella=datos["huella"],
                protocolo=datos["protocolo"],
                responsable=datos["responsable"],
            )
            numero = registro.version
            if numero in aprobaciones:
                raise _invalido(f"hay un registro de la versión {numero} después de aprobarla.")
            if registro.accion is AccionProtocolo.BORRADOR:
                if numero not in (ultima, ultima + 1) or (
                    numero == ultima and numero not in borradores
                ):
                    raise _invalido(f"el borrador de la versión {numero} está fuera de orden.")
                contenido = contenido_desde_datos(registro.protocolo)
                if contenido.huella().valor != registro.huella:
                    raise _invalido(f"la huella del borrador de la versión {numero} no coincide.")
                borradores[numero] = (contenido, Huella(registro.huella))
                ultima = numero
            else:
                if numero != ultima or numero not in borradores:
                    raise _invalido(f"la aprobación de la versión {numero} no tiene borrador.")
                if borradores[numero][1].valor != registro.huella:
                    raise _invalido(
                        f"la aprobación de la versión {numero} no coincide con su borrador."
                    )
                assert registro.responsable is not None
                aprobaciones[numero] = registro.responsable
        vigente = max(aprobaciones, default=None)
        versiones = []
        for numero in sorted(borradores):
            contenido, huella = borradores[numero]
            if numero not in aprobaciones:
                estado = EstadoProtocolo.BORRADOR
            elif numero == vigente:
                estado = EstadoProtocolo.APROBADO
            else:
                estado = EstadoProtocolo.REEMPLAZADO
            versiones.append(
                VersionProtocolo(numero, estado, contenido, huella, aprobaciones.get(numero))
            )
        return cls(tuple(versiones))

    def version(self, numero: int) -> VersionProtocolo:
        for version in self.versiones:
            if version.numero == numero:
                return version
        raise ConfiguracionInvalida(
            f"No existe la versión {numero} del protocolo.",
            "Consulte las versiones con `suficiencia protocolo ver`.",
        )

    def ultima(self) -> VersionProtocolo | None:
        return self.versiones[-1] if self.versiones else None

    def vigente(self) -> VersionProtocolo | None:
        for version in self.versiones:
            if version.estado is EstadoProtocolo.APROBADO:
                return version
        return None


# --- Operaciones -----------------------------------------------------------------


def guardar_borrador(
    historial: HistorialProtocolo, contenido: ContenidoProtocolo, version: int | None
) -> RegistroProtocolo:
    """Prepara el registro de un borrador.

    Con ``version`` = None crea una versión nueva, salvo que la última siga en
    borrador: entonces la reemplaza. Con un número, edita esa versión solo si sigue
    en borrador (PU-06).

    Raises:
        ProtocoloInmutable: si la versión indicada ya está aprobada o reemplazada.
    """
    ultima = historial.ultima()
    if version is None:
        if ultima is not None and ultima.estado is EstadoProtocolo.BORRADOR:
            numero = ultima.numero
        else:
            numero = (ultima.numero if ultima else 0) + 1
    else:
        existente = historial.version(version)
        if existente.estado is not EstadoProtocolo.BORRADOR:
            raise ProtocoloInmutable(existente.numero, existente.estado)
        numero = existente.numero
    return RegistroProtocolo(
        accion=AccionProtocolo.BORRADOR,
        version=numero,
        huella=contenido.huella().valor,
        protocolo=contenido.a_datos(),
        responsable=None,
    )


@dataclass(frozen=True)
class DatosDesviacion:
    descripcion: str
    justificacion: str


@dataclass(frozen=True)
class Aprobacion:
    """Registros que produce una aprobación: la desviación, si la hay, va primero."""

    desviacion: RegistroDesviacion | None
    aprobacion: RegistroProtocolo


def aprobar(
    historial: HistorialProtocolo,
    version: int,
    huella_revisada: str,
    responsable: str,
    confirmatorios: Sequence[str],
    desviacion: DatosDesviacion | None,
) -> Aprobacion:
    """Prepara la aprobación de una versión en borrador (CU-05).

    ``huella_revisada`` es la huella que el revisor aprueba: si el borrador cambió
    después de revisarlo, no coincide y la aprobación se rechaza.
    ``confirmatorios`` son los identificadores de los experimentos confirmatorios
    ya registrados.

    Raises:
        ProtocoloInmutable: si la versión ya está aprobada o reemplazada.
        ConfiguracionInvalida: si no es la última versión o la huella no coincide.
        DecisionPendiente: si falta lo decidido en alguna DP del protocolo.
        DesviacionRequerida: si hay experimentos confirmatorios y no se registra la desviación.
    """
    objetivo = historial.version(version)
    if objetivo.estado is not EstadoProtocolo.BORRADOR:
        raise ProtocoloInmutable(objetivo.numero, objetivo.estado)
    ultima = historial.ultima()
    assert ultima is not None
    if objetivo.numero != ultima.numero:
        raise ConfiguracionInvalida(
            f"La versión {version} no es la última del protocolo.",
            f"Apruebe la versión {ultima.numero}.",
        )
    if Huella(huella_revisada) != objetivo.huella:
        raise ConfiguracionInvalida(
            f"La huella revisada no coincide con la del borrador de la versión {version}.",
            "El borrador cambió después de revisarlo. Revíselo de nuevo y use su huella "
            "actual (`suficiencia protocolo ver`).",
        )
    faltantes = objetivo.contenido.decisiones_faltantes()
    if faltantes:
        raise DecisionPendiente(faltantes[0], f"lo decidido en {faltantes[0]} dentro del protocolo")
    anterior = historial.vigente()
    registro_desviacion = None
    if confirmatorios:
        if desviacion is None:
            raise DesviacionRequerida(confirmatorios)
        registro_desviacion = RegistroDesviacion(
            version_anterior=anterior.numero if anterior else 0,
            version_nueva=objetivo.numero,
            descripcion=desviacion.descripcion,
            justificacion=desviacion.justificacion,
            responsable=responsable,
            resultados_afectados=tuple(sorted(confirmatorios)),
        )
    elif desviacion is not None and anterior is not None:
        registro_desviacion = RegistroDesviacion(
            version_anterior=anterior.numero,
            version_nueva=objetivo.numero,
            descripcion=desviacion.descripcion,
            justificacion=desviacion.justificacion,
            responsable=responsable,
            resultados_afectados=(),
        )
    return Aprobacion(
        desviacion=registro_desviacion,
        aprobacion=RegistroProtocolo(
            accion=AccionProtocolo.APROBACION,
            version=objetivo.numero,
            huella=objetivo.huella.valor,
            protocolo=None,
            responsable=responsable,
        ),
    )


def exigir_vigente(
    historial: HistorialProtocolo, version_declarada: str | None, operacion: str
) -> VersionProtocolo:
    """Comprueba que exista un protocolo aprobado vigente y que sea el declarado (PU-05).

    Raises:
        SinProtocoloVigente: si no hay protocolo aprobado o la versión declarada no es la vigente.
    """
    vigente = historial.vigente()
    if vigente is None:
        raise SinProtocoloVigente(operacion, "no hay ninguna versión aprobada.")
    if version_declarada is not None and version_declarada != str(vigente.numero):
        raise SinProtocoloVigente(
            operacion,
            f"declara la versión {version_declarada!r}, pero la vigente es la {vigente.numero}.",
        )
    return vigente


def resultados_afectados(desviaciones: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    """Experimentos marcados por alguna desviación (RF-M4-13)."""
    return frozenset(e for d in desviaciones for e in d["resultados_afectados"])


@dataclass(frozen=True)
class EvaluacionSuficiencia:
    """Aplicación de la regla con la versión del protocolo y el modo en que se hizo."""

    modo: ModoExperimento
    version_protocolo: int
    huella_protocolo: str
    estado_protocolo: EstadoProtocolo
    ficticio: bool
    resultado: ResultadoSuficiencia


def evaluar_suficiencia(
    historial: HistorialProtocolo,
    version: int,
    modo: ModoExperimento,
    resultados: Sequence[ResultadoEscenario],
    procedimientos: Mapping[str, ProcedimientoMultiplicidad],
) -> EvaluacionSuficiencia:
    """Aplica el criterio de una versión del protocolo en el modo indicado.

    En modo confirmatorio solo vale la versión aprobada vigente (RF-M4-05). En modo
    exploratorio puede usarse cualquier versión, incluso un borrador, y el
    resultado queda marcado como exploratorio: no es evidencia confirmatoria.

    Raises:
        SinProtocoloVigente: en modo confirmatorio, si la versión no es la vigente.
    """
    if modo is ModoExperimento.CONFIRMATORIO:
        elegida = exigir_vigente(historial, str(version), "Aplicar la regla en modo confirmatorio")
    else:
        elegida = historial.version(version)
    return EvaluacionSuficiencia(
        modo=modo,
        version_protocolo=elegida.numero,
        huella_protocolo=elegida.huella.valor,
        estado_protocolo=elegida.estado,
        ficticio=elegida.contenido.ficticio,
        resultado=aplicar_regla(elegida.contenido.criterio, resultados, procedimientos),
    )
