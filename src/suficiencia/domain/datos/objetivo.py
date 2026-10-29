"""Objetivo y estados de etiqueta (M1; RF-M1-06, RF-M1-10, RF-M1-11; CU-03).

El objetivo se construye con reglas parametrizadas por el desglose de DP-01
(sección 12.1 de la especificación). Todos los parámetros son obligatorios y no
tienen valor por omisión: una definición incompleta no se construye. El
programa no contiene ninguna definición de deserción; las únicas que existen
son ejemplos ficticios rotulados como tales.

Cada unidad (estudiante, o estudiante y carrera) recibe un estado de etiqueta:
positivo, negativo o no etiquetable con su motivo (REC-03). Los no etiquetables
nunca entran en entrenamiento ni evaluación (``para_modelado``) y se cuentan por
cohorte y motivo; si su proporción supera el nivel fijado en DP-18, la cohorte
exige un análisis de sensibilidad (cambio CP-08).

Los periodos son ordinales desde el ingreso (1 = primer periodo de la cohorte),
como en el historial de matrícula del diccionario sintético.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from suficiencia.domain.errores import ConfiguracionInvalida


class Categoria(Enum):
    """Qué significa cada código de estado de matrícula (catálogo de la institución, DP-01)."""

    MATRICULA = "matricula"
    AUSENCIA = "ausencia"
    PAUSA = "pausa"
    RETIRO_EN_PERIODO = "retiro_en_periodo"
    TRASLADO_INTERNO = "traslado_interno"
    TRASLADO_EXTERNO = "traslado_externo"
    DESENLACE_EXCLUIDO = "desenlace_excluido"
    EVENTO_FORMAL = "evento_formal"


class Efecto(Enum):
    """Cómo cuenta un periodo para el objetivo."""

    MATRICULA = "matricula"
    AUSENCIA = "ausencia"
    NEUTRAL = "neutral"
    EVENTO = "evento"
    NO_EVENTO = "no_evento"
    NO_OBSERVABLE = "no_observable"
    DESENLACE_EXCLUIDO = "desenlace_excluido"


class Unidad(Enum):
    """DP-01b."""

    ESTUDIANTE = "estudiante"
    ESTUDIANTE_CARRERA = "estudiante_carrera"


class PoblacionInicial(Enum):
    """DP-01c."""

    ADMITIDOS = "admitidos"
    MATRICULADOS_PRIMER_PERIODO = "matriculados_primer_periodo"


class InicioHorizonte(Enum):
    """DP-01e."""

    INGRESO = "ingreso"
    FECHA_INDICE = "fecha_indice"


class FechadoEvento(Enum):
    """DP-01f."""

    PRIMER_PERIODO_SIN_MATRICULA = "primer_periodo_sin_matricula"
    CONFIRMACION = "confirmacion"


class Reingreso(Enum):
    """DP-01j."""

    ANULA_EVENTO = "anula_evento"
    NO_ANULA = "no_anula"


class PeriodosExtraordinarios(Enum):
    """DP-01k."""

    IGNORAR = "ignorar"
    CONTAR = "contar"


class Seguimiento(Enum):
    """DP-01m: qué hay que observar para no declarar el seguimiento incompleto."""

    FIN_HORIZONTE = "fin_horizonte"
    FIN_HORIZONTE_Y_CONFIRMACION = "fin_horizonte_y_confirmacion"


class EstadoEtiqueta(Enum):
    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    NO_ETIQUETABLE = "no_etiquetable"


class Motivo(Enum):
    """Motivos de un caso no etiquetable (RF-M1-10)."""

    SEGUIMIENTO_INCOMPLETO = "seguimiento_incompleto"
    RESULTADO_NO_OBSERVABLE = "resultado_no_observable"
    DESENLACE_EXCLUIDO = "desenlace_excluido"


# Efectos que admite cada categoría configurable (opciones de la sección 12.1).
EFECTOS_PERMITIDOS: Mapping[str, frozenset[Efecto]] = {
    "pausas": frozenset({Efecto.NEUTRAL, Efecto.AUSENCIA, Efecto.NO_OBSERVABLE}),
    "retiro_en_periodo": frozenset({Efecto.EVENTO, Efecto.AUSENCIA, Efecto.MATRICULA}),
    "traslado_interno": frozenset(
        {Efecto.MATRICULA, Efecto.EVENTO, Efecto.DESENLACE_EXCLUIDO, Efecto.NO_OBSERVABLE}
    ),
    "traslado_externo": frozenset({Efecto.EVENTO, Efecto.DESENLACE_EXCLUIDO, Efecto.NO_OBSERVABLE}),
    "desenlaces_excluidos": frozenset({Efecto.DESENLACE_EXCLUIDO, Efecto.EVENTO, Efecto.NO_EVENTO}),
    "registro_faltante": frozenset({Efecto.AUSENCIA, Efecto.NO_OBSERVABLE}),
}

TRATAMIENTO_NO_ETIQUETABLES = "excluir_y_contar"
"""Único tratamiento de DP-18 implementado: la regla por defecto de REC-03."""


def _invalida(causa: str) -> ConfiguracionInvalida:
    return ConfiguracionInvalida(
        f"Definición del objetivo: {causa}",
        "Corrija la definición; el ejemplo válido está en config/ejemplos/objetivo_ficticio.yaml.",
    )


def _entero_positivo(valor: object, campo: str) -> None:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        raise _invalida(f"'{campo}' debe ser un entero mayor o igual a 1.")


@dataclass(frozen=True)
class DefinicionObjetivo:
    """Reglas del objetivo. Cada campo corresponde a un elemento del desglose de DP-01.

    DP-01d (fecha índice de cada ventana) no está aquí: se declara en
    ``config/escenarios.yaml`` desde H2.2 y se aplica por ventana en H2.5.
    """

    nombre: str
    ficticio: bool
    periodos_sin_matricula: int  # DP-01a
    unidad: Unidad  # DP-01b
    columna_carrera: str | None  # DP-01b, solo con estudiante_carrera
    poblacion_inicial: PoblacionInicial  # DP-01c
    cohortes: frozenset[str] | None  # DP-01c; None solo si se declaró "todas"
    horizonte_periodos: int  # DP-01e
    horizonte_desde: InicioHorizonte  # DP-01e
    fechado: FechadoEvento  # DP-01f
    pausas: Efecto  # DP-01g
    limite_pausas: int | None  # DP-01g; None solo si se declaró "sin_limite"
    retiro_en_periodo: Efecto  # DP-01h
    traslado_interno: Efecto  # DP-01i
    traslado_externo: Efecto  # DP-01i
    reingreso: Reingreso  # DP-01j
    periodos_extraordinarios: PeriodosExtraordinarios  # DP-01k
    lista_extraordinarios: frozenset[int]  # DP-01k
    desenlaces_excluidos: Efecto  # DP-01l
    seguimiento: Seguimiento  # DP-01m
    registro_faltante: Efecto  # DP-01m (periodo sin registro dentro de lo observable)
    catalogo: Mapping[str, Categoria]  # códigos de estado de la institución (DP-01)
    tratamiento_no_etiquetables: str  # DP-18
    nivel_sensibilidad: float  # DP-18 (cambio CP-08)

    def __post_init__(self) -> None:
        if not isinstance(self.nombre, str) or not self.nombre.strip():
            raise _invalida("'nombre' no puede estar vacío.")
        _entero_positivo(self.periodos_sin_matricula, "evento.periodos_sin_matricula")
        _entero_positivo(self.horizonte_periodos, "horizonte.periodos")
        if self.unidad is Unidad.ESTUDIANTE_CARRERA and not self.columna_carrera:
            raise _invalida("con unidad 'estudiante_carrera' hay que indicar 'columna_carrera'.")
        if self.unidad is Unidad.ESTUDIANTE and self.columna_carrera:
            raise _invalida("'columna_carrera' solo se usa con unidad 'estudiante_carrera'.")
        if self.cohortes is not None and not self.cohortes:
            raise _invalida("'poblacion.cohortes' debe ser 'todas' o una lista no vacía.")
        if self.limite_pausas is not None:
            _entero_positivo(self.limite_pausas, "pausas.limite_periodos")
        if self.pausas is not Efecto.NEUTRAL and self.limite_pausas is not None:
            raise _invalida("'pausas.limite_periodos' solo se usa con tratamiento 'neutral'.")
        for campo in EFECTOS_PERMITIDOS:
            efecto = getattr(self, campo)
            if efecto not in EFECTOS_PERMITIDOS[campo]:
                permitidos = ", ".join(sorted(e.value for e in EFECTOS_PERMITIDOS[campo]))
                raise _invalida(f"'{campo}' = {efecto.value!r} no es válido; use: {permitidos}.")
        if not self.catalogo:
            raise _invalida("el catálogo de estados de matrícula está vacío.")
        if Categoria.MATRICULA not in self.catalogo.values():
            raise _invalida("el catálogo no tiene ningún código con categoría 'matricula'.")
        if self.tratamiento_no_etiquetables != TRATAMIENTO_NO_ETIQUETABLES:
            raise _invalida(
                f"'no_etiquetables.tratamiento' solo admite '{TRATAMIENTO_NO_ETIQUETABLES}' "
                "(REC-03); las demás opciones de DP-18 no están implementadas."
            )
        nivel = self.nivel_sensibilidad
        if isinstance(nivel, bool) or not isinstance(nivel, (int, float)) or not 0 < nivel <= 1:
            raise _invalida("'no_etiquetables.nivel_analisis_sensibilidad' debe estar en (0, 1].")


@dataclass(frozen=True)
class ColumnasHistorial:
    """Columnas del historial de matrícula que usa el objetivo (salen del diccionario)."""

    unidad: tuple[str, ...]
    cohorte: str
    periodo: str
    estado: str


@dataclass(frozen=True)
class Etiqueta:
    estado: EstadoEtiqueta
    motivo: Motivo | None
    periodo_evento: int | None
    ultimo_periodo_observado: int | None


@dataclass(frozen=True)
class ResultadoObjetivo:
    """Una fila por unidad de la población, con su estado de etiqueta."""

    registros: pd.DataFrame
    fuera_de_poblacion: int
    fuera_de_cohortes: int


COLUMNA_ESTADO = "estado_etiqueta"
COLUMNA_MOTIVO = "motivo"
COLUMNA_PERIODO_EVENTO = "periodo_evento"
COLUMNA_ULTIMO_PERIODO = "ultimo_periodo_observado"


def _periodos_regulares(definicion: DefinicionObjetivo, desde: int, cantidad: int) -> list[int]:
    """Los ``cantidad`` periodos que cuentan a partir de ``desde`` (DP-01k)."""
    periodos: list[int] = []
    periodo = desde
    while len(periodos) < cantidad:
        periodo += 1
        if (
            definicion.periodos_extraordinarios is PeriodosExtraordinarios.IGNORAR
            and periodo in definicion.lista_extraordinarios
        ):
            continue
        periodos.append(periodo)
    return periodos


def periodo_necesario(definicion: DefinicionObjetivo, desde: int = 0) -> int:
    """Último periodo que hay que observar para etiquetar sin seguimiento incompleto."""
    fin = _periodos_regulares(definicion, desde, definicion.horizonte_periodos)[-1]
    if (
        definicion.seguimiento is Seguimiento.FIN_HORIZONTE_Y_CONFIRMACION
        and definicion.fechado is FechadoEvento.PRIMER_PERIODO_SIN_MATRICULA
        and definicion.periodos_sin_matricula > 1
    ):
        return _periodos_regulares(definicion, fin, definicion.periodos_sin_matricula - 1)[-1]
    return fin


def _efecto(definicion: DefinicionObjetivo, categoria: Categoria) -> Efecto:
    return {
        Categoria.MATRICULA: Efecto.MATRICULA,
        Categoria.AUSENCIA: Efecto.AUSENCIA,
        Categoria.PAUSA: definicion.pausas,
        Categoria.RETIRO_EN_PERIODO: definicion.retiro_en_periodo,
        Categoria.TRASLADO_INTERNO: definicion.traslado_interno,
        Categoria.TRASLADO_EXTERNO: definicion.traslado_externo,
        Categoria.DESENLACE_EXCLUIDO: definicion.desenlaces_excluidos,
        Categoria.EVENTO_FORMAL: Efecto.EVENTO,
    }[categoria]


def _es_terminal(categoria: Categoria, efecto: Efecto) -> bool:
    """Después de estos estados la unidad ya no tiene más periodos que observar."""
    if categoria in {Categoria.TRASLADO_EXTERNO, Categoria.DESENLACE_EXCLUIDO}:
        return True
    return categoria is Categoria.TRASLADO_INTERNO and efecto is not Efecto.MATRICULA


def etiquetar_unidad(
    estados: Mapping[int, str],
    limite_observable: int,
    definicion: DefinicionObjetivo,
    desde: int = 0,
) -> Etiqueta:
    """Estado de etiqueta de una unidad a partir de su historial (RF-M1-06, 10 y 11).

    Args:
        estados: código de estado por periodo ordinal.
        limite_observable: último periodo observable de la cohorte a la fecha de corte.
        definicion: reglas del objetivo.
        desde: el horizonte empieza después de este periodo (0 = desde el ingreso).
    """
    ultimo = max(estados) if estados else None

    def resultado(estado: EstadoEtiqueta, motivo: Motivo | None, evento: int | None) -> Etiqueta:
        return Etiqueta(estado, motivo, evento, ultimo)

    horizonte = _periodos_regulares(definicion, desde, definicion.horizonte_periodos)
    fin_horizonte = horizonte[-1]
    secuencia = list(horizonte)
    if (
        definicion.seguimiento is Seguimiento.FIN_HORIZONTE_Y_CONFIRMACION
        and definicion.fechado is FechadoEvento.PRIMER_PERIODO_SIN_MATRICULA
    ):
        secuencia += _periodos_regulares(
            definicion, fin_horizonte, definicion.periodos_sin_matricula - 1
        )
    anula = definicion.reingreso is Reingreso.ANULA_EVENTO

    evento: int | None = None
    racha = 0
    inicio_racha: int | None = None
    pausas_seguidas = 0
    observado_hasta = desde
    for periodo in secuencia:
        en_horizonte = periodo <= fin_horizonte
        if not en_horizonte and racha == 0:
            break
        if periodo > limite_observable:
            break
        observado_hasta = periodo
        codigo = estados.get(periodo)
        if codigo is None:
            categoria = None
            efecto = definicion.registro_faltante
        else:
            categoria = definicion.catalogo[codigo]
            efecto = _efecto(definicion, categoria)

        if efecto is Efecto.NEUTRAL:
            pausas_seguidas += 1
            limite = definicion.limite_pausas
            if limite is None or pausas_seguidas <= limite:
                continue
            efecto = Efecto.AUSENCIA
        else:
            pausas_seguidas = 0

        if efecto is Efecto.MATRICULA:
            if evento is not None and anula and en_horizonte:
                evento = None
            racha, inicio_racha = 0, None
        elif efecto is Efecto.AUSENCIA:
            if racha == 0:
                inicio_racha = periodo
            racha += 1
            if racha == definicion.periodos_sin_matricula and evento is None:
                assert inicio_racha is not None
                fecha = (
                    inicio_racha
                    if definicion.fechado is FechadoEvento.PRIMER_PERIODO_SIN_MATRICULA
                    else periodo
                )
                if fecha <= fin_horizonte:
                    evento = fecha
                    if not anula:
                        return resultado(EstadoEtiqueta.POSITIVO, None, evento)
                racha, inicio_racha = 0, None
                if not en_horizonte:
                    break
        elif efecto is Efecto.EVENTO:
            if en_horizonte and evento is None:
                evento = periodo
                if not anula:
                    return resultado(EstadoEtiqueta.POSITIVO, None, evento)
            racha, inicio_racha = 0, None
        elif efecto is Efecto.NO_EVENTO:
            if evento is not None:
                return resultado(EstadoEtiqueta.POSITIVO, None, evento)
            return resultado(EstadoEtiqueta.NEGATIVO, None, None)
        elif efecto is Efecto.NO_OBSERVABLE:
            if evento is not None and categoria is not None and _es_terminal(categoria, efecto):
                return resultado(EstadoEtiqueta.POSITIVO, None, evento)
            return resultado(EstadoEtiqueta.NO_ETIQUETABLE, Motivo.RESULTADO_NO_OBSERVABLE, None)
        elif efecto is Efecto.DESENLACE_EXCLUIDO:
            if evento is not None:
                return resultado(EstadoEtiqueta.POSITIVO, None, evento)
            return resultado(EstadoEtiqueta.NO_ETIQUETABLE, Motivo.DESENLACE_EXCLUIDO, None)

        if categoria is not None and _es_terminal(categoria, efecto):
            if evento is not None:
                return resultado(EstadoEtiqueta.POSITIVO, None, evento)
            return resultado(EstadoEtiqueta.NEGATIVO, None, None)

    horizonte_incompleto = observado_hasta < fin_horizonte
    if evento is not None:
        if anula and horizonte_incompleto:
            # Un reingreso todavía no observado podría anular el evento.
            return resultado(EstadoEtiqueta.NO_ETIQUETABLE, Motivo.SEGUIMIENTO_INCOMPLETO, None)
        return resultado(EstadoEtiqueta.POSITIVO, None, evento)
    confirmacion_pendiente = racha > 0 and len(secuencia) > len(horizonte)
    if horizonte_incompleto or confirmacion_pendiente:
        return resultado(EstadoEtiqueta.NO_ETIQUETABLE, Motivo.SEGUIMIENTO_INCOMPLETO, None)
    return resultado(EstadoEtiqueta.NEGATIVO, None, None)


def _validar_columnas(historial: pd.DataFrame, columnas: ColumnasHistorial) -> None:
    requeridas = [*columnas.unidad, columnas.cohorte, columnas.periodo, columnas.estado]
    faltantes = [c for c in requeridas if c not in historial.columns]
    if faltantes:
        raise ConfiguracionInvalida(
            f"El historial no tiene las columnas {', '.join(faltantes)}.",
            "Revise que el diccionario declare la cohorte, el periodo y el estado de matrícula, "
            "y la columna de carrera si la unidad es estudiante y carrera.",
        )
    if historial[requeridas].isna().any().any():
        raise ConfiguracionInvalida(
            "El historial tiene vacíos en la unidad, la cohorte, el periodo o el estado.",
            "Corrija los datos: la auditoría debe ser apta antes de construir el objetivo.",
        )


def _validar_codigos(historial: pd.DataFrame, columna: str, definicion: DefinicionObjetivo) -> None:
    desconocidos = sorted(set(historial[columna].astype(str)) - set(definicion.catalogo))
    if desconocidos:
        raise ConfiguracionInvalida(
            f"Estados de matrícula sin categoría en el catálogo: {', '.join(desconocidos)}.",
            "Agregue cada código al catálogo de la definición del objetivo (DP-01).",
        )


@dataclass(frozen=True)
class HistorialUnidad:
    """Historial de una unidad de la población inicial, listo para etiquetar."""

    clave: tuple[object, ...]
    cohorte: str
    estados: Mapping[int, str]
    limite_observable: int


@dataclass(frozen=True)
class UnidadesPreparadas:
    unidades: tuple[HistorialUnidad, ...]
    fuera_de_poblacion: int
    fuera_de_cohortes: int


def preparar_unidades(
    historial: pd.DataFrame, columnas: ColumnasHistorial, definicion: DefinicionObjetivo
) -> UnidadesPreparadas:
    """Agrupa el historial por unidad y aplica DP-01b, DP-01c y DP-01k."""
    _validar_columnas(historial, columnas)
    _validar_codigos(historial, columnas.estado, definicion)

    tabla = historial[[*columnas.unidad, columnas.cohorte, columnas.periodo, columnas.estado]]
    tabla = tabla.assign(**{columnas.periodo: tabla[columnas.periodo].astype(int)})
    if definicion.periodos_extraordinarios is PeriodosExtraordinarios.IGNORAR:
        tabla = tabla[~tabla[columnas.periodo].isin(definicion.lista_extraordinarios)]

    cohortes = tabla[columnas.cohorte].astype(str)
    fuera_de_cohortes = 0
    if definicion.cohortes is not None:
        dentro = cohortes.isin(definicion.cohortes)
        fuera_de_cohortes = int(
            tabla.loc[~dentro, list(columnas.unidad)].drop_duplicates().shape[0]
        )
        tabla = tabla[dentro]
    limites = tabla.groupby(columnas.cohorte)[columnas.periodo].max().to_dict()
    primer_regular = _periodos_regulares(definicion, 0, 1)[0]

    unidades: list[HistorialUnidad] = []
    fuera_de_poblacion = 0
    for clave, grupo in tabla.groupby(list(columnas.unidad), sort=True):
        valores_clave = clave if isinstance(clave, tuple) else (clave,)
        cohortes_unidad = grupo[columnas.cohorte].astype(str).unique()
        if len(cohortes_unidad) != 1:
            raise ConfiguracionInvalida(
                f"La unidad {valores_clave} aparece en {len(cohortes_unidad)} cohortes.",
                "Cada unidad debe pertenecer a una sola cohorte; revise los datos o la unidad "
                "de análisis (DP-01b).",
            )
        if grupo[columnas.periodo].duplicated().any():
            raise ConfiguracionInvalida(
                f"La unidad {valores_clave} tiene más de un estado en el mismo periodo.",
                "Revise la unidad de análisis (DP-01b): quizá corresponde a estudiante y carrera.",
            )
        estados = {
            int(periodo): str(codigo)
            for periodo, codigo in zip(grupo[columnas.periodo], grupo[columnas.estado], strict=True)
        }
        if definicion.poblacion_inicial is PoblacionInicial.MATRICULADOS_PRIMER_PERIODO:
            codigo_inicial = estados.get(primer_regular)
            if codigo_inicial is None or definicion.catalogo[codigo_inicial] is not (
                Categoria.MATRICULA
            ):
                fuera_de_poblacion += 1
                continue
        cohorte = str(cohortes_unidad[0])
        unidades.append(
            HistorialUnidad(tuple(valores_clave), cohorte, estados, int(limites[cohorte]))
        )
    return UnidadesPreparadas(tuple(unidades), fuera_de_poblacion, fuera_de_cohortes)


def fila_de_etiqueta(
    unidad: HistorialUnidad, columnas: ColumnasHistorial, etiqueta: Etiqueta
) -> dict[str, object]:
    fila: dict[str, object] = dict(zip(columnas.unidad, unidad.clave, strict=True))
    fila[columnas.cohorte] = unidad.cohorte
    fila[COLUMNA_ESTADO] = etiqueta.estado.value
    fila[COLUMNA_MOTIVO] = etiqueta.motivo.value if etiqueta.motivo else None
    fila[COLUMNA_PERIODO_EVENTO] = etiqueta.periodo_evento
    fila[COLUMNA_ULTIMO_PERIODO] = etiqueta.ultimo_periodo_observado
    return fila


def tabla_de_etiquetas(filas: list[dict[str, object]], columnas: ColumnasHistorial) -> pd.DataFrame:
    columnas_salida = [
        *columnas.unidad,
        columnas.cohorte,
        COLUMNA_ESTADO,
        COLUMNA_MOTIVO,
        COLUMNA_PERIODO_EVENTO,
        COLUMNA_ULTIMO_PERIODO,
    ]
    tabla = pd.DataFrame(filas, columns=columnas_salida)
    for columna in (COLUMNA_PERIODO_EVENTO, COLUMNA_ULTIMO_PERIODO):
        tabla[columna] = tabla[columna].astype("Int64")
    return tabla


def construir_objetivo(
    historial: pd.DataFrame,
    columnas: ColumnasHistorial,
    definicion: DefinicionObjetivo,
    desde: int | None = None,
) -> ResultadoObjetivo:
    """Construye el estado de etiqueta de cada unidad (CU-03).

    Args:
        historial: una fila por unidad y periodo, ya seudonimizada y auditada.
        columnas: nombres de las columnas que usa el objetivo.
        definicion: reglas parametrizadas de DP-01 y DP-18.
        desde: periodo tras el cual empieza el horizonte. Obligatorio si el horizonte
            es relativo a la fecha índice (se aplica por ventana, H2.5); con horizonte
            desde el ingreso debe omitirse.
    """
    if definicion.horizonte_desde is InicioHorizonte.FECHA_INDICE:
        if desde is None:
            raise ConfiguracionInvalida(
                "El horizonte relativo a la fecha índice se calcula para cada ventana.",
                "Se aplica al construir las poblaciones por ventana; para etiquetar "
                "desde el ingreso, declare 'horizonte.desde: ingreso'.",
            )
        inicio = desde
    else:
        if desde is not None:
            raise ConfiguracionInvalida(
                "Con 'horizonte.desde: ingreso' el horizonte no depende de la ventana.",
                "No indique un periodo de inicio.",
            )
        inicio = 0
    preparadas = preparar_unidades(historial, columnas, definicion)
    filas = [
        fila_de_etiqueta(
            unidad,
            columnas,
            etiquetar_unidad(unidad.estados, unidad.limite_observable, definicion, inicio),
        )
        for unidad in preparadas.unidades
    ]
    return ResultadoObjetivo(
        tabla_de_etiquetas(filas, columnas),
        preparadas.fuera_de_poblacion,
        preparadas.fuera_de_cohortes,
    )


def para_modelado(registros: pd.DataFrame) -> pd.DataFrame:
    """Solo las unidades etiquetables: los no etiquetables nunca se entrenan ni evalúan."""
    etiquetables = {EstadoEtiqueta.POSITIVO.value, EstadoEtiqueta.NEGATIVO.value}
    return registros[registros[COLUMNA_ESTADO].isin(etiquetables)].copy()


@dataclass(frozen=True)
class ResumenNoEtiquetables:
    """Proporción de no etiquetables de una cohorte (RF-M2-09, cambio CP-08)."""

    cohorte: str
    unidades: int
    no_etiquetables: int
    por_motivo: Mapping[str, int]
    proporcion: float
    requiere_analisis_sensibilidad: bool


def resumir_no_etiquetables(
    registros: pd.DataFrame, columna_cohorte: str, nivel: float
) -> tuple[ResumenNoEtiquetables, ...]:
    """Cuenta los no etiquetables por cohorte y motivo y marca las que superan el nivel.

    Muestra la distribución de los estados de etiqueta: según RF-M1-03 y RF-M2-09,
    solo puede aplicarse a la partición de desarrollo, después del sellado (H2.5).
    """
    resumenes: list[ResumenNoEtiquetables] = []
    for cohorte, grupo in registros.groupby(columna_cohorte, sort=True):
        no_etiquetables = grupo[grupo[COLUMNA_ESTADO] == EstadoEtiqueta.NO_ETIQUETABLE.value]
        motivos: Counter[str] = Counter(str(m) for m in no_etiquetables[COLUMNA_MOTIVO])
        proporcion = len(no_etiquetables) / len(grupo)
        resumenes.append(
            ResumenNoEtiquetables(
                cohorte=str(cohorte),
                unidades=len(grupo),
                no_etiquetables=len(no_etiquetables),
                por_motivo=dict(sorted(motivos.items())),
                proporcion=proporcion,
                requiere_analisis_sensibilidad=proporcion > nivel,
            )
        )
    return tuple(resumenes)


def codigos_sin_categoria(codigos: Iterable[str], definicion: DefinicionObjetivo) -> list[str]:
    """Códigos declarados (por ejemplo, en el diccionario) que el catálogo no categoriza."""
    return sorted(set(codigos) - set(definicion.catalogo))
