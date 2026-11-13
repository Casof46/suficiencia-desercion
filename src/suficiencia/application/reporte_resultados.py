"""Reportes de resultados (F3.7 y F4.1).

Reporte de una evaluación final, con su comparación con R0 y su interpretabilidad
(F3.7; desde F4.1 también leído del registro), y reporte de los escenarios en validación
por ventana y conjunto, con los cinco modelos de cada escenario (RF-M4-10, RF-M4-14;
F4.1).

Arma, con lo que ya devolvieron los servicios, el reporte comparativo que pide
RF-M6-07 (definición de R0 y de los controles, diferencias con intervalos,
anticipación, reducción de información, estado y limitaciones), las importancias de
la interpretabilidad y las métricas de la evaluación final. No calcula nada nuevo.

Con datos sintéticos, el texto empieza con la leyenda y cada fila de cada tabla lleva
la columna de rótulo (RNF-19, PI-16). El reporte no contiene seudónimos ni
identificadores (RF-M6-04): los registros locales se numeran.
"""

from __future__ import annotations

from collections.abc import Sequence

from suficiencia.application.contratos import (
    ReporteResultados,
    ResultadoComparacion,
    ResultadoEvaluacionFinal,
    ResultadoExplicacion,
    ResultadoMetricas,
    TablaReporte,
)
from suficiencia.domain.trazabilidad.rotulo import (
    CAMPO_ORIGEN,
    LEYENDA_SINTETICA,
    OrigenDatos,
    exigir_rotulo_tabla,
    exigir_rotulo_texto,
    valor_rotulo,
)

LEYENDA = LEYENDA_SINTETICA
"""Leyenda que la interfaz pone en cada gráfico de resultados sintéticos (RNF-19)."""

LIMITACIONES = (
    "Con datos sintéticos solo se prueba el software, nunca la eficacia del método.",
    "El protocolo, las configuraciones y los valores de las decisiones abiertas son "
    "ficticios: ningún resultado es una decisión ni una conclusión del proyecto.",
    "La incertidumbre no incluye el reentrenamiento ni la variación entre cohortes.",
    "La comparación no demuestra que alertar antes cause menos deserción, y nunca se "
    "declara superioridad.",
    "La cobertura temprana (CMP-3) no se calcula: necesita q (DP-08i) y el diseño D3 (DP-17).",
    "Las explicaciones describen asociaciones del modelo, no causas, y están en la escala "
    "del modelo antes de la calibración.",
)


def _origen(*valores: str) -> OrigenDatos:
    """Sintético si cualquiera de las partes lo es."""
    if all(v == OrigenDatos.REAL.value for v in valores):
        return OrigenDatos.REAL
    return OrigenDatos.SINTETICO


def _numero(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.3f}"


def _tabla(
    nombre: str,
    titulo: str,
    columnas: Sequence[str],
    filas: Sequence[Sequence[str | int | float | None]],
    origen: OrigenDatos,
) -> TablaReporte:
    rotulo = valor_rotulo(origen)
    return TablaReporte(
        nombre=nombre,
        titulo=titulo,
        columnas=(*columnas, CAMPO_ORIGEN),
        filas=tuple((*fila, rotulo) for fila in filas),
    )


