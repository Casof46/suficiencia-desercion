"""Motor de la regla de suficiencia (M4; RF-M4-06; PU-04).

El motor no contiene ningún criterio. Recibe el criterio como datos, dentro del
protocolo aprobado: métricas (DP-08a), condiciones con sus límites (DP-08b y
DP-08c), comparadores (DP-08d), estadístico del intervalo (DP-08e), procedimiento
de multiplicidad (DP-08f) y desempate (DP-08g). Ninguno de esos campos tiene valor
por omisión; un valor nulo detiene el programa nombrando la decisión pendiente.

Tampoco calcula métricas ni intervalos: recibe, por escenario, estimaciones ya
calculadas (puntual y límites). Devuelve el escenario suficiente, "ningún escenario
cumple" o un empate que el desempate aprobado no resuelve. Nunca fuerza una
selección.

Los procedimientos de multiplicidad se conectan por nombre. El proyecto no
implementa ninguno (``PROCEDIMIENTOS_IMPLEMENTADOS`` está vacío) porque DP-08f sigue
abierta: un protocolo que nombre uno detiene la evaluación hasta que se implemente.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Protocol

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente, ErrorSuficiencia


class Sentido(Enum):
    """Dirección en que una métrica mejora."""

    MAYOR_ES_MEJOR = "mayor_es_mejor"
    MENOR_ES_MEJOR = "menor_es_mejor"


class Estadistico(Enum):
    """Qué valor de la estimación se compara con el límite (DP-08e)."""

    PUNTUAL = "puntual"
    LIMITE_INFERIOR = "limite_inferior"
    LIMITE_SUPERIOR = "limite_superior"


class TipoCondicion(Enum):
    """Estructuras de condición admitidas (DP-08b).

    - ``umbral``: la métrica del escenario frente a un valor mínimo o máximo.
    - ``no_inferioridad``: la diferencia (escenario menos comparador) frente a un
      margen. El comparador de la condición nombra un grupo de comparadores que
      fija DP-08d (por ejemplo, el conjunto más completo de la misma ventana y de
      cada ventana posterior evaluable). Cada escenario recibe sus propias
      diferencias dentro del grupo, y la condición se cumple solo si se cumple
      frente a todos ellos.
    """

    UMBRAL = "umbral"
    NO_INFERIORIDAD = "no_inferioridad"


class Desempate(Enum):
    """Claves de desempate entre escenarios suficientes (DP-08g), en el orden aprobado."""

    VENTANA_MAS_TEMPRANA = "ventana_mas_temprana"
    MENOS_BLOQUES = "menos_bloques"


PREFIJO_DESEMPATE_METRICA = "mejor_metrica:"
"""Desempate por el valor puntual de una métrica declarada (``mejor_metrica:<nombre>``)."""

PREFIJO_DESEMPATE_ORDEN = "orden_de_conjuntos:"
"""Desempate por un orden explícito de conjuntos (``orden_de_conjuntos:A,A+F,A+B``):
gana el conjunto que aparece antes. Un conjunto que no está en la lista no se
desempata con esta clave."""


class EstadoEscenario(Enum):
    CUMPLE = "cumple"
    NO_CUMPLE = "no_cumple"
    NO_EVALUABLE = "no_evaluable"


class EstadoSuficiencia(Enum):
    """Resultado de aplicar la regla (RF-M4-06)."""

    ESCENARIO_SUFICIENTE = "escenario_suficiente"
    NINGUNO_CUMPLE = "ningun_escenario_cumple"
    EMPATE_SIN_RESOLVER = "empate_sin_resolver"


# --- Criterio --------------------------------------------------------------------


def _invalido(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Criterio de suficiencia: {causa}",
        "Corrija el criterio del protocolo; el ejemplo de las pruebas está en "
        "config/ejemplos/protocolo_ficticio.yaml.",
    )


@dataclass(frozen=True)
class Metrica:
    """Métrica declarada en el criterio (DP-08a)."""

    nombre: str
    sentido: Sentido

    def __post_init__(self) -> None:
        if not isinstance(self.nombre, str) or not self.nombre.strip():
            raise _invalido("una métrica no tiene nombre.")


@dataclass(frozen=True)
class Condicion:
    """Una condición que el escenario debe cumplir.

    ``limite`` es el umbral (``umbral``) o el margen, positivo, (``no_inferioridad``).
    ``inclusivo`` indica si igualar el límite cuenta como cumplir. ``comparador`` es
    obligatorio en ``no_inferioridad`` y no se admite en ``umbral``.
    """

    tipo: TipoCondicion
    metrica: str
    estadistico: Estadistico
    limite: float
    inclusivo: bool
    comparador: str | None

    def __post_init__(self) -> None:
        if isinstance(self.limite, bool) or not isinstance(self.limite, (int, float)):
            raise _invalido(f"el límite de la condición sobre '{self.metrica}' no es un número.")
        if not math.isfinite(self.limite):
            raise _invalido(f"el límite de la condición sobre '{self.metrica}' no es finito.")
        if not isinstance(self.inclusivo, bool):
            raise _invalido(f"'inclusivo' de la condición sobre '{self.metrica}' debe ser sí o no.")
        if self.tipo is TipoCondicion.NO_INFERIORIDAD:
            if not self.comparador or not self.comparador.strip():
                raise _invalido(
                    f"la condición de no inferioridad sobre '{self.metrica}' no tiene comparador."
                )
            if self.limite < 0:
                raise _invalido(f"el margen de no inferioridad sobre '{self.metrica}' es negativo.")
        elif self.comparador is not None:
            raise _invalido(f"la condición de umbral sobre '{self.metrica}' no lleva comparador.")


@dataclass(frozen=True)
class CriterioSuficiencia:
    """Regla de decisión del protocolo: un escenario cumple si cumple todas las condiciones."""

    metricas: tuple[Metrica, ...]
    condiciones: tuple[Condicion, ...]
    multiplicidad: str
    desempate: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.metricas:
            raise _invalido("no declara ninguna métrica.")
        nombres = [m.nombre for m in self.metricas]
        if len(set(nombres)) != len(nombres):
            raise _invalido("declara dos veces la misma métrica.")
        if not self.condiciones:
            raise _invalido("no tiene ninguna condición.")
        for condicion in self.condiciones:
            if condicion.metrica not in nombres:
                raise _invalido(f"la condición usa la métrica no declarada '{condicion.metrica}'.")
        if not isinstance(self.multiplicidad, str) or not self.multiplicidad.strip():
            raise _invalido("no nombra el procedimiento de multiplicidad.")
        if not self.desempate:
            raise _invalido("no tiene regla de desempate.")
        if len(set(self.desempate)) != len(self.desempate):
            raise _invalido("repite una clave de desempate.")
        for clave in self.desempate:
            _validar_clave_desempate(clave, nombres)

    def sentido_de(self, metrica: str) -> Sentido:
        return next(m.sentido for m in self.metricas if m.nombre == metrica)

    def a_datos(self) -> dict[str, Any]:
        """Forma canónica, la misma que se lee (``criterio_desde_datos``)."""
        return {
            "metricas": [{"nombre": m.nombre, "sentido": m.sentido.value} for m in self.metricas],
            "condiciones": [
                {
                    "tipo": c.tipo.value,
                    "metrica": c.metrica,
                    "estadistico": c.estadistico.value,
                    "limite": float(c.limite),
                    "inclusivo": c.inclusivo,
                    "comparador": c.comparador,
                }
                for c in self.condiciones
            ],
            "multiplicidad": self.multiplicidad,
            "desempate": list(self.desempate),
        }


def _validar_clave_desempate(clave: str, metricas: Sequence[str]) -> None:
    if clave in {d.value for d in Desempate}:
        return
    if clave.startswith(PREFIJO_DESEMPATE_METRICA):
        metrica = clave.removeprefix(PREFIJO_DESEMPATE_METRICA)
        if metrica in metricas:
            return
        raise _invalido(f"el desempate usa la métrica no declarada '{metrica}'.")
    if clave.startswith(PREFIJO_DESEMPATE_ORDEN):
        conjuntos = orden_de_conjuntos(clave)
        if not conjuntos or not all(conjuntos):
            raise _invalido(f"'{clave}' debe listar conjuntos separados por comas.")
        if len(set(conjuntos)) != len(conjuntos):
            raise _invalido(f"'{clave}' repite un conjunto.")
        return
    opciones = ", ".join(
        [d.value for d in Desempate]
        + [f"{PREFIJO_DESEMPATE_METRICA}<métrica>", f"{PREFIJO_DESEMPATE_ORDEN}<c1>,<c2>,..."]
    )
    raise _invalido(f"clave de desempate desconocida '{clave}'. Opciones: {opciones}.")


def orden_de_conjuntos(clave: str) -> list[str]:
    """Conjuntos de una clave ``orden_de_conjuntos:``, en el orden indicado."""
    return [c.strip() for c in clave.removeprefix(PREFIJO_DESEMPATE_ORDEN).split(",")]


def _campo(datos: Mapping[str, Any], clave: str, decision: str, donde: str) -> Any:
    if clave not in datos:
        raise _invalido(f"falta '{clave}' en {donde} ({decision}).")
    if datos[clave] is None:
        raise DecisionPendiente(decision, f"'{clave}' en {donde}")
    return datos[clave]


def _enum(tipo: type[Any], valor: Any, campo: str) -> Any:
    try:
        return tipo(valor)
    except ValueError:
        opciones = ", ".join(e.value for e in tipo)
        raise _invalido(f"'{campo}' = {valor!r} no es válido. Opciones: {opciones}.") from None


def _lista(valor: Any, campo: str) -> list[Any]:
    if not isinstance(valor, list):
        raise _invalido(f"'{campo}' debe ser una lista.")
    return valor


def _diccionario(valor: Any, campo: str) -> Mapping[str, Any]:
    if not isinstance(valor, Mapping):
        raise _invalido(f"'{campo}' debe ser un conjunto de campos.")
    return valor


_CLAVES_CRITERIO = {"metricas", "condiciones", "multiplicidad", "desempate"}
_CLAVES_METRICA = {"nombre", "sentido"}
_CLAVES_CONDICION = {"tipo", "metrica", "estadistico", "limite", "inclusivo", "comparador"}


def _sin_claves_extra(datos: Mapping[str, Any], validas: set[str], donde: str) -> None:
    extra = sorted(set(datos) - validas)
    if extra:
        raise _invalido(f"campos desconocidos en {donde}: {', '.join(extra)}.")


def criterio_desde_datos(datos: Any) -> CriterioSuficiencia:
    """Construye el criterio a partir de datos leídos de un protocolo.

    Raises:
        DecisionPendiente: si un campo vale ``null`` (nombra el subcódigo de DP-08).
        ConfiguracionInvalida: si la estructura no es válida.
    """
    datos = _diccionario(datos, "criterio_suficiencia")
    _sin_claves_extra(datos, _CLAVES_CRITERIO, "el criterio")
    metricas = []
    for elemento in _lista(_campo(datos, "metricas", "DP-08a", "el criterio"), "metricas"):
        elemento = _diccionario(elemento, "metricas")
        _sin_claves_extra(elemento, _CLAVES_METRICA, "una métrica")
        metricas.append(
            Metrica(
                nombre=_campo(elemento, "nombre", "DP-08a", "una métrica"),
                sentido=_enum(
                    Sentido, _campo(elemento, "sentido", "DP-08a", "una métrica"), "sentido"
                ),
            )
        )
    condiciones = []
    for elemento in _lista(_campo(datos, "condiciones", "DP-08b", "el criterio"), "condiciones"):
        elemento = _diccionario(elemento, "condiciones")
        _sin_claves_extra(elemento, _CLAVES_CONDICION, "una condición")
        tipo = _enum(TipoCondicion, _campo(elemento, "tipo", "DP-08b", "una condición"), "tipo")
        if "comparador" not in elemento:
            raise _invalido("falta 'comparador' en una condición (DP-08d; vacío en un umbral).")
        comparador = elemento["comparador"]
        if tipo is TipoCondicion.NO_INFERIORIDAD and comparador is None:
            raise DecisionPendiente("DP-08d", "el comparador de una condición de no inferioridad")
        condiciones.append(
            Condicion(
                tipo=tipo,
                metrica=_campo(elemento, "metrica", "DP-08a", "una condición"),
                estadistico=_enum(
                    Estadistico,
                    _campo(elemento, "estadistico", "DP-08e", "una condición"),
                    "estadistico",
                ),
                limite=_campo(elemento, "limite", "DP-08c", "una condición"),
                inclusivo=_campo(elemento, "inclusivo", "DP-08c", "una condición"),
                comparador=comparador,
            )
        )
    desempate = _lista(_campo(datos, "desempate", "DP-08g", "el criterio"), "desempate")
    if not all(isinstance(c, str) for c in desempate):
        raise _invalido("cada clave de desempate debe ser un texto.")
    return CriterioSuficiencia(
        metricas=tuple(metricas),
        condiciones=tuple(condiciones),
        multiplicidad=_campo(datos, "multiplicidad", "DP-08f", "el criterio"),
        desempate=tuple(desempate),
    )


# --- Resultados de entrada ---------------------------------------------------------


@dataclass(frozen=True)
class Estimacion:
    """Valor de una métrica o de una diferencia: puntual y, si existen, sus límites."""

    puntual: float
    limite_inferior: float | None
    limite_superior: float | None

    def __post_init__(self) -> None:
        valores = [self.puntual, self.limite_inferior, self.limite_superior]
        if any(v is not None and not math.isfinite(v) for v in valores):
            raise ConfiguracionInvalida(
                "Una estimación tiene un valor no finito.",
                "Revise el cálculo de métricas e intervalos.",
            )
        if (self.limite_inferior is not None and self.limite_inferior > self.puntual) or (
            self.limite_superior is not None and self.limite_superior < self.puntual
        ):
            raise ConfiguracionInvalida(
                "Una estimación tiene el valor puntual fuera de su intervalo.",
                "Revise el cálculo de métricas e intervalos.",
            )

    def valor(self, estadistico: Estadistico) -> float | None:
        if estadistico is Estadistico.PUNTUAL:
            return self.puntual
        if estadistico is Estadistico.LIMITE_INFERIOR:
            return self.limite_inferior
        return self.limite_superior


@dataclass(frozen=True)
class ResultadoEscenario:
    """Estimaciones de un escenario que el motor compara con el criterio.

    ``conjunto`` es el código del conjunto de información (por ejemplo, ``A+F``).
    ``diferencias`` se indexa por ``(metrica, grupo de comparadores)`` y contiene,
    para cada comparador concreto del grupo que aplica a este escenario, la
    diferencia escenario menos comparador, en las unidades de la métrica. Qué
    comparadores aplican a cada escenario lo calcula quien entrega los resultados,
    según DP-08d.
    """

    escenario: str
    conjunto: str
    orden_ventana: int
    numero_bloques: int
    metricas: Mapping[str, Estimacion]
    diferencias: Mapping[tuple[str, str], Mapping[str, Estimacion]]


# --- Evaluación --------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluacionCondicion:
    condicion: Condicion
    valor: float | None
    cumple: bool | None
    motivo: str


@dataclass(frozen=True)
class EvaluacionEscenario:
    escenario: str
    estado: EstadoEscenario
    condiciones: tuple[EvaluacionCondicion, ...]


def _compara(valor: float, limite: float, inclusivo: bool, mayor: bool) -> bool:
    if mayor:
        return valor >= limite if inclusivo else valor > limite
    return valor <= limite if inclusivo else valor < limite


def _evaluar_condicion(
    criterio: CriterioSuficiencia, condicion: Condicion, resultado: ResultadoEscenario
) -> EvaluacionCondicion:
    mayor = criterio.sentido_de(condicion.metrica) is Sentido.MAYOR_ES_MEJOR
    signo = (
        (">=" if condicion.inclusivo else ">") if mayor else ("<=" if condicion.inclusivo else "<")
    )
    estadistico = condicion.estadistico.value
    if condicion.tipo is TipoCondicion.UMBRAL:
        que = f"la métrica '{condicion.metrica}'"
        estimacion = resultado.metricas.get(condicion.metrica)
        if estimacion is None:
            return EvaluacionCondicion(condicion, None, None, f"falta {que}")
        valor = estimacion.valor(condicion.estadistico)
        if valor is None:
            return EvaluacionCondicion(condicion, None, None, f"falta el {estadistico} de {que}")
        cumple = _compara(valor, condicion.limite, condicion.inclusivo, mayor)
        motivo = f"{estadistico} de {que} = {valor:g}; se exige {signo} {condicion.limite:g}"
        return EvaluacionCondicion(condicion, valor, cumple, motivo)

    assert condicion.comparador is not None
    que = f"la diferencia de '{condicion.metrica}' frente a '{condicion.comparador}'"
    # Diferencia = escenario - comparador. Si mayor es mejor, no ser inferior es que
    # la diferencia supere -margen; si menor es mejor, que no supere +margen.
    limite = -condicion.limite if mayor else condicion.limite
    grupo = resultado.diferencias.get((condicion.metrica, condicion.comparador))
    if not grupo:
        return EvaluacionCondicion(condicion, None, None, f"falta {que}")
    valores: dict[str, float] = {}
    for comparador, estimacion in sorted(grupo.items()):
        valor = estimacion.valor(condicion.estadistico)
        if valor is None:
            return EvaluacionCondicion(
                condicion, None, None, f"falta el {estadistico} de {que} ({comparador})"
            )
        valores[comparador] = valor
    # El peor caso decide: la condición se cumple solo si se cumple frente a todos.
    peor = min(valores, key=valores.__getitem__) if mayor else max(valores, key=valores.__getitem__)
    cumple = all(_compara(v, limite, condicion.inclusivo, mayor) for v in valores.values())
    detalle = ", ".join(f"{c} = {v:g}" for c, v in valores.items())
    motivo = f"{estadistico} de {que}: {detalle}; se exige {signo} {limite:g}"
    if len(valores) > 1:
        motivo += f" frente a todos (peor: {peor})"
    return EvaluacionCondicion(condicion, valores[peor], cumple, motivo)


def evaluar_escenario(
    criterio: CriterioSuficiencia, resultado: ResultadoEscenario
) -> EvaluacionEscenario:
    """Evalúa cada condición. Una sola que no se cumple basta para "no cumple"; si
    ninguna falla pero falta algún valor, el escenario es "no evaluable", nunca
    "cumple"."""
    evaluaciones = tuple(_evaluar_condicion(criterio, c, resultado) for c in criterio.condiciones)
    if any(e.cumple is False for e in evaluaciones):
        estado = EstadoEscenario.NO_CUMPLE
    elif any(e.cumple is None for e in evaluaciones):
        estado = EstadoEscenario.NO_EVALUABLE
    else:
        estado = EstadoEscenario.CUMPLE
    return EvaluacionEscenario(resultado.escenario, estado, evaluaciones)


# --- Multiplicidad -----------------------------------------------------------------


class ProcedimientoMultiplicidad(Protocol):
    """Interfaz de un procedimiento de control de multiplicidad (DP-08f).

    Recibe la familia confirmatoria completa (todas las evaluaciones y sus
    resultados) y devuelve qué escenarios confirman su suficiencia. Solo puede
    quitar escenarios de los que cumplen las condiciones, nunca añadir.
    """

    def confirmar(
        self,
        evaluaciones: tuple[EvaluacionEscenario, ...],
        resultados: Mapping[str, ResultadoEscenario],
    ) -> frozenset[str]: ...


PROCEDIMIENTOS_IMPLEMENTADOS: Mapping[str, ProcedimientoMultiplicidad] = MappingProxyType({})
"""Procedimientos de multiplicidad del proyecto. Vacío mientras DP-08f esté abierta."""


class ProcedimientoInvalido(ErrorSuficiencia):
    """Un procedimiento de multiplicidad confirmó un escenario que no cumple."""


def _procedimiento(
    nombre: str, procedimientos: Mapping[str, ProcedimientoMultiplicidad]
) -> ProcedimientoMultiplicidad:
    if nombre not in procedimientos:
        raise DecisionPendiente(
            "DP-08f",
            f"la implementación del procedimiento de multiplicidad '{nombre}' que nombra "
            "el protocolo",
        )
    return procedimientos[nombre]


# --- Regla -------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoSuficiencia:
    estado: EstadoSuficiencia
    escenario: str | None
    empatados: tuple[str, ...]
    cumplen: tuple[str, ...]
    confirmados: tuple[str, ...]
    evaluaciones: tuple[EvaluacionEscenario, ...]


def _clave_orden(
    clave: str, criterio: CriterioSuficiencia, resultado: ResultadoEscenario
) -> float | None:
    """Valor que se minimiza en cada paso del desempate; None si falta el dato."""
    if clave == Desempate.VENTANA_MAS_TEMPRANA.value:
        return float(resultado.orden_ventana)
    if clave == Desempate.MENOS_BLOQUES.value:
        return float(resultado.numero_bloques)
    if clave.startswith(PREFIJO_DESEMPATE_ORDEN):
        orden = orden_de_conjuntos(clave)
        return float(orden.index(resultado.conjunto)) if resultado.conjunto in orden else None
    metrica = clave.removeprefix(PREFIJO_DESEMPATE_METRICA)
    estimacion = resultado.metricas.get(metrica)
    if estimacion is None:
        return None
    mayor = criterio.sentido_de(metrica) is Sentido.MAYOR_ES_MEJOR
    return -estimacion.puntual if mayor else estimacion.puntual


def _desempatar(
    criterio: CriterioSuficiencia,
    candidatos: list[str],
    resultados: Mapping[str, ResultadoEscenario],
) -> list[str]:
    restantes = sorted(candidatos)
    for clave in criterio.desempate:
        if len(restantes) == 1:
            break
        valores = {e: _clave_orden(clave, criterio, resultados[e]) for e in restantes}
        if any(v is None for v in valores.values()):
            # Sin el dato no se puede desempatar con esta clave: el empate sigue.
            break
        mejor = min(v for v in valores.values() if v is not None)
        restantes = [e for e in restantes if valores[e] == mejor]
    return restantes


def aplicar_regla(
    criterio: CriterioSuficiencia,
    resultados: Sequence[ResultadoEscenario],
    procedimientos: Mapping[str, ProcedimientoMultiplicidad],
) -> ResultadoSuficiencia:
    """Aplica el criterio a la familia de escenarios (RF-M4-06; CU-08 paso 5).

    Raises:
        DecisionPendiente: si el procedimiento de multiplicidad no está implementado (DP-08f).
        ConfiguracionInvalida: si no hay escenarios o alguno está repetido.
        ProcedimientoInvalido: si el procedimiento confirma un escenario que no cumple.
    """
    procedimiento = _procedimiento(criterio.multiplicidad, procedimientos)
    if not resultados:
        raise ConfiguracionInvalida(
            "No hay resultados de escenarios para aplicar la regla.",
            "Entregue al menos un escenario evaluado.",
        )
    por_escenario = {r.escenario: r for r in resultados}
    if len(por_escenario) != len(resultados):
        raise ConfiguracionInvalida(
            "Un escenario aparece dos veces en los resultados.",
            "Entregue un resultado por escenario.",
        )
    evaluaciones = tuple(evaluar_escenario(criterio, r) for r in resultados)
    cumplen = sorted(e.escenario for e in evaluaciones if e.estado is EstadoEscenario.CUMPLE)
    confirmados = procedimiento.confirmar(evaluaciones, MappingProxyType(por_escenario))
    ajenos = sorted(set(confirmados) - set(cumplen))
    if ajenos:
        raise ProcedimientoInvalido(
            f"El procedimiento de multiplicidad '{criterio.multiplicidad}' confirmó "
            f"escenarios que no cumplen las condiciones: {', '.join(ajenos)}.",
            "Un procedimiento de multiplicidad solo puede quitar escenarios; corrija su "
            "implementación.",
        )
    if not confirmados:
        return ResultadoSuficiencia(
            EstadoSuficiencia.NINGUNO_CUMPLE,
            None,
            (),
            tuple(cumplen),
            (),
            evaluaciones,
        )
    restantes = _desempatar(criterio, sorted(confirmados), por_escenario)
    if len(restantes) == 1:
        return ResultadoSuficiencia(
            EstadoSuficiencia.ESCENARIO_SUFICIENTE,
            restantes[0],
            (),
            tuple(cumplen),
            tuple(sorted(confirmados)),
            evaluaciones,
        )
    return ResultadoSuficiencia(
        EstadoSuficiencia.EMPATE_SIN_RESOLVER,
        None,
        tuple(restantes),
        tuple(cumplen),
        tuple(sorted(confirmados)),
        evaluaciones,
    )
