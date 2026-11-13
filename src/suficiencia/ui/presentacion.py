"""Presentación del visor de demostración (H2.D): de contratos a tablas y fragmentos HTML.

No importa Streamlit, para que estas funciones se prueben sin levantar el visor.
Solo recibe contratos de la capa de aplicación (RF-UI-02) y no calcula nada
metodológico: reordena y rotula lo que los servicios ya devolvieron.
"""

from __future__ import annotations

from html import escape

import pandas as pd

from suficiencia.application.contratos import (
    CasoDemostracionObjetivo,
    EstadoProyecto,
    RegistroResumen,
    ResultadoComparacionExperimentos,
    ResultadoDisponibilidadFunciones,
    ResultadoEscenarios,
    ResultadoEstadoDecisiones,
    ResultadoExplicacion,
    ResultadoHistorialExperimentos,
    ResultadoImportacion,
    ResultadoPoblaciones,
)

AVISO_DEMOSTRACION = (
    "Visor de demostración con datos SINTÉTICOS y configuraciones FICTICIAS. "
    "Ninguna cifra de esta aplicación es un resultado de la investigación: la "
    "definición de deserción (DP-01), las poblaciones (DP-04) y la partición (DP-05) "
    "siguen abiertas."
)

# Letra, nombre y color de cada estado de matrícula en la línea de tiempo.
_ESTADOS = {
    "matriculado": ("M", "Matriculado", "#3E7CB1"),
    "no_matriculado": ("A", "No matriculado", "#C8553D"),
    "reserva": ("P", "Reserva", "#E0B04B"),
    "retiro_total": ("R", "Retiro total", "#8E4162"),
    "traslado": ("T", "Traslado", "#5E6472"),
    "-": ("–", "Sin registro", "#C9CDD2"),
}

_RESULTADOS = {
    "positivo": "Deserta",
    "negativo": "No deserta",
    "no_etiquetable": "No etiquetable",
}


def tabla_casos_de_uso(estado: EstadoProyecto) -> pd.DataFrame:
    """Un renglón por caso de uso: servicio, hito y lo que ya está disponible."""
    filas = [
        {
            "Caso de uso": caso.codigo,
            "Nombre": caso.nombre,
            "Servicio": servicio.servicio,
            "Hito": caso.hito,
            "Ya disponible": caso.avance or "—",
        }
        for servicio in estado.servicios
        for caso in servicio.casos_de_uso
    ]
    return pd.DataFrame(filas).sort_values("Caso de uso", ignore_index=True)


def matriz_escenarios(resultado: ResultadoEscenarios) -> pd.DataFrame:
    """Matriz ventana × conjunto: número de variables, o "no factible"."""
    conjuntos = list(dict.fromkeys(e.conjunto for e in resultado.escenarios))
    ventanas = [v.codigo for v in resultado.ventanas]
    matriz = pd.DataFrame(index=ventanas, columns=conjuntos, dtype=object)
    for escenario in resultado.escenarios:
        matriz.loc[escenario.ventana, escenario.conjunto] = (
            f"{len(escenario.variables)} var." if escenario.factible else "no factible"
        )
    matriz.index.name = "Ventana"
    return matriz


def tabla_auditoria(resultado: ResultadoImportacion) -> pd.DataFrame:
    """Columnas auditadas, sin la distribución de la clase (RF-M1-03)."""
    return pd.DataFrame(
        [
            {
                "Columna": c.nombre,
                "Rol": c.rol,
                "Tipo": c.tipo,
                "Nulos": c.nulos,
                "Tipo inválido": c.tipo_invalido,
                "Fuera de dominio": c.fuera_de_dominio,
                "Valores distintos": c.cardinalidad,
            }
            for c in resultado.informe.columnas
        ]
    )


def leyenda_estados() -> str:
    """Leyenda HTML de los colores de la línea de tiempo."""
    elementos = "".join(
        f'<span class="suf-ley"><span class="suf-celda" style="background:{color}">'
        f"{letra}</span>{escape(nombre)}</span>"
        for letra, nombre, color in _ESTADOS.values()
    )
    return f'<div class="suf-leyenda">{elementos}</div>'