def _tablas(
    evaluacion: ResultadoEvaluacionFinal,
    comparacion: ResultadoComparacion | None,
    explicacion: ResultadoExplicacion | None,
    origen: OrigenDatos,
) -> tuple[TablaReporte, ...]:
    metricas = [
        (
            c.identificador,
            c.rol,
            c.escenario,
            c.algoritmo,
            c.filas,
            c.eventos,
            c.prevalencia,
            c.umbral,
            nombre,
            e.puntual,
            e.limite_inferior,
            e.limite_superior,
        )
        for c in evaluacion.configuraciones
        for nombre, e in c.metricas.items()
    ]
    no_inferioridad = [
        (
            n.metrica,
            n.diferencia,
            n.limite_unilateral,
            n.limite_inferior,
            n.limite_superior,
            n.margen,
            n.estado,
        )
        for n in (comparacion.no_inferioridad if comparacion else ())
    ]
    controles = [
        (c.codigo, c.escenario, c.algoritmo, m, e.puntual, e.limite_inferior, e.limite_superior)
        for c in (comparacion.controles if comparacion else ())
        for m, e in c.diferencias.items()
    ]
    tablas = [
        _tabla(
            "metricas_prueba",
            "Métricas de la evaluación final, con intervalos",
            (
                "configuracion",
                "rol",
                "escenario",
                "algoritmo",
                "filas",
                "eventos",
                "prevalencia",
                "umbral",
                "metrica",
                "puntual",
                "limite_inferior",
                "limite_superior",
            ),
            metricas,
            origen,
        ),
    ]
    if comparacion is not None:
        tablas += [
            _tabla(
                "no_inferioridad",
                "Diferencias pareadas con R0 y no inferioridad (CMP-1)",
                (
                    "metrica",
                    "diferencia",
                    "limite_unilateral",
                    "limite_inferior",
                    "limite_superior",
                    "margen",
                    "estado",
                ),
                no_inferioridad,
                origen,
            ),
            _tabla(
                "controles",
                "Diferencias con los controles, descriptivas (CMP-2)",
                (
                    "control",
                    "escenario",
                    "algoritmo",
                    "metrica",
                    "diferencia",
                    "limite_inferior",
                    "limite_superior",
                ),
                controles,
                origen,
            ),
        ]
    if explicacion is not None:
        tablas.append(
            _tabla(
                "importancia_bloques",
                "Importancia SHAP por bloque",
                ("configuracion", "rol", "escenario", "algoritmo", "explicador", "escala")
                + ("bloque", "importancia"),
                [
                    (c.identificador, c.rol, c.escenario, c.algoritmo, c.explicador, c.escala)
                    + (b, v)
                    for c in explicacion.configuraciones
                    for b, v in c.importancia_bloques.items()
                ],
                origen,
            )
        )
        tablas.append(
            _tabla(
                "importancia_variables",
                "Importancia SHAP por variable",
                ("configuracion", "variable", "importancia"),
                [
                    (c.identificador, v, i)
                    for c in explicacion.configuraciones
                    for v, i in c.importancia_variables.items()
                ],
                origen,
            )
        )
    return tuple(tablas)


def _texto_comparacion(comparacion: ResultadoComparacion) -> list[str]:
    lineas = [
        f"Seleccionada: {comparacion.seleccionada or 'ninguna'} "
        f"({comparacion.escenario_seleccionado or '—'}). Referencia R0: "
        f"{comparacion.referencia or 'ninguna'} ({comparacion.escenario_referencia or '—'}), "
        "elegida con su propia regla, sin compuerta ni umbrales (DP-19).",
        "",
        "Controles: "
        + (
            "; ".join(f"{c.codigo} ({c.escenario}, {c.algoritmo})" for c in comparacion.controles)
            or "ninguno"
        )
        + ".",
        "",
        f"Población comparada (CMP-1): {comparacion.poblacion_comparada} estudiantes, "
        f"{comparacion.eventos_comparados} eventos.",
        "",
    ]
    if comparacion.no_inferioridad:
        lineas += [
            "| Métrica | Diferencia | Límite unilateral | Intervalo bilateral | Margen | Estado |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        lineas += [
            f"| {n.metrica} | {n.diferencia:+.3f} | {n.limite_unilateral:+.3f} | "
            f"[{n.limite_inferior:+.3f}; {n.limite_superior:+.3f}] | {n.margen:g} | {n.estado} |"
            for n in comparacion.no_inferioridad
        ]
        lineas.append("")
    if comparacion.anticipacion_ventanas is not None:
        lineas += [
            f"Anticipación: {comparacion.anticipacion_ventanas} ventanas, "
            f"{comparacion.anticipacion_ciclos} ciclos. Bloques evitados: "
            f"{', '.join(comparacion.bloques_evitados) or 'ninguno'}; variables evitadas: "
            f"{len(comparacion.variables_evitadas)}.",
            "",
        ]
    motivos = (
        f" ({'; '.join(comparacion.motivos_no_validez)})" if comparacion.motivos_no_validez else ""
    )
    lineas += [
        f"Estado del resultado: **{comparacion.estado}**{motivos}. No se declara superioridad.",
        "",
    ]
    return lineas


