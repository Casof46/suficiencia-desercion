"""Resultados de evaluación, comparación y explicación escritos a mano (EJEMPLO FICTICIO).

Para probar el reporte y los gráficos de F3.7 sin entrenar modelos. Todas las cifras
son inventadas: no salen de ningún modelo ni de ningún dato.
"""

from __future__ import annotations

from suficiencia.application.contratos import (
    ContribucionResumen,
    ControlResumen,
    EstimacionResumen,
    ExplicacionConfiguracionResumen,
    ExplicacionLocalResumen,
    MetricasCorridaResumen,
    MetricasPruebaResumen,
    NoInferioridadResumen,
    ResultadoComparacion,
    ResultadoEvaluacionFinal,
    ResultadoExplicacion,
    ResultadoMetricas,
)


def _estimacion(puntual: float, ancho: float) -> EstimacionResumen:
    return EstimacionResumen(
        puntual=puntual,
        limite_inferior=puntual - ancho,
        limite_superior=puntual + ancho,
        replicas_validas=200,
    )


def evaluacion(origen: str = "sintetico") -> ResultadoEvaluacionFinal:
    configuraciones = tuple(
        MetricasPruebaResumen(
            identificador=identificador,
            rol=rol,
            escenario=escenario,
            algoritmo="lr",
            filas=100,
            eventos=20,
            prevalencia=0.2,
            umbral=0.3,
            metricas={"auc_roc": _estimacion(auc, 0.05), "brier_escalado": _estimacion(0.1, 0.03)},
            con_umbral={"accuracy": 0.7, "precision": 0.4, "recall": 0.5, "f1": 0.44},
        )
        for identificador, rol, escenario, auc in (
            ("SEL-T1|A+F", "seleccionada", "T1|A+F", 0.7),
            ("R0", "referencia_r0", "T3|A+F+S+B", 0.65),
            ("R-ven-T1", "control", "T1|A+F+S+B", 0.72),
        )
    )
    return ResultadoEvaluacionFinal(
        version_protocolo=1,
        ficticio=True,
        origen_datos=origen,
        configuraciones=configuraciones,
        estado_regla="escenario_suficiente",
        escenario_suficiente="T1|A+F",
        detalle_regla=("T1|A+F: cumple",),
        identificador_registro="EXP-ficticio-1",
        accesos_a_la_prueba=1,
    )


def comparacion(origen: str = "sintetico") -> ResultadoComparacion:
    return ResultadoComparacion(
        evaluacion="EXP-ficticio-1",
        version_protocolo=1,
        ficticio=True,
        origen_datos=origen,
        estado="C3_no_inferioridad_no_demostrada",
        motivos_no_validez=(),
        seleccionada="SEL-T1|A+F",
        escenario_seleccionado="T1|A+F",
        referencia="R0",
        escenario_referencia="T3|A+F+S+B",
        poblacion_comparada=90,
        eventos_comparados=15,
        no_inferioridad=(
            NoInferioridadResumen(
                metrica="auc_roc",
                diferencia=0.05,
                limite_unilateral=-0.03,
                limite_inferior=-0.05,
                limite_superior=0.15,
                margen=0.05,
                estado="demostrada",
            ),
        ),
        anticipacion_ventanas=2,
        anticipacion_ciclos=2,
        bloques_evitados=("B", "S"),
        variables_evitadas=("tipo_colegio",),
        controles=(
            ControlResumen(
                codigo="R-ven-T1",
                escenario="T1|A+F+S+B",
                algoritmo="lr",
                filas=100,
                diferencias={"auc_roc": _estimacion(-0.02, 0.04)},
            ),
        ),
        identificador_registro="EXP-ficticio-2",
        accesos_a_la_prueba=1,
    )


def explicacion(origen: str = "sintetico") -> ResultadoExplicacion:
    return ResultadoExplicacion(
        evaluacion="EXP-ficticio-1",
        version_protocolo=1,
        ficticio=True,
        origen_datos=origen,
        alcance="todas_congeladas",
        niveles=("global", "bloque", "local"),
        particion="desarrollo",
        semilla=1,
        configuraciones=(
            ExplicacionConfiguracionResumen(
                identificador="SEL-T1|A+F",
                rol="seleccionada",
                escenario="T1|A+F",
                algoritmo="lr",
                explicador="lineal",
                escala="log_odds",
                filas_particion=500,
                filas_fondo=50,
                filas_explicadas=100,
                valor_base=-1.2,
                error_aditividad=0.0,
                importancia_variables={"promedio_ciclo": 0.3, "deuda_vencida_ciclo": 0.1},
                importancia_bloques={"A": 0.3, "F": 0.1},
                locales=(
                    ExplicacionLocalResumen(
                        registro=1,
                        shap=(ContribucionResumen(variable="promedio_ciclo", valor=-0.4),),
                        lime=(ContribucionResumen(variable="promedio_ciclo", valor=-0.1),),
                        lime_ajuste=0.5,
                    ),
                ),
            ),
        ),
        carpeta="workspace/explicaciones/ficticia",
        identificador_registro="EXP-ficticio-3",
        accesos_a_la_prueba=1,
    )


def metricas(origen: str = "sintetico") -> ResultadoMetricas:
    """Métricas de validación de tres escenarios; svm solo en T1|A (EJEMPLO FICTICIO)."""
    corridas = []
    for escenario, base in (("T0|A", 0.55), ("T1|A", 0.62), ("T1|A+F", 0.64)):
        for posicion, familia in enumerate(("lr", "rf", "xgboost", "lightgbm", "svm")):
            if familia == "svm" and escenario != "T1|A":
                continue
            corridas.append(
                MetricasCorridaResumen(
                    identificador=f"EXP-{escenario}-{familia}",
                    escenario=escenario,
                    ventana=escenario.split("|")[0],
                    conjunto=escenario.split("|")[1],
                    familia=familia,
                    filas=300,
                    eventos=60,
                    prevalencia=0.2,
                    metricas={
                        "auc_roc": _estimacion(base + posicion / 100, 0.04),
                        "brier": _estimacion(0.15, 0.01),
                    },
                )
            )
    return ResultadoMetricas(
        configuracion_experimentos="Experimentos ficticios",
        configuraciones_ficticias=True,
        origen_datos=origen,
        metodo="percentil",
        nivel=0.95,
        replicas=200,
        estratificacion="cohorte_resultado",
        q=None,
        corridas=tuple(corridas),
        identificador_registro="EXP-ficticio-4",
    )