def resultado_caso(caso: CasoDemostracionObjetivo) -> str:
    """Texto del resultado de un caso de la demostración."""
    texto = _RESULTADOS.get(caso.estado, caso.estado)
    if caso.periodo_evento is not None:
        texto += f" (evento en el periodo {caso.periodo_evento})"
    if caso.motivo:
        texto += f": {caso.motivo.replace('_', ' ')}"
    return texto


def linea_de_tiempo(caso: CasoDemostracionObjetivo, horizonte: int) -> str:
    """Historial de un caso como fila de celdas; marca el horizonte y el evento."""
    celdas = []
    for periodo in range(1, max(len(caso.historial), horizonte) + 1):
        clases = ["suf-celda"]
        if periodo == horizonte:
            clases.append("suf-horizonte")
        if periodo == caso.periodo_evento:
            clases.append("suf-evento")
        if periodo <= len(caso.historial):
            letra, nombre, color = _ESTADOS.get(
                caso.historial[periodo - 1], ("?", caso.historial[periodo - 1], "#999999")
            )
            estilo = f"background:{color}"
        elif periodo <= caso.periodos_observables:
            letra, nombre, estilo = "", "Sin dato en el historial", "background:#EDEFF1"
        else:
            letra, nombre, estilo = "", "Fuera de lo observable", "background:transparent"
            clases.append("suf-vacia")
        celdas.append(
            f'<span class="{" ".join(clases)}" style="{estilo}" '
            f'title="Periodo {periodo}: {escape(nombre)}">{letra}</span>'
        )
    return f'<div class="suf-linea">{"".join(celdas)}</div>'


def tabla_seguimiento(resultado: ResultadoPoblaciones) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Cohorte": s.cohorte,
                "Partición": s.particion,
                "Unidades": s.unidades,
                "Observable hasta el periodo": s.ultimo_periodo_observable,
                "Periodo necesario": s.periodo_necesario,
                "Seguimiento": "completo" if s.completo else "INCOMPLETO",
            }
            for s in resultado.seguimiento
        ]
    )


def tabla_poblaciones(resultado: ResultadoPoblaciones) -> pd.DataFrame:
    """D1, D2 y D3 por ventana, solo de desarrollo (RF-M2-12)."""
    return pd.DataFrame(
        [
            {
                "Diseño": d.diseno,
                "Ventana": d.ventana,
                "Tamaño": d.tamano,
                "Eventos": d.eventos,
                "Prevalencia": d.prevalencia,
                "Eventos detectables": (
                    "—" if d.eventos_detectables is None else str(d.eventos_detectables)
                ),
            }
            for d in resultado.descripciones_desarrollo
        ]
    )


COLORES_DISENOS = ["#2B5D8A", "#E0B04B", "#8E4162"]


def serie_tamanos(resultado: ResultadoPoblaciones) -> pd.DataFrame:
    """Tamaño de cada diseño por ventana, para el gráfico (solo desarrollo)."""
    tabla = tabla_poblaciones(resultado)
    serie = tabla.pivot(index="Ventana", columns="Diseño", values="Tamaño")
    serie.columns.name = None
    return serie


def tabla_no_etiquetables(resultado: ResultadoPoblaciones) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Cohorte": n.cohorte,
                "Unidades": n.unidades,
                "No etiquetables": n.no_etiquetables,
                "Proporción": n.proporcion,
                "Motivos": ", ".join(f"{m}: {k}" for m, k in sorted(n.por_motivo.items())),
                "Requiere sensibilidad (CP-08)": "sí" if n.requiere_analisis_sensibilidad else "no",
            }
            for n in resultado.no_etiquetables_desarrollo
        ]
    )


def tabla_accesos(registros: tuple[RegistroResumen, ...]) -> pd.DataFrame:
    """Registro de accesos a la prueba, del más reciente al más antiguo."""
    filas = [
        {
            "N.º": r.numero,
            "Fecha (UTC)": r.fecha,
            "Operación": r.contenido.get("operacion", ""),
            "Resultado": "PERMITIDO" if r.contenido.get("permitido") else "RECHAZADO",
            "Motivo": r.contenido.get("motivo", ""),
        }
        for r in registros
    ]
    columnas = ["N.º", "Fecha (UTC)", "Operación", "Resultado", "Motivo"]
    return pd.DataFrame(filas, columns=columnas).iloc[::-1].reset_index(drop=True)