def _texto(
    evaluacion: ResultadoEvaluacionFinal,
    comparacion: ResultadoComparacion | None,
    explicacion: ResultadoExplicacion | None,
    origen: OrigenDatos,
    ficticio: bool,
) -> str:
    lineas: list[str] = []
    if origen is OrigenDatos.SINTETICO:
        lineas += [f"> **{LEYENDA_SINTETICA}**", ""]
    lineas += [
        "# Reporte de resultados",
        "",
        f"Protocolo versión {evaluacion.version_protocolo}"
        + (" (FICTICIO)" if ficticio else "")
        + f". Evaluación final {evaluacion.identificador_registro}; accesos permitidos a "
        f"la prueba: {evaluacion.accesos_a_la_prueba}.",
        "",
        "## Evaluación final",
        "",
        f"Regla de suficiencia: **{evaluacion.estado_regla}**"
        + (f" ({evaluacion.escenario_suficiente})" if evaluacion.escenario_suficiente else "")
        + ".",
        "",
        "| Configuración | Rol | Escenario | Algoritmo | n | Eventos | Prevalencia |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    lineas += [
        f"| {c.identificador} | {c.rol} | {c.escenario} | {c.algoritmo} | {c.filas} | "
        f"{c.eventos} | {c.prevalencia:.3f} |"
        for c in evaluacion.configuraciones
    ]
    lineas += ["", "## Comparación con la referencia R0", ""]
    if comparacion is None:
        lineas += ["No hay una evaluación comparativa registrada para esta evaluación final.", ""]
    else:
        lineas += _texto_comparacion(comparacion)
    if explicacion is not None:
        lineas += [
            "## Interpretabilidad",
            "",
            f"Alcance {explicacion.alcance}; niveles {', '.join(explicacion.niveles)}; "
            f"partición de {explicacion.particion}; semilla {explicacion.semilla}.",
            "",
        ]
        for c in explicacion.configuraciones:
            bloques = "; ".join(f"{b} {_numero(v)}" for b, v in c.importancia_bloques.items())
            lineas.append(
                f"- {c.identificador} ({c.escenario}, {c.algoritmo}; explicador {c.explicador}, "
                f"escala {c.escala}): {bloques or 'sin importancia por bloque'}"
            )
        lineas.append("")
    lineas += ["## Limitaciones", ""]
    lineas += [f"- {limitacion}" for limitacion in LIMITACIONES]
    return "\n".join(lineas) + "\n"


def construir_reporte(
    evaluacion: ResultadoEvaluacionFinal,
    comparacion: ResultadoComparacion | None,
    explicacion: ResultadoExplicacion | None,
) -> ReporteResultados:
    """Reporte de una evaluación final con su comparación y su explicación, si existen."""
    origenes = [evaluacion.origen_datos]
    origenes += [r.origen_datos for r in (comparacion, explicacion) if r is not None]
    origen = _origen(*origenes)
    ficticio = evaluacion.ficticio or bool(comparacion and comparacion.ficticio)
    return ReporteResultados(
        origen_datos=origen.value,
        ficticio=ficticio,
        leyenda=LEYENDA_SINTETICA if origen is OrigenDatos.SINTETICO else "",
        texto=_texto(evaluacion, comparacion, explicacion, origen, ficticio),
        tablas=_tablas(evaluacion, comparacion, explicacion, origen),
    )


def exigir_rotulos(reporte: ReporteResultados) -> None:
    """Comprueba el rótulo del texto y de cada tabla antes de exportar (RNF-19, PI-16).

    Raises:
        RotuloFaltante: si alguna parte no lo lleva.
    """
    origen = _origen(reporte.origen_datos)
    exigir_rotulo_texto("reporte.md", reporte.texto, origen)
    for tabla in reporte.tablas:
        posicion = tabla.columnas.index(CAMPO_ORIGEN) if CAMPO_ORIGEN in tabla.columnas else None
        exigir_rotulo_tabla(
            tabla.nombre,
            tabla.columnas,
            [] if posicion is None else [fila[posicion] for fila in tabla.filas],
            origen,
        )


