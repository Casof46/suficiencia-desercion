"""Gráficos Plotly de la página de resultados del visor (RF-UI-03; F3.7).

No importa Streamlit, para que los gráficos se prueben sin levantar el visor. Solo
recibe contratos de la capa de aplicación y no calcula nada metodológico: dibuja lo
que los servicios ya devolvieron. Con datos sintéticos, cada gráfico lleva el rótulo
en el título y la leyenda completa debajo (RNF-19, PI-16).
"""

from __future__ import annotations

import plotly.graph_objects as go

from suficiencia.application.contratos import (
    ResultadoComparacion,
    ResultadoEvaluacionFinal,
    ResultadoExplicacion,
)
from suficiencia.application.reporte_resultados import LEYENDA

ROTULO_TITULO = "DATOS SINTÉTICOS"
COLORES = ["#2B5D8A", "#C8553D", "#E0B04B", "#5E6472", "#8E4162"]
COLORES_BLOQUES = {"A": "#2B5D8A", "F": "#E0B04B", "S": "#8E4162", "B": "#5E6472"}


def _sintetico(origen: str) -> bool:
    return origen != "real"


def _rotular(figura: go.Figure, titulo: str, origen: str) -> go.Figure:
    """Título con el rótulo y la leyenda completa al pie (RNF-19)."""
    if _sintetico(origen):
        titulo = f"{ROTULO_TITULO} · {titulo}"
        figura.add_annotation(
            text=LEYENDA,
            xref="paper",
            yref="paper",
            x=0,
            y=-0.28,
            showarrow=False,
            xanchor="left",
            font={"size": 11, "color": "#C8553D"},
        )
    figura.update_layout(
        title={"text": titulo},
        margin={"b": 110},
        template="plotly_white",
        legend={"orientation": "h", "y": 1.08},
    )
    return figura


def figura_metricas(evaluacion: ResultadoEvaluacionFinal, metrica: str) -> go.Figure:
    """Una métrica de la evaluación final por configuración, con su intervalo."""
    nombres, puntuales, arriba, abajo = [], [], [], []
    for c in evaluacion.configuraciones:
        estimacion = c.metricas.get(metrica)
        if estimacion is None or estimacion.puntual is None:
            continue
        nombres.append(f"{c.identificador}<br>{c.escenario}, {c.algoritmo}")
        puntuales.append(estimacion.puntual)
        superior = estimacion.limite_superior
        inferior = estimacion.limite_inferior
        arriba.append(None if superior is None else superior - estimacion.puntual)
        abajo.append(None if inferior is None else estimacion.puntual - inferior)
    figura = go.Figure(
        go.Scatter(
            x=nombres,
            y=puntuales,
            mode="markers",
            marker={"size": 11, "color": COLORES[0]},
            error_y={"type": "data", "array": arriba, "arrayminus": abajo},
            name=metrica,
        )
    )
    figura.update_yaxes(title_text=metrica)
    titulo = f"Evaluación final: {metrica} con su intervalo"
    return _rotular(figura, titulo, evaluacion.origen_datos)


def figura_no_inferioridad(comparacion: ResultadoComparacion) -> go.Figure:
    """Diferencia pareada con R0, su intervalo bilateral y el margen −δ de cada métrica."""
    figura = go.Figure()
    for posicion, n in enumerate(comparacion.no_inferioridad):
        figura.add_trace(
            go.Scatter(
                x=[n.diferencia],
                y=[n.metrica],
                mode="markers",
                marker={"size": 12, "color": COLORES[posicion % len(COLORES)]},
                error_x={
                    "type": "data",
                    "array": [n.limite_superior - n.diferencia],
                    "arrayminus": [n.diferencia - n.limite_inferior],
                },
                name=f"{n.metrica}: {n.estado}",
            )
        )
        figura.add_shape(
            type="line",
            x0=-n.margen,
            x1=-n.margen,
            y0=posicion - 0.3,
            y1=posicion + 0.3,
            line={"color": "#C8553D", "dash": "dash"},
        )
    figura.add_vline(x=0, line={"color": "#1B2430", "width": 1})
    figura.update_xaxes(title_text="Diferencia con R0 (mayor es mejor); línea roja: −margen")
    return _rotular(
        figura,
        f"Comparación con R0: {comparacion.estado}",
        comparacion.origen_datos,
    )


def figura_bloques(explicacion: ResultadoExplicacion) -> go.Figure:
    """Parte de la importancia SHAP de cada configuración que corresponde a cada bloque.

    Se muestran proporciones porque las escalas cambian entre familias (log-odds,
    probabilidad o margen) y las importancias absolutas no se comparan entre ellas.
    """
    figura = go.Figure()
    configuraciones = [
        f"{c.identificador}<br>{c.escenario}, {c.algoritmo}" for c in explicacion.configuraciones
    ]
    bloques = list(
        dict.fromkeys(b for c in explicacion.configuraciones for b in c.importancia_bloques)
    )
    totales = [sum(c.importancia_bloques.values()) for c in explicacion.configuraciones]
    for bloque in bloques:
        figura.add_trace(
            go.Bar(
                x=configuraciones,
                y=[
                    c.importancia_bloques.get(bloque, 0) / total if total > 0 else 0
                    for c, total in zip(explicacion.configuraciones, totales, strict=True)
                ],
                name=bloque,
                marker_color=COLORES_BLOQUES.get(bloque, COLORES[3]),
            )
        )
    figura.update_layout(barmode="stack")
    figura.update_yaxes(title_text="Proporción de la importancia", tickformat=".0%")
    return _rotular(
        figura,
        "Importancia por bloque: asociaciones del modelo, no causas",
        explicacion.origen_datos,
    )