def tabla_locales(explicacion: ResultadoExplicacion) -> pd.DataFrame:
    """Explicaciones locales por registro numerado; sin seudónimos (F3.7)."""
    filas = [
        {
            "Configuración": c.identificador,
            "Registro": r.registro,
            "SHAP (principales)": "; ".join(f"{x.variable} {x.valor:+.3f}" for x in r.shap),
            "LIME (principales)": "; ".join(f"{x.variable} {x.valor:+.3f}" for x in r.lime),
            "R² de LIME": round(r.lime_ajuste, 2),
        }
        for c in explicacion.configuraciones
        for r in c.locales
    ]
    columnas = [
        "Configuración",
        "Registro",
        "SHAP (principales)",
        "LIME (principales)",
        "R² de LIME",
    ]
    return pd.DataFrame(filas, columns=columnas)


def tabla_decisiones(estado: ResultadoEstadoDecisiones) -> pd.DataFrame:
    """Estado de DP-01 a DP-20 con su última decisión registrada, si existe (RF-UI-04)."""
    filas = [
        {
            "Código": d.codigo,
            "Decisión": d.nombre,
            "Quién decide": d.decide,
            "Resolver antes de": d.resolver_antes_de,
            "Estado": "REGISTRADA" if d.registrada else "ABIERTA",
            "Registros": "; ".join(f"{r.codigo} ({r.fecha[:10]})" for r in d.registros) or "—",
        }
        for d in estado.decisiones
    ]
    columnas = ["Código", "Decisión", "Quién decide", "Resolver antes de", "Estado", "Registros"]
    return pd.DataFrame(filas, columns=columnas)


def tabla_funciones(resultado: ResultadoDisponibilidadFunciones) -> pd.DataFrame:
    """Cada función del visor, sus decisiones y si queda desactivada con datos del proyecto."""
    filas = [
        {
            "Función": f.nombre,
            "Depende de": ", ".join(f.decisiones),
            "Abiertas": ", ".join(f.abiertas) or "—",
            "Con datos del proyecto": "Disponible" if f.con_datos_del_proyecto else "DESACTIVADA",
            "Con el ejemplo ficticio": "Disponible",
        }
        for f in resultado.funciones
    ]
    columnas = [
        "Función",
        "Depende de",
        "Abiertas",
        "Con datos del proyecto",
        "Con el ejemplo ficticio",
    ]
    return pd.DataFrame(filas, columns=columnas)


def tabla_historial(resultado: ResultadoHistorialExperimentos) -> pd.DataFrame:
    """Experimentos del registro, del más reciente al más antiguo (RF-M6-02)."""
    filas = [
        {
            "N.º": e.numero,
            "Fecha (UTC)": e.fecha,
            "Identificador": e.identificador,
            "Tipo": e.tipo,
            "Modo": e.modo,
            "Estado": e.estado,
            "Escenario": e.escenario or "—",
            "Familia": e.familia or "—",
            "Origen de los datos": e.origen_datos,
            "Error": e.error or "",
        }
        for e in resultado.experimentos
    ]
    columnas = [
        "N.º",
        "Fecha (UTC)",
        "Identificador",
        "Tipo",
        "Modo",
        "Estado",
        "Escenario",
        "Familia",
        "Origen de los datos",
        "Error",
    ]
    return pd.DataFrame(filas, columns=columnas).iloc[::-1].reset_index(drop=True)


def tabla_comparacion_experimentos(
    comparacion: ResultadoComparacionExperimentos, solo_diferencias: bool
) -> pd.DataFrame:
    """Campos de dos experimentos lado a lado; opcionalmente, solo los distintos."""
    columna_a, columna_b = f"A ({comparacion.a})", f"B ({comparacion.b})"
    filas = [
        {
            "Campo": c.campo,
            columna_a: c.valor_a,
            columna_b: c.valor_b,
            "Igual": "sí" if c.igual else "no",
        }
        for c in comparacion.campos
        if not (solo_diferencias and c.igual)
    ]
    return pd.DataFrame(filas, columns=["Campo", columna_a, columna_b, "Igual"])