LIMITACIONES_VALIDACION = (
    "Con datos sintéticos solo se prueba el software, nunca la eficacia del método.",
    "Son métricas de validación, en modo exploratorio: el máximo de muchas puntuaciones de "
    "validación es optimista y no es una estimación final.",
    "No se elige ningún escenario ni ningún modelo: eso lo hace la regla de selección (DP-10).",
)


def construir_reporte_validacion(metricas: ResultadoMetricas) -> ReporteResultados:
    """Reporte de los escenarios en validación por ventana y conjunto (RF-M4-10, RF-M4-14).

    Una fila por escenario, familia y métrica, con su intervalo, y en el texto una matriz
    ventana × conjunto por familia con la primera métrica declarada (DP-08a). No calcula
    nada: reordena las métricas de las corridas registradas.
    """
    origen = _origen(metricas.origen_datos)
    nombres = list(dict.fromkeys(m for c in metricas.corridas for m in c.metricas))
    tabla = _tabla(
        "validacion_escenarios",
        "Métricas de validación de cada escenario y familia, con intervalos",
        (
            "escenario",
            "ventana",
            "conjunto",
            "familia",
            "filas",
            "eventos",
            "prevalencia",
            "metrica",
            "puntual",
            "limite_inferior",
            "limite_superior",
        ),
        [
            (c.escenario, c.ventana, c.conjunto, c.familia, c.filas, c.eventos, c.prevalencia)
            + (m, e.puntual, e.limite_inferior, e.limite_superior)
            for c in metricas.corridas
            for m, e in c.metricas.items()
        ],
        origen,
    )
    lineas: list[str] = []
    if origen is OrigenDatos.SINTETICO:
        lineas += [f"> **{LEYENDA_SINTETICA}**", ""]
    lineas += [
        "# Escenarios en validación",
        "",
        f"Configuración de experimentos: {metricas.configuracion_experimentos}"
        + (" (FICTICIA)" if metricas.configuraciones_ficticias else "")
        + f". Intervalos {metricas.metodo} al {metricas.nivel:.0%} con {metricas.replicas} "
        f"réplicas, estratificados por {metricas.estratificacion}. Corridas: "
        f"{len(metricas.corridas)}; registro {metricas.identificador_registro}.",
        "",
    ]
    if nombres:
        principal = nombres[0]
        ventanas = sorted({c.ventana for c in metricas.corridas})
        conjuntos = list(dict.fromkeys(c.conjunto for c in metricas.corridas))
        lineas += [f"## {principal} por ventana y conjunto", ""]
        for familia in dict.fromkeys(c.familia for c in metricas.corridas):
            valores = {
                (c.ventana, c.conjunto): c.metricas[principal].puntual
                for c in metricas.corridas
                if c.familia == familia and principal in c.metricas
            }
            lineas += [
                f"**{familia}**",
                "",
                "| Ventana | " + " | ".join(conjuntos) + " |",
                "| --- |" + " --- |" * len(conjuntos),
            ]
            lineas += [
                f"| {v} | "
                + " | ".join(
                    _numero(valores[(v, k)]) if (v, k) in valores else "·" for k in conjuntos
                )
                + " |"
                for v in ventanas
            ]
            lineas.append("")
        lineas += [
            "«·»: escenario sin corrida de esa familia (no factible o no entrenado). "
            "La tabla `validacion_escenarios` tiene todas las métricas con sus intervalos.",
            "",
        ]
    lineas += ["## Limitaciones", ""]
    lineas += [f"- {limitacion}" for limitacion in LIMITACIONES_VALIDACION]
    return ReporteResultados(
        origen_datos=origen.value,
        ficticio=metricas.configuraciones_ficticias,
        leyenda=LEYENDA_SINTETICA if origen is OrigenDatos.SINTETICO else "",
        texto="\n".join(lineas) + "\n",
        tablas=(tabla,),
    )
