#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_dataset_sintetico.py
============================

DATOS 100 % SINTÉTICOS. NO PROVIENEN DE NINGUNA UNIVERSIDAD NI INSTITUCIÓN REAL.

Genera el entorno de prueba técnica del OE3 de la investigación
"Método temporal para determinar la suficiencia de información en la detección
temprana del riesgo de deserción académica mediante Machine Learning".

El generador reproduce la ESTRUCTURA de la formulación del manuscrito
(ventanas T0–T3 con orígenes o_c(t), bloques A/F/S/B, ocho conjuntos con A como
base, admisibilidad Σ_t, poblaciones anidadas R(t), etiqueta Y con H = 4 y
reservas, partición cronológica por cohortes). Las relaciones entre variables y
riesgo son SUPUESTOS ARTIFICIALES del generador: no describen estudiantes reales
y no sirven como evidencia empírica del método.

Uso:
    python generar_dataset_sintetico.py                 # semilla 20261023, carpeta ./salida
    python generar_dataset_sintetico.py --salida otra --semilla 20261023
    python generar_dataset_sintetico.py --sin-validar   # solo genera datos

Dependencias: Python >= 3.10, numpy, pandas, openpyxl (sin archivos externos).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import zipfile
from datetime import date, timedelta

import numpy as np
import pandas as pd

# =============================================================================
# 1. PARÁMETROS DE SIMULACIÓN (no son estimaciones de ninguna población real)
# =============================================================================
VERSION = "1.0.0"
SEMILLA_DEFECTO = 20261023

H = 4                                   # horizonte en ciclos regulares (propuesta del paper)
VENTANAS = ["T0", "T1", "T2", "T3"]
ORD = {v: i for i, v in enumerate(VENTANAS)}
BLOQUES = ["A", "F", "S", "B"]
NOMBRE_BLOQUE = {"A": "Académico", "F": "Financiero", "S": "Socioeconómico", "B": "Conductual"}
CONJUNTOS = ["A", "A+F", "A+S", "A+B", "A+F+S", "A+F+B", "A+S+B", "A+F+S+B"]

N_COHORTES = 12                         # cohortes semestrales cronológicas
PRIMER_ANIO = 2011                      # calendario sintético (anterior a 2020 a propósito)
MAX_CICLO_SIM = 8                       # ciclos regulares simulados por episodio
CICLOS_DETALLADOS = 4                   # ciclos con notas, pagos y LMS registro a registro
FECHA_CORTE_DATOS = date(2018, 1, 15)   # fecha de extracción sintética
SEMANAS = 16
NOTA_APROBATORIA = 12.0                 # escala vigesimal 0–20 (parámetro sintético)
C0 = 2                                  # cohortes mínimas del primer bloque de entrenamiento
N_COHORTES_PRUEBA = 2                   # cohortes etiquetadas más recientes reservadas

AREAS = ["ingenieria", "negocios", "salud", "comunicaciones_humanidades", "arquitectura_diseno"]
P_AREAS = [0.30, 0.27, 0.15, 0.15, 0.13]
EFECTO_AREA_NOTA = {"ingenieria": -0.5, "negocios": 0.2, "salud": 0.0,
                    "comunicaciones_humanidades": 0.3, "arquitectura_diseno": -0.2}
EFECTO_AREA_RIESGO = {"ingenieria": 0.05, "negocios": 0.0, "salud": -0.10,
                      "comunicaciones_humanidades": 0.05, "arquitectura_diseno": 0.0}
PENSION_ESCALA = {1: 780.0, 2: 1080.0, 3: 1420.0, 4: 1810.0, 5: 2290.0}   # S/ por cuota (sintético)
RANGOS_INGRESO = ["R1_hasta_1500", "R2_1501_3000", "R3_3001_5000", "R4_5001_8000", "R5_mas_de_8000"]
B0_RIESGO = {1: -3.40, 2: -3.50, 3: -3.60, 4: -3.70}   # interceptos del riesgo de no matrícula

ESTADO_M = "matriculado"
ESTADO_N = "no_matriculado"
ESTADO_R = "reserva_aprobada"
ESTADO_F = "baja_por_fallecimiento"
COD = {ESTADO_M: "M", ESTADO_N: "N", ESTADO_R: "R", ESTADO_F: "F"}


def sig(x):
    return 1.0 / (1.0 + np.exp(-x))


# =============================================================================
# 2. CALENDARIO SINTÉTICO Y ORÍGENES o_c(t)
# =============================================================================
def periodo_label(p: int) -> str:
    return f"{PRIMER_ANIO + (p - 1) // 2}-{1 if p % 2 == 1 else 2}"


def calendario(p: int) -> dict:
    anio = PRIMER_ANIO + (p - 1) // 2
    if p % 2 == 1:
        cm, ic = date(anio, 3, 20), date(anio, 3, 23)
    else:
        cm, ic = date(anio, 8, 21), date(anio, 8, 24)
    fc = ic + timedelta(days=SEMANAS * 7 - 1)
    return {"periodo": periodo_label(p), "cierre_matricula": cm, "inicio_clases": ic,
            "fin_clases": fc, "cierre_notas": fc + timedelta(days=14)}


P_OBS = max(p for p in range(1, 60) if calendario(p)["cierre_matricula"] <= FECHA_CORTE_DATOS)


def origen(c: int, t: str) -> date:
    """o_c(t): T0 = cierre de matrícula del ciclo 1; Tj = cierre de notas del ciclo j."""
    if t == "T0":
        return calendario(c)["cierre_matricula"]
    j = ORD[t]
    return calendario(c + j - 1)["cierre_notas"]


def ultimo_ciclo_observado(c: int) -> int:
    return min(MAX_CICLO_SIM, P_OBS - c + 1)


# =============================================================================
# 3. DICCIONARIO DE VARIABLES PREDICTORAS (variables lógicas j con b(j) y α(j))
# =============================================================================
PEND = "Supuesto sintético pendiente de verificación institucional"
VARS = [
    # ------------------------------ A — académico ------------------------------
    dict(nombre="puntaje_admision", bloque="A", alfa="T0", tipo="numérico continuo",
         unidad="puntos (escala sintética 0–100)", rmin=0, rmax=100, cats=None, tv="estática",
         desc="Puntaje del examen de admisión. Solo existe para la modalidad examen_admision (faltante estructural en otras modalidades).",
         fuente="fuentes_crudas/estudiantes_admision.csv (fecha_admision)",
         gen="55 + 11·z_acad + N(0, 8), recortado a [0, 100]; NaN si modalidad ≠ examen_admision.",
         disp="Registrado en la fecha de admisión, anterior a o(T0).",
         fuga="Bajo: registro previo a T0.",
         uso="Predictor desde T0. Imputar dentro del bloque de entrenamiento con indicador de faltante.",
         verif=PEND + ": existencia y escala del puntaje."),
    dict(nombre="promedio_secundaria", bloque="A", alfa="T0", tipo="numérico continuo",
         unidad="nota vigesimal (0–20)", rmin=11, rmax=20, cats=None, tv="estática",
         desc="Promedio de educación secundaria declarado en la admisión.",
         fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="14,8 + 1,4·z_acad + N(0, 0,9), recortado a [11, 20].",
         disp="Registrado en la admisión, anterior a o(T0).", fuga="Bajo.",
         uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="modalidad_admision", bloque="A", alfa="T0", tipo="categórica nominal",
         unidad="categorías", rmin=None, rmax=None,
         cats=["examen_admision", "evaluacion_preferente", "admision_por_merito"], tv="estática",
         desc="Modalidad de ingreso dentro del régimen regular.",
         fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="admision_por_merito si z_acad > 0,9 con prob. 0,45; si no, evaluacion_preferente con prob. 0,22; resto examen_admision.",
         disp="Registrada en la admisión.", fuga="Bajo.",
         uso="Predictor desde T0 (codificación one-hot ajustada en entrenamiento).", verif=PEND + "."),
    dict(nombre="area_programa", bloque="A", alfa="T0", tipo="categórica nominal",
         unidad="categorías", rmin=None, rmax=None, cats=AREAS, tv="estática",
         desc="Área genérica del programa al ingreso (no corresponde a carreras reales).",
         fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="Multinomial con probabilidades " + ", ".join(f"{a} {p}" for a, p in zip(AREAS, P_AREAS)) + ".",
         disp="Registrada en la admisión.", fuga="Bajo.",
         uso="Predictor desde T0. Los cambios de programa posteriores no se usan como predictor.", verif=PEND + "."),
    dict(nombre="creditos_matriculados_ultimo_ciclo", bloque="A", alfa="T0", tipo="numérico entero",
         unidad="créditos", rmin=9, rmax=35, cats=None, tv="valor a o(t)",
         desc="Créditos matriculados en el ciclo de referencia (ciclo 1 en T0 y T1; ciclo j en Tj).",
         fuente="fuentes_crudas/matricula_ciclos.csv (fecha_registro_estado)",
         gen="Suma de créditos de 3–7 cursos (créditos 3, 4 o 5); menos cursos si trabaja > 20 h.",
         disp="La matrícula del ciclo j se registra antes de su cierre de matrícula, anterior a o(Tj). La matrícula del ciclo j+1 es posterior a o(Tj) y no se usa.",
         fuga="Medio: la matrícula del ciclo siguiente revela permanencia; el constructor solo usa registros con fecha ≤ o(t).",
         uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="cursos_matriculados_ultimo_ciclo", bloque="A", alfa="T0", tipo="numérico entero",
         unidad="cursos", rmin=3, rmax=7, cats=None, tv="valor a o(t)",
         desc="Número de cursos matriculados en el ciclo de referencia.",
         fuente="fuentes_crudas/matricula_ciclos.csv",
         gen="round(5,6 − 0,9·[horas > 20] + N(0, 0,6)) recortado a [3, 7].",
         disp="Igual que creditos_matriculados_ultimo_ciclo.", fuga="Igual que la anterior.",
         uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="promedio_ultimo_ciclo", bloque="A", alfa="T1", tipo="numérico continuo",
         unidad="nota vigesimal (0–20)", rmin=0, rmax=20, cats=None, tv="valor a o(t)",
         desc="Promedio ponderado por créditos de los cursos calificados del ciclo j (ventana Tj).",
         fuente="fuentes_crudas/cursos_notas.csv (fecha_registro_nota = cierre de notas)",
         gen="Nota por curso = 13,6 + 2,2·z_acad + 0,6·z_motiv − 0,8·[horas>20] − 0,5·dificultad_financiera − 0,5·choque − 0,4·desenganche + efecto_área + 0,2·(ciclo−1) + N(0, 0,8) + N(0, 2,2); recortada a [0, 20]; si inasistencia > 30 % la nota se reduce a U(2, 8).",
         disp="Las notas consolidadas del ciclo j existen desde el cierre de notas del ciclo j = o(Tj). No existen en T0.",
         fuga="Bajo si se respeta α = T1.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="promedio_ponderado_acum", bloque="A", alfa="T1", tipo="numérico continuo",
         unidad="nota vigesimal (0–20)", rmin=0, rmax=20, cats=None, tv="valor a o(t)",
         desc="Promedio ponderado acumulado de los ciclos 1..j.",
         fuente="fuentes_crudas/cursos_notas.csv", gen="Derivado fila a fila de las notas por curso.",
         disp="Desde o(T1).", fuga="Bajo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="variacion_promedio_ultimo_ciclo", bloque="A", alfa="T2", tipo="numérico continuo",
         unidad="puntos de nota", rmin=-20, rmax=20, cats=None, tv="valor a o(t)",
         desc="Promedio del ciclo j menos promedio del ciclo j−1 (evolución del rendimiento).",
         fuente="fuentes_crudas/cursos_notas.csv", gen="Derivado de las notas por curso.",
         disp="Requiere dos ciclos calificados: primera ventana T2.", fuga="Bajo.",
         uso="Predictor desde T2.", verif=PEND + "."),
    dict(nombre="creditos_aprobados_acum", bloque="A", alfa="T1", tipo="numérico entero",
         unidad="créditos", rmin=0, rmax=110, cats=None, tv="valor a o(t)",
         desc="Créditos aprobados (nota ≥ 12) acumulados hasta el ciclo j.",
         fuente="fuentes_crudas/cursos_notas.csv", gen="Derivado de notas y créditos.",
         disp="Desde o(T1).", fuga="Bajo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="tasa_aprobacion_creditos_acum", bloque="A", alfa="T1", tipo="proporción",
         unidad="fracción 0–1", rmin=0, rmax=1, cats=None, tv="valor a o(t)",
         desc="Créditos aprobados / créditos matriculados (incluye retirados) de los ciclos 1..j.",
         fuente="fuentes_crudas/cursos_notas.csv", gen="Derivado.",
         disp="Desde o(T1).", fuga="Bajo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="cursos_desaprobados_ultimo_ciclo", bloque="A", alfa="T1", tipo="numérico entero",
         unidad="cursos", rmin=0, rmax=7, cats=None, tv="valor a o(t)",
         desc="Cursos calificados con nota < 12 en el ciclo j.", fuente="fuentes_crudas/cursos_notas.csv",
         gen="Derivado.", disp="Desde o(T1).", fuga="Bajo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="cursos_desaprobados_acum", bloque="A", alfa="T1", tipo="numérico entero",
         unidad="cursos", rmin=0, rmax=28, cats=None, tv="valor a o(t)",
         desc="Cursos desaprobados acumulados en los ciclos 1..j.", fuente="fuentes_crudas/cursos_notas.csv",
         gen="Derivado.", disp="Desde o(T1).", fuga="Bajo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="cursos_retirados_acum", bloque="A", alfa="T1", tipo="numérico entero",
         unidad="cursos", rmin=0, rmax=28, cats=None, tv="valor a o(t)",
         desc="Retiros de cursos individuales con fecha ≤ o(t).", fuente="fuentes_crudas/cursos_notas.csv (fecha_retiro)",
         gen="P(retiro de un curso) = σ(−3,6 + 0,5·choque + 0,5·desenganche − 0,3·z_acad); fecha entre los días 35 y 80 del ciclo.",
         disp="Los retiros ocurren durante el ciclo, después de o(T0); se usan desde T1.",
         fuga="Medio: un retiro registrado después de o(t) no debe contarse; el constructor filtra por fecha.",
         uso="Predictor desde T1.", verif=PEND + ": fecha de registro de retiros."),
    dict(nombre="pct_inasistencia_ultimo_ciclo", bloque="A", alfa="T1", tipo="porcentaje",
         unidad="% de sesiones (0–100)", rmin=0, rmax=100, cats=None, tv="valor a o(t)",
         desc="Inasistencia ponderada por créditos de los cursos calificados del ciclo j, consolidada al cierre de notas.",
         fuente="fuentes_crudas/cursos_notas.csv",
         gen="Por curso: 7 + 8·desenganche + 4·choque − 2·z_motiv + N(0, 5), recortado a [0, 70].",
         disp="Se supone consolidada al cierre de notas (no hay registro diario fechado): desde T1.",
         fuga="Medio si se usara asistencia parcial con fecha desconocida; aquí solo el consolidado.",
         uso="Predictor desde T1.", verif=PEND + ": disponibilidad y fecha de la asistencia."),
    # ------------------------------ F — financiero ------------------------------
    dict(nombre="escala_pension", bloque="F", alfa="T0", tipo="ordinal entera",
         unidad="escala 1 (menor) – 5 (mayor)", rmin=1, rmax=5, cats=None, tv="estática",
         desc="Escala de pensión asignada al ingreso.", fuente="fuentes_crudas/estudiantes_admision.csv (fecha_registro_financiamiento)",
         gen="round(3 + 1,0·ses + N(0, 0,7)) recortado a [1, 5].",
         disp="Asignada antes de o(T0).", fuga="Bajo.", uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="tipo_financiamiento", bloque="F", alfa="T0", tipo="categórica nominal",
         unidad="categorías", rmin=None, rmax=None,
         cats=["ninguno", "beca_parcial", "beca_integral", "credito_educativo"], tv="estática",
         desc="Beca o financiamiento asignado al ingreso.", fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="beca_integral si z_acad>1,2 y ses<−0,2 con prob. 0,35; beca_parcial con prob. σ(−2,9+0,9·z_acad−0,4·ses); credito_educativo con prob. σ(−3,1−0,8·ses).",
         disp="Asignado antes de o(T0).", fuga="Bajo.", uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="pct_beca", bloque="F", alfa="T0", tipo="numérico discreto",
         unidad="% de descuento sobre la pensión", rmin=0, rmax=100, cats=None, tv="estática",
         desc="Porcentaje de descuento de la beca (0, 25, 50 o 100).", fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="100 si beca_integral; 25 o 50 si beca_parcial; 0 en otro caso.",
         disp="Asignado antes de o(T0).", fuga="Bajo.", uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="saldo_pendiente_soles", bloque="F", alfa="T1", tipo="numérico continuo",
         unidad="soles (S/)", rmin=0, rmax=60000, cats=None, tv="valor a o(t)",
         desc="Monto de cuotas vencidas a o(t) que no tienen pago registrado con fecha ≤ o(t).",
         fuente="fuentes_crudas/pagos_cuotas.csv (fecha_vencimiento, fecha_pago)",
         gen="Cuotas de pensión 2–5 por ciclo (días 20, 48, 76 y 104 del ciclo); retraso según dificultad financiera del ciclo.",
         disp="La primera cuota de pensión vence después de o(T0); en T0 solo existe el derecho de matrícula, pagado al matricularse. Por eso α = T1.",
         fuga="ALTO si se usan pagos posteriores al corte (p. ej., regularizaciones para matricularse en el ciclo siguiente). El constructor ignora todo pago con fecha > o(t).",
         uso="Predictor desde T1.", verif=PEND + ": fechas confiables de pago."),
    dict(nombre="cuotas_vencidas_impagas", bloque="F", alfa="T1", tipo="numérico entero",
         unidad="cuotas", rmin=0, rmax=20, cats=None, tv="valor a o(t)",
         desc="Número de cuotas vencidas sin pago registrado a o(t).", fuente="fuentes_crudas/pagos_cuotas.csv",
         gen="Derivado.", disp="Igual que saldo_pendiente_soles.", fuga="Igual que saldo_pendiente_soles.",
         uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="pct_obligaciones_vencidas_impagas", bloque="F", alfa="T1", tipo="proporción",
         unidad="fracción 0–1 del monto vencido", rmin=0, rmax=1, cats=None, tv="valor a o(t)",
         desc="Monto vencido e impago / monto total vencido a o(t).", fuente="fuentes_crudas/pagos_cuotas.csv",
         gen="Derivado.", disp="Igual que saldo_pendiente_soles.", fuga="Igual que saldo_pendiente_soles.",
         uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="dias_atraso_promedio_pagos", bloque="F", alfa="T1", tipo="numérico continuo",
         unidad="días", rmin=0, rmax=400, cats=None, tv="valor a o(t)",
         desc="Promedio de max(0, fecha_pago − fecha_vencimiento) de las cuotas pagadas hasta o(t).",
         fuente="fuentes_crudas/pagos_cuotas.csv", gen="Derivado.",
         disp="Igual que saldo_pendiente_soles.", fuga="Igual que saldo_pendiente_soles.",
         uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="max_dias_atraso_vigente", bloque="F", alfa="T1", tipo="numérico entero",
         unidad="días", rmin=0, rmax=500, cats=None, tv="valor a o(t)",
         desc="Mayor antigüedad (o(t) − vencimiento) entre las cuotas vencidas e impagas a o(t); 0 si no hay.",
         fuente="fuentes_crudas/pagos_cuotas.csv", gen="Derivado.",
         disp="Igual que saldo_pendiente_soles.", fuga="Igual que saldo_pendiente_soles.",
         uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="cuotas_pagadas_con_atraso_acum", bloque="F", alfa="T1", tipo="numérico entero",
         unidad="cuotas", rmin=0, rmax=20, cats=None, tv="valor a o(t)",
         desc="Cuotas pagadas hasta o(t) con más de 7 días de retraso.", fuente="fuentes_crudas/pagos_cuotas.csv",
         gen="Derivado.", disp="Igual que saldo_pendiente_soles.", fuga="Igual que saldo_pendiente_soles.",
         uso="Predictor desde T1.", verif=PEND + "."),
    # ------------------------------ S — socioeconómico ------------------------------
    dict(nombre="edad_ingreso", bloque="S", alfa="T0", tipo="numérico entero",
         unidad="años", rmin=16, rmax=35, cats=None, tv="estática",
         desc="Edad al ingreso según el registro de admisión.", fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="16–20 con prob. 0,06/0,42/0,30/0,14/0,08; 7 % suma 3–10 años.",
         disp="Registro de admisión, anterior a o(T0).", fuga="Bajo.", uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="tipo_colegio", bloque="S", alfa="T0", tipo="categórica nominal",
         unidad="categorías", rmin=None, rmax=None, cats=["publico", "privado"], tv="estática",
         desc="Tipo de institución de educación secundaria.", fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="privado con prob. σ(0,2 + 1,3·ses).", disp="Registro de admisión.", fuga="Bajo.",
         uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="region_procedencia", bloque="S", alfa="T0", tipo="categórica nominal",
         unidad="categorías", rmin=None, rmax=None, cats=["capital", "otra_region"], tv="estática",
         desc="Procedencia geográfica genérica.", fuente="fuentes_crudas/estudiantes_admision.csv",
         gen="otra_region con prob. σ(−1,45 + 0,3·trabaja).", disp="Registro de admisión.", fuga="Bajo.",
         uso="Predictor desde T0.", verif=PEND + "."),
    dict(nombre="encuesta_respondida", bloque="S", alfa="T1", tipo="binaria",
         unidad="0/1", rmin=0, rmax=1, cats=None, tv="valor a o(t)",
         desc="Indicador de que existe la encuesta socioeconómica (bloque S de encuesta completo o ausente).",
         fuente="fuentes_crudas/encuesta_socioeconomica.csv (fecha_respuesta)",
         gen="Responde con prob. σ(1,6 + 0,4·z_motiv), entre los días 14 y 42 del ciclo 1, si no se retiró antes.",
         disp="La encuesta se aplica durante el ciclo 1, después de o(T0): α = T1.",
         fuga="Medio: la no respuesta se relaciona con la motivación latente (supuesto).",
         uso="Indicador de bloque faltante (el paper pide representarlo con un indicador).",
         verif="Requiere una encuesta institucional específica. " + PEND + "."),
    dict(nombre="ingreso_hogar_rango", bloque="S", alfa="T1", tipo="categórica ordinal",
         unidad="rango de ingreso mensual del hogar (S/)", rmin=None, rmax=None, cats=RANGOS_INGRESO, tv="estática desde T1",
         desc="Rango de ingreso del hogar declarado en la encuesta.", fuente="fuentes_crudas/encuesta_socioeconomica.csv",
         gen="Cortes de ses + N(0, 0,5) en −1,0, −0,2, 0,5 y 1,3.", disp="Desde la respuesta de la encuesta (T1).",
         fuga="Bajo.", uso="Predictor desde T1; NaN si no respondió.", verif="Requiere encuesta. " + PEND + "."),
    dict(nombre="trabaja", bloque="S", alfa="T1", tipo="binaria",
         unidad="0/1", rmin=0, rmax=1, cats=None, tv="estática desde T1",
         desc="El estudiante declara trabajar.", fuente="fuentes_crudas/encuesta_socioeconomica.csv",
         gen="Latente: trabaja con prob. σ(−1,15 − 0,9·ses + 0,3·(edad−18)); 4 % de error de declaración.",
         disp="Desde la encuesta (T1).", fuga="Bajo.", uso="Predictor desde T1.", verif="Requiere encuesta. " + PEND + "."),
    dict(nombre="horas_trabajo_semana", bloque="S", alfa="T1", tipo="numérico entero",
         unidad="horas por semana", rmin=0, rmax=60, cats=None, tv="estática desde T1",
         desc="Horas semanales de trabajo declaradas (0 si no trabaja).", fuente="fuentes_crudas/encuesta_socioeconomica.csv",
         gen="Latente N(22 − 4·ses, 8) recortado a [6, 48]; declarado con error N(0, 3).",
         disp="Desde la encuesta (T1).", fuga="Bajo.", uso="Predictor desde T1.", verif="Requiere encuesta. " + PEND + "."),
    dict(nombre="apoyo_economico_familiar", bloque="S", alfa="T1", tipo="categórica ordinal",
         unidad="categorías", rmin=None, rmax=None, cats=["total", "parcial", "ninguno"], tv="estática desde T1",
         desc="Disponibilidad de apoyo económico familiar declarada.", fuente="fuentes_crudas/encuesta_socioeconomica.csv",
         gen="total con prob. σ(0,3 + ses − trabaja); del resto, parcial con prob. 0,6.",
         disp="Desde la encuesta (T1).", fuga="Bajo.", uso="Predictor desde T1.", verif="Requiere encuesta. " + PEND + "."),
    dict(nombre="primera_generacion_universitaria", bloque="S", alfa="T1", tipo="binaria",
         unidad="0/1", rmin=0, rmax=1, cats=None, tv="estática desde T1",
         desc="Ningún progenitor con estudios universitarios (declarado).", fuente="fuentes_crudas/encuesta_socioeconomica.csv",
         gen="Prob. σ(−0,4 − 1,0·ses).", disp="Desde la encuesta (T1).", fuga="Bajo.",
         uso="Predictor desde T1.", verif="Requiere encuesta. " + PEND + "."),
    # ------------------------------ B — conductual ------------------------------
    dict(nombre="accesos_ultimo_ciclo", bloque="B", alfa="T1", tipo="numérico entero",
         unidad="accesos", rmin=0, rmax=2000, cats=None, tv="valor a o(t)",
         desc="Accesos a la plataforma virtual en el ciclo j hasta o(t).", fuente="fuentes_crudas/lms_semanal.csv (fecha_fin_semana)",
         gen="Poisson(9·exp(0,3·z_motiv + 0,1·z_acad − 0,15·choque)·exp(−desenganche·(semana−1)/15)·Gamma(4, 0,25)) por semana.",
         disp="No hay registros de plataforma antes del inicio de clases, posterior a o(T0): α = T1.",
         fuga="Medio: actividad posterior a o(t) (p. ej., del ciclo siguiente) no debe usarse; el constructor filtra por fecha.",
         uso="Predictor desde T1.", verif=PEND + ": registros del aula virtual y su fecha."),
    dict(nombre="dias_activos_ultimo_ciclo", bloque="B", alfa="T1", tipo="numérico entero",
         unidad="días", rmin=0, rmax=112, cats=None, tv="valor a o(t)",
         desc="Días con al menos un acceso en el ciclo j.", fuente="fuentes_crudas/lms_semanal.csv",
         gen="Por semana: 0 si no hay accesos; si no, 1 + Binomial(6, min(0,9, accesos/(accesos+6))).",
         disp="Igual que accesos_ultimo_ciclo.", fuga="Igual que accesos_ultimo_ciclo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="actividades_entregadas_ultimo_ciclo", bloque="B", alfa="T1", tipo="numérico entero",
         unidad="actividades", rmin=0, rmax=32, cats=None, tv="valor a o(t)",
         desc="Actividades entregadas en el ciclo j (2 asignadas por semana).", fuente="fuentes_crudas/lms_semanal.csv",
         gen="Binomial(2, σ(1,5 + 0,6·z_motiv + 0,2·z_acad − 0,5·choque − 1,3·desenganche·(semana−1)/15)); 0 si no hubo accesos.",
         disp="Igual que accesos_ultimo_ciclo.", fuga="Igual que accesos_ultimo_ciclo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="pct_actividades_entregadas_ultimo_ciclo", bloque="B", alfa="T1", tipo="proporción",
         unidad="fracción 0–1", rmin=0, rmax=1, cats=None, tv="valor a o(t)",
         desc="Entregadas / asignadas en el ciclo j.", fuente="fuentes_crudas/lms_semanal.csv", gen="Derivado.",
         disp="Igual que accesos_ultimo_ciclo.", fuga="Igual que accesos_ultimo_ciclo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="dias_desde_ultima_actividad", bloque="B", alfa="T1", tipo="numérico entero",
         unidad="días", rmin=0, rmax=900, cats=None, tv="valor a o(t)",
         desc="o(t) − fecha de la última actividad registrada con fecha ≤ o(t).", fuente="fuentes_crudas/lms_semanal.csv (fecha_ultima_actividad)",
         gen="Derivado. Sin actividad registrada: o(t) − inicio de clases del ciclo 1.",
         disp="Igual que accesos_ultimo_ciclo.", fuga="Igual que accesos_ultimo_ciclo.", uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="tendencia_accesos_ultimo_ciclo", bloque="B", alfa="T1", tipo="numérico continuo",
         unidad="razón (semanas 9–16 + 1)/(semanas 1–8 + 1)", rmin=0, rmax=1000, cats=None, tv="valor a o(t)",
         desc="Cambio de la actividad dentro del ciclo j (valores < 1 indican caída).", fuente="fuentes_crudas/lms_semanal.csv",
         gen="Derivado.", disp="Igual que accesos_ultimo_ciclo.", fuga="Igual que accesos_ultimo_ciclo.",
         uso="Predictor desde T1.", verif=PEND + "."),
    dict(nombre="accesos_acum", bloque="B", alfa="T1", tipo="numérico entero",
         unidad="accesos", rmin=0, rmax=6000, cats=None, tv="valor a o(t)",
         desc="Accesos acumulados en los ciclos 1..j hasta o(t).", fuente="fuentes_crudas/lms_semanal.csv",
         gen="Derivado.", disp="Igual que accesos_ultimo_ciclo.", fuga="Igual que accesos_ultimo_ciclo.",
         uso="Predictor desde T1.", verif=PEND + "."),
]
VAR_INDEX = {v["nombre"]: v for v in VARS}


def col_wide(t: str, v: dict) -> str:
    return f"{t}_{v['bloque']}_{v['nombre']}"


def variables_en_ventana(t: str):
    return [v for v in VARS if ORD[v["alfa"]] <= ORD[t]]


def bloques_admisibles(t: str):
    return [b for b in BLOQUES if any(v["bloque"] == b for v in variables_en_ventana(t))]


def conjuntos_admisibles(t: str):
    disp = set(bloques_admisibles(t))
    return [s for s in CONJUNTOS if set(s.split("+")) <= disp]


def conjunto_mas_completo(t: str) -> str:
    return "+".join(b for b in BLOQUES if b in bloques_admisibles(t))


class ConjuntoNoAplicable(Exception):
    """Par (ventana, conjunto) con s ∉ Σ_t: se registra como 'no aplicable', no se rellena."""


def columnas_conjunto(t: str, conjunto: str):
    if conjunto not in CONJUNTOS:
        raise ValueError(f"Conjunto desconocido: {conjunto}")
    if conjunto not in conjuntos_admisibles(t):
        raise ConjuntoNoAplicable(f"({t}, {conjunto}) no aplicable: algún bloque no tiene variables con α ≤ {t}")
    bl = set(conjunto.split("+"))
    return [col_wide(t, v) for v in variables_en_ventana(t) if v["bloque"] in bl]


def construir_matriz(wide: pd.DataFrame, t: str, conjunto: str, cohortes=None):
    """Devuelve (ids, X) para el escenario (t, s) sobre R(t). No incluye la etiqueta.
    La imputación, codificación y escalamiento deben ajustarse después, solo con cohortes de ajuste."""
    cols = columnas_conjunto(t, conjunto)
    df = wide[wide[f"en_riesgo_{t}"] == 1]
    if cohortes is not None:
        df = df[df["cohorte"].isin(list(cohortes))]
    return df["id_estudiante"].reset_index(drop=True), df[cols].reset_index(drop=True)


# =============================================================================
# 4. SIMULACIÓN DEL "MUNDO" SINTÉTICO (registros fechados)
# =============================================================================
def simular(semilla: int) -> dict:
    rng = np.random.default_rng(semilla)

    # ---- cohortes y episodios ----
    tam = [int((400 if c % 2 == 1 else 262) + rng.integers(-20, 21)) for c in range(1, N_COHORTES + 1)]
    n = sum(tam)
    cohorte = np.repeat(np.arange(1, N_COHORTES + 1), tam)
    efecto_cohorte = rng.normal(0, 0.12, N_COHORTES)

    alfabeto = np.array(list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789"))
    cand = ["SYN-" + "".join(r) for r in rng.choice(alfabeto, (int(n * 1.1), 8))]
    ids = list(dict.fromkeys(cand))[:n]
    assert len(ids) == n

    # ---- latentes (nunca se exportan) ----
    ses = rng.normal(size=n)
    z_acad = 0.35 * ses + np.sqrt(1 - 0.35 ** 2) * rng.normal(size=n)
    z_motiv = 0.20 * z_acad + np.sqrt(1 - 0.20 ** 2) * rng.normal(size=n)
    z_fin = -0.55 * ses + np.sqrt(1 - 0.55 ** 2) * rng.normal(size=n)

    edad = rng.choice([16, 17, 18, 19, 20], size=n, p=[0.06, 0.42, 0.30, 0.14, 0.08])
    mayor = rng.random(n) < 0.07
    edad[mayor] += rng.integers(3, 11, mayor.sum())
    trabaja = rng.random(n) < sig(-1.15 - 0.9 * ses + 0.30 * (edad - 18))
    horas = np.where(trabaja, np.clip(np.round(rng.normal(22 - 4 * ses, 8)), 6, 48), 0).astype(int)
    pesado = horas > 20

    area = rng.choice(AREAS, size=n, p=P_AREAS)
    r_mod = rng.random(n)
    merito = (z_acad > 0.9) & (r_mod < 0.45)
    pref = (~merito) & (rng.random(n) < 0.22)
    modalidad = np.where(merito, "admision_por_merito", np.where(pref, "evaluacion_preferente", "examen_admision"))
    puntaje = np.where(modalidad == "examen_admision",
                       np.round(np.clip(55 + 11 * z_acad + rng.normal(0, 8, n), 0, 100), 1), np.nan)
    prom_sec = np.round(np.clip(14.8 + 1.4 * z_acad + rng.normal(0, 0.9, n), 11, 20), 2)
    privado = rng.random(n) < sig(0.2 + 1.3 * ses)
    otra_region = rng.random(n) < sig(-1.45 + 0.3 * trabaja)
    escala = np.clip(np.round(3 + 1.0 * ses + rng.normal(0, 0.7, n)), 1, 5).astype(int)
    integral = (z_acad > 1.2) & (ses < -0.2) & (rng.random(n) < 0.35)
    parcial = (~integral) & (rng.random(n) < sig(-2.9 + 0.9 * z_acad - 0.4 * ses))
    credito = (~integral) & (~parcial) & (rng.random(n) < sig(-3.1 - 0.8 * ses))
    tipo_fin = np.where(integral, "beca_integral", np.where(parcial, "beca_parcial",
                        np.where(credito, "credito_educativo", "ninguno")))
    pct_beca = np.where(integral, 100, np.where(parcial, rng.choice([25, 50], n), 0)).astype(int)

    responde = rng.random(n) < sig(1.6 + 0.4 * z_motiv)
    ingreso_r = np.digitize(ses + rng.normal(0, 0.5, n), [-1.0, -0.2, 0.5, 1.3])
    error_decl = rng.random(n) < 0.04
    trabaja_decl = np.where(error_decl, ~trabaja, trabaja)
    horas_decl = np.where(trabaja_decl,
                          np.where(trabaja, np.clip(np.round(horas + rng.normal(0, 3, n)), 4, 60),
                                   rng.integers(6, 20, n)), 0).astype(int)
    p_total = sig(0.3 + 1.0 * ses - 1.0 * trabaja)
    r_ap = rng.random(n)
    apoyo = np.where(r_ap < p_total, "total", np.where(r_ap < p_total + 0.6 * (1 - p_total), "parcial", "ninguno"))
    primera_gen = rng.random(n) < sig(-0.4 - 1.0 * ses)

    est_rows, mat_rows, cur_rows, pag_rows, lms_rows, enc_rows = [], [], [], [], [], []

    for i in range(n):
        c = int(cohorte[i])
        sid = ids[i]
        cal1 = calendario(c)
        f_adm = cal1["cierre_matricula"] - timedelta(days=int(rng.integers(20, 121)))
        f_fin = min(f_adm + timedelta(days=int(rng.integers(3, 15))), cal1["cierre_matricula"] - timedelta(days=1))
        est_rows.append(dict(
            id_estudiante=sid, cohorte=c, periodo_ingreso=cal1["periodo"],
            fecha_admision=f_adm, modalidad_admision=modalidad[i], puntaje_admision=puntaje[i],
            promedio_secundaria=prom_sec[i], area_programa=area[i], edad_ingreso=int(edad[i]),
            tipo_colegio="privado" if privado[i] else "publico",
            region_procedencia="otra_region" if otra_region[i] else "capital",
            fecha_registro_financiamiento=f_fin, escala_pension=int(escala[i]),
            tipo_financiamiento=tipo_fin[i], pct_beca=int(pct_beca[i])))

        pension = PENSION_ESCALA[int(escala[i])] * (1 - pct_beca[i] / 100.0)
        derecho = round(0.45 * PENSION_ESCALA[int(escala[i])], 2)
        estado = ESTADO_M
        consec_n = consec_r = 0
        separado = fallecido = False
        rt_prev = False
        acum_cred_cal = acum_suma = acum_desap = 0.0
        pendientes = []          # cuotas impagas al cierre del ciclo anterior
        f_cierre_prev = None
        siguiente = ESTADO_M

        for k in range(1, MAX_CICLO_SIM + 1):
            p = c + k - 1
            cal = calendario(p)
            estado = ESTADO_M if k == 1 else siguiente
            fila = dict(id_estudiante=sid, ciclo_regular=k, periodo_academico=cal["periodo"],
                        estado_matricula=estado, fecha_registro_estado=None,
                        creditos_matriculados=np.nan, cursos_matriculados=np.nan,
                        retiro_total=0, fecha_retiro_total=None, cambio_programa=0,
                        separacion_academica=0, fecha_separacion=None,
                        fallecimiento_registrado=0, fecha_fallecimiento=None)

            # regularización de deudas del ciclo anterior (registros POSTERIORES a o(T_{k-1}))
            if pendientes:
                for pr in pendientes:
                    if estado == ESTADO_M:
                        pr["fecha_pago"] = cal["cierre_matricula"] - timedelta(days=int(rng.integers(1, 16)))
                    elif estado == ESTADO_R and rng.random() < 0.6:
                        pr["fecha_pago"] = cal["cierre_matricula"] - timedelta(days=int(rng.integers(1, 16)))
                    elif estado == ESTADO_N and rng.random() < 0.25:
                        pr["fecha_pago"] = f_cierre_prev + timedelta(days=int(rng.integers(60, 500)))
                pendientes = []

            rt = False
            if estado == ESTADO_M:
                consec_n = consec_r = 0
                f_mat = cal["cierre_matricula"] - timedelta(days=int(rng.integers(0, 21)))
                fila["fecha_registro_estado"] = f_mat
                if k >= 2 and rng.random() < 0.02:
                    fila["cambio_programa"] = 1
                if k <= CICLOS_DETALLADOS:
                    choque = rng.normal()
                    dif_fin = (pct_beca[i] < 100) and (rng.random() < sig(-2.3 + 1.0 * z_fin[i] + 0.45 * choque + 0.3 * credito[i]))
                    desen = max(0.0, 0.15 + 0.30 * (-z_motiv[i]) + 0.30 * choque + rng.normal(0, 0.25))
                    n_cur = int(np.clip(np.round(5.6 - 0.9 * pesado[i] + rng.normal(0, 0.6)), 3, 7))
                    creds = rng.choice([3, 4, 4, 4, 5], n_cur).astype(int)
                    fila["creditos_matriculados"] = int(creds.sum())
                    fila["cursos_matriculados"] = n_cur
                    # retiros individuales y retiro total
                    ret_ind = rng.random(n_cur) < sig(-3.6 + 0.5 * choque + 0.5 * desen - 0.3 * z_acad[i])
                    f_ret_ind = [cal["inicio_clases"] + timedelta(days=int(rng.integers(35, 81))) for _ in range(n_cur)]
                    rt = rng.random() < sig(-4.4 + 0.7 * choque + 0.6 * desen + 0.4 * dif_fin + 1.0 * rt_prev)
                    f_rt = cal["inicio_clases"] + timedelta(days=int(rng.integers(25, 96))) if rt else None
                    if (not rt) and ret_ind.all():          # retirarse de todos los cursos = retiro total
                        rt = True
                        f_rt = max(f_ret_ind)
                    # cursos
                    suma_c = cred_cal = cred_desap = 0.0
                    n_desap = 0
                    base = (13.6 + 2.2 * z_acad[i] + 0.6 * z_motiv[i] - 0.8 * pesado[i] - 0.5 * dif_fin
                            - 0.5 * choque - 0.4 * desen + EFECTO_AREA_NOTA[area[i]] + 0.2 * (k - 1))
                    for q in range(n_cur):
                        retirado = bool(ret_ind[q]) or rt
                        f_r = None
                        if retirado:
                            f_r = f_ret_ind[q] if ret_ind[q] else f_rt
                            if rt and f_r > f_rt:
                                f_r = f_rt
                        nota = inas = np.nan
                        f_nota = None
                        if not retirado:
                            nota = float(np.clip(base + rng.normal(0, 0.8) + rng.normal(0, 2.2), 0, 20))
                            inas = float(np.clip(7 + 8 * desen + 4 * choque - 2 * z_motiv[i] + rng.normal(0, 5), 0, 70))
                            if inas > 30:
                                nota = min(nota, float(rng.uniform(2, 8)))
                            nota, inas = round(nota, 1), round(inas, 1)
                            f_nota = cal["cierre_notas"]
                            suma_c += nota * creds[q]
                            cred_cal += creds[q]
                            if nota < NOTA_APROBATORIA:
                                n_desap += 1
                                cred_desap += creds[q]
                        cur_rows.append(dict(id_estudiante=sid, ciclo_regular=k, curso=f"C{k}{q + 1:02d}",
                                             creditos=int(creds[q]), retirado=int(retirado), fecha_retiro=f_r,
                                             nota_final=nota, pct_inasistencia=inas, fecha_registro_nota=f_nota,
                                             fecha_cierre_ciclo=cal["cierre_notas"]))
                    if rt:
                        fila["retiro_total"] = 1
                        fila["fecha_retiro_total"] = f_rt
                    prom_k = suma_c / cred_cal if cred_cal > 0 else np.nan
                    acum_cred_cal += cred_cal
                    acum_suma += suma_c
                    acum_desap += n_desap
                    prom_acum = acum_suma / acum_cred_cal if acum_cred_cal > 0 else np.nan
                    frac_desap = cred_desap / max(1, creds.sum())

                    # plataforma virtual (semanal)
                    sem_fin = SEMANAS if not rt else min(SEMANAS, (f_rt - cal["inicio_clases"]).days // 7 + 1)
                    nivel = 9.0 * np.exp(0.30 * z_motiv[i] + 0.10 * z_acad[i] - 0.15 * choque)
                    for w in range(1, sem_fin + 1):
                        ini_w = cal["inicio_clases"] + timedelta(days=7 * (w - 1))
                        fin_w = ini_w + timedelta(days=6)
                        lam = nivel * np.exp(-desen * (w - 1) / 15.0) * rng.gamma(4.0, 0.25)
                        acc = int(rng.poisson(lam))
                        dias = 0 if acc == 0 else int(min(7, 1 + rng.binomial(6, min(0.9, acc / (acc + 6.0)))))
                        ent = 0 if dias == 0 else int(rng.binomial(2, sig(1.5 + 0.6 * z_motiv[i] + 0.2 * z_acad[i]
                                                                        - 0.5 * choque - 1.3 * desen * (w - 1) / 15.0)))
                        ult = None
                        if acc > 0:
                            ult = ini_w + timedelta(days=int(rng.integers(0, 7)))
                            if rt and ult > f_rt:
                                ult = f_rt
                        lms_rows.append(dict(id_estudiante=sid, ciclo_regular=k, semana=w, fecha_fin_semana=fin_w,
                                             accesos=acc, dias_activos=dias, actividades_asignadas=2,
                                             actividades_entregadas=ent, fecha_ultima_actividad=ult))
                    # encuesta socioeconómica (solo ciclo 1)
                    if k == 1 and responde[i]:
                        f_enc = cal["inicio_clases"] + timedelta(days=int(rng.integers(14, 43)))
                        if not (rt and f_rt <= f_enc):
                            enc_rows.append(dict(id_estudiante=sid, fecha_respuesta=f_enc,
                                                 ingreso_hogar_rango=RANGOS_INGRESO[int(ingreso_r[i])],
                                                 trabaja=int(trabaja_decl[i]), horas_trabajo_semana=int(horas_decl[i]),
                                                 apoyo_economico_familiar=apoyo[i],
                                                 primera_generacion_universitaria=int(primera_gen[i])))
                    # pagos
                    pag_rows.append(dict(id_estudiante=sid, ciclo_regular=k, n_cuota=1, concepto="derecho_matricula",
                                         monto=derecho, fecha_vencimiento=f_mat, fecha_pago=f_mat))
                    deuda_fin = False
                    if pension > 0:
                        for nc in range(2, 6):
                            venc = cal["inicio_clases"] + timedelta(days=20 + 28 * (nc - 2))
                            if rt and venc > f_rt:
                                continue                      # cuota anulada por retiro total
                            reg = dict(id_estudiante=sid, ciclo_regular=k, n_cuota=nc, concepto=f"pension_cuota_{nc}",
                                       monto=round(pension, 2), fecha_vencimiento=venc, fecha_pago=None)
                            if dif_fin:
                                if rng.random() < 0.38:
                                    pendientes.append(reg)
                                else:
                                    reg["fecha_pago"] = venc + timedelta(days=int(rng.exponential(28 + 6 * (nc - 2))) + 1)
                            else:
                                if rng.random() < 0.015:
                                    pendientes.append(reg)
                                else:
                                    reg["fecha_pago"] = venc + timedelta(days=int(np.clip(np.round(rng.normal(0.5, 4)), -10, 60)))
                            if reg["fecha_pago"] is None or reg["fecha_pago"] > cal["cierre_notas"]:
                                deuda_fin = True
                            pag_rows.append(reg)
                    # separación académica (registro administrativo posterior al cierre de notas)
                    if k >= 2 and not rt and (not np.isnan(prom_acum)) and prom_acum < 9.5 and acum_desap >= 5 \
                            and rng.random() < 0.4:
                        separado = True
                        fila["separacion_academica"] = 1
                        fila["fecha_separacion"] = cal["cierre_notas"] + timedelta(days=15)
                    # riesgo de no matrícula en k+1 (solo información anterior a la decisión)
                    p_eff = prom_k if not np.isnan(prom_k) else 8.0
                    lp = (B0_RIESGO[k] + efecto_cohorte[c - 1] + EFECTO_AREA_RIESGO[area[i]]
                          - 0.40 * z_motiv[i] - 0.15 * (p_eff - 12) / 2 + 0.5 * frac_desap + 0.6 * dif_fin
                          + 0.50 * deuda_fin + 0.30 * pesado[i] + 0.70 * desen + 0.30 * choque + 0.20 * z_fin[i]
                          + 0.35 * pesado[i] * (creds.sum() >= 22)
                          + (0.3 if (not np.isnan(prom_acum) and prom_acum < 10.5) else 0.0)
                          + (1.3 if rt else 0.0))
                    p_res = sig(-3.8 + 0.5 * dif_fin + 0.3 * choque)
                else:
                    rt = rng.random() < 0.02
                    if rt:
                        fila["retiro_total"] = 1
                        fila["fecha_retiro_total"] = cal["inicio_clases"] + timedelta(days=int(rng.integers(25, 96)))
                    lp = (-3.0 + efecto_cohorte[c - 1] - 0.45 * z_motiv[i] + 0.25 * z_fin[i] - 0.25 * z_acad[i]
                          + 0.35 * pesado[i] + 1.3 * rt + rng.normal(0, 0.5))
                    p_res = 0.02
                rt_prev = rt
                f_cierre_prev = cal["cierre_notas"]
                # transición a k+1
                u = rng.random()
                if separado:
                    siguiente = ESTADO_N
                elif u < p_res:
                    siguiente = ESTADO_R
                elif u < p_res + sig(lp):
                    siguiente = ESTADO_N
                else:
                    siguiente = ESTADO_M
            elif estado == ESTADO_N:
                consec_n += 1
                consec_r = 0
                fila["fecha_registro_estado"] = cal["cierre_matricula"]
                f_cierre_prev = cal["cierre_notas"]
                if separado:
                    siguiente = ESTADO_N
                else:
                    p_ret = sig(-0.85 + 0.3 * z_motiv[i]) if consec_n == 1 else 0.06
                    p_res_n = 0.08 if consec_n == 1 else 0.0       # reserva solicitada tras un ciclo sin matrícula
                    u = rng.random()
                    siguiente = ESTADO_M if u < p_ret else (ESTADO_R if u < p_ret + p_res_n else ESTADO_N)
            elif estado == ESTADO_R:
                consec_r += 1
                consec_n = 0
                fila["fecha_registro_estado"] = cal["cierre_matricula"] - timedelta(days=int(rng.integers(0, 21)))
                f_cierre_prev = cal["cierre_notas"]
                u = rng.random()
                if consec_r < 2:
                    siguiente = ESTADO_M if u < 0.55 else (ESTADO_R if u < 0.70 else ESTADO_N)
                else:
                    siguiente = ESTADO_M if u < 0.65 else ESTADO_N
            else:  # fallecido
                fila["fecha_registro_estado"] = cal["cierre_matricula"]
                siguiente = ESTADO_F

            # fallecimiento entre ciclos (caso especial del paper: se excluye)
            if estado != ESTADO_F and rng.random() < 0.0006:
                fallecido = True
                fila["fallecimiento_registrado"] = 1
                fila["fecha_fallecimiento"] = cal["cierre_notas"] + timedelta(days=int(rng.integers(1, 25)))
                siguiente = ESTADO_F
            mat_rows.append(fila)

    raw = {
        "estudiantes_admision": pd.DataFrame(est_rows),
        "matricula_ciclos": pd.DataFrame(mat_rows),
        "cursos_notas": pd.DataFrame(cur_rows),
        "pagos_cuotas": pd.DataFrame(pag_rows),
        "lms_semanal": pd.DataFrame(lms_rows),
        "encuesta_socioeconomica": pd.DataFrame(enc_rows),
    }
    return truncar_a_fecha_corte(convertir_fechas(raw))


COLS_FECHA = {
    "estudiantes_admision": ["fecha_admision", "fecha_registro_financiamiento"],
    "matricula_ciclos": ["fecha_registro_estado", "fecha_retiro_total", "fecha_separacion", "fecha_fallecimiento"],
    "cursos_notas": ["fecha_retiro", "fecha_registro_nota", "fecha_cierre_ciclo"],
    "pagos_cuotas": ["fecha_vencimiento", "fecha_pago"],
    "lms_semanal": ["fecha_fin_semana", "fecha_ultima_actividad"],
    "encuesta_socioeconomica": ["fecha_respuesta"],
}


def convertir_fechas(raw: dict) -> dict:
    for k, cols in COLS_FECHA.items():
        for col in cols:
            raw[k][col] = pd.to_datetime(raw[k][col])
    return raw


def truncar_a_fecha_corte(raw: dict) -> dict:
    """Solo existe lo registrado hasta FECHA_CORTE_DATOS (estado del ciclo observado si su cierre de
    matrícula es ≤ corte). Pagos posteriores al corte quedan como no observados."""
    fc = pd.Timestamp(FECHA_CORTE_DATOS)
    est = raw["estudiantes_admision"]
    coh = est.set_index("id_estudiante")["cohorte"]
    m = raw["matricula_ciclos"]
    per = m["id_estudiante"].map(coh) + m["ciclo_regular"] - 1
    m = m[per <= P_OBS].copy()
    for col in ["fecha_retiro_total", "fecha_separacion", "fecha_fallecimiento"]:
        tarde = m[col] > fc
        m.loc[tarde, col] = pd.NaT
    m.loc[m["fecha_separacion"].isna(), "separacion_academica"] = 0
    m.loc[m["fecha_fallecimiento"].isna(), "fallecimiento_registrado"] = 0
    raw["matricula_ciclos"] = m.reset_index(drop=True)
    cu = raw["cursos_notas"]
    per = cu["id_estudiante"].map(coh) + cu["ciclo_regular"] - 1
    cu = cu[per <= P_OBS].copy()
    cu = cu[cu["fecha_cierre_ciclo"] <= fc].copy()
    raw["cursos_notas"] = cu.reset_index(drop=True)
    pg = raw["pagos_cuotas"]
    pg = pg[pg["fecha_vencimiento"] <= fc].copy()
    pg.loc[pg["fecha_pago"] > fc, "fecha_pago"] = pd.NaT
    raw["pagos_cuotas"] = pg.reset_index(drop=True)
    lm = raw["lms_semanal"]
    raw["lms_semanal"] = lm[lm["fecha_fin_semana"] <= fc].reset_index(drop=True)
    en = raw["encuesta_socioeconomica"]
    raw["encuesta_socioeconomica"] = en[en["fecha_respuesta"] <= fc].reset_index(drop=True)
    return raw


# =============================================================================
# 5. CONSTRUCTOR DE SNAPSHOTS: solo registros con fecha ≤ o_c(t), fila a fila
# =============================================================================
def _origenes(est: pd.DataFrame, t: str) -> pd.Series:
    return est.set_index("id_estudiante")["cohorte"].map(lambda c: pd.Timestamp(origen(int(c), t)))


def _filtrar(df: pd.DataFrame, col: str, o: pd.Series) -> pd.DataFrame:
    oo = df["id_estudiante"].map(o)
    return df[df[col].notna() & (df[col] <= oo)]


def poblacion_en_riesgo(raw: dict, t: str) -> pd.Series:
    """R(t) con información fechada ≤ o(t): matriculado y no retirado de todos los cursos en cada
    ciclo 1..j (R anidado). R(T0) = matriculados en el ciclo 1."""
    est = raw["estudiantes_admision"]
    o = _origenes(est, t)
    j = max(1, ORD[t])
    m = _filtrar(raw["matricula_ciclos"], "fecha_registro_estado", o)
    m = m[m["ciclo_regular"] <= j]
    activo = (m["estado_matricula"] == ESTADO_M)
    rt = m["fecha_retiro_total"].notna() & (m["fecha_retiro_total"] <= m["id_estudiante"].map(o))
    if t == "T0":
        rt = rt & False
    m = m.assign(ok=(activo & ~rt).astype(int))
    cnt = m.groupby("id_estudiante")["ok"].agg(["sum", "count"])
    r = (cnt["sum"] == j) & (cnt["count"] == j)
    return r.reindex(o.index, fill_value=False).astype(int)


def construir_snapshot(raw: dict, t: str) -> pd.DataFrame:
    est = raw["estudiantes_admision"].set_index("id_estudiante")
    o = _origenes(raw["estudiantes_admision"], t)
    j = ORD[t]
    out = pd.DataFrame(index=o.index)
    out.index.name = "id_estudiante"
    ok_adm = est["fecha_admision"] <= o
    ok_fin = est["fecha_registro_financiamiento"] <= o

    # --- A estáticas y matrícula ---
    for n in ["puntaje_admision", "promedio_secundaria", "modalidad_admision", "area_programa"]:
        out[n] = est[n].where(ok_adm)
    m = _filtrar(raw["matricula_ciclos"], "fecha_registro_estado", o)
    m = m[m["estado_matricula"] == ESTADO_M]
    ref = max(1, j)
    mref = m[m["ciclo_regular"] == ref].set_index("id_estudiante")
    out["creditos_matriculados_ultimo_ciclo"] = mref["creditos_matriculados"].reindex(out.index)
    out["cursos_matriculados_ultimo_ciclo"] = mref["cursos_matriculados"].reindex(out.index)

    if j >= 1:
        cu = raw["cursos_notas"]
        cal = _filtrar(cu, "fecha_registro_nota", o)                 # cursos calificados con fecha ≤ o(t)
        cal = cal.assign(pond=cal["nota_final"] * cal["creditos"],
                         aprob_cred=np.where(cal["nota_final"] >= NOTA_APROBATORIA, cal["creditos"], 0),
                         desap=(cal["nota_final"] < NOTA_APROBATORIA).astype(int))
        g_all = cal.groupby("id_estudiante")
        prom_acum = g_all["pond"].sum() / g_all["creditos"].sum()
        def prom_ciclo(cc):
            sub = cal[cal["ciclo_regular"] == cc]
            g = sub.groupby("id_estudiante")
            return g["pond"].sum() / g["creditos"].sum()
        p_ult = prom_ciclo(j)
        out["promedio_ultimo_ciclo"] = p_ult.reindex(out.index)
        out["promedio_ponderado_acum"] = prom_acum.reindex(out.index)
        if j >= 2:
            out["variacion_promedio_ultimo_ciclo"] = (p_ult - prom_ciclo(j - 1)).reindex(out.index)
        out["creditos_aprobados_acum"] = g_all["aprob_cred"].sum().reindex(out.index).fillna(0)
        den = _filtrar(cu, "fecha_cierre_ciclo", o).groupby("id_estudiante")["creditos"].sum()
        out["tasa_aprobacion_creditos_acum"] = (out["creditos_aprobados_acum"] / den.reindex(out.index)).where(
            den.reindex(out.index) > 0)
        sub = cal[cal["ciclo_regular"] == j]
        out["cursos_desaprobados_ultimo_ciclo"] = sub.groupby("id_estudiante")["desap"].sum().reindex(out.index).fillna(0)
        out["cursos_desaprobados_acum"] = g_all["desap"].sum().reindex(out.index).fillna(0)
        ret = _filtrar(cu[cu["retirado"] == 1], "fecha_retiro", o)
        out["cursos_retirados_acum"] = ret.groupby("id_estudiante").size().reindex(out.index).fillna(0)
        sub = sub.assign(pin=sub["pct_inasistencia"] * sub["creditos"])
        g = sub.groupby("id_estudiante")
        out["pct_inasistencia_ultimo_ciclo"] = (g["pin"].sum() / g["creditos"].sum()).reindex(out.index)

    # --- F ---
    for n in ["escala_pension", "tipo_financiamiento", "pct_beca"]:
        out[n] = est[n].where(ok_fin)
    if j >= 1:
        pg = raw["pagos_cuotas"]
        venc = _filtrar(pg, "fecha_vencimiento", o).copy()
        oo = venc["id_estudiante"].map(o)
        pagado = venc["fecha_pago"].notna() & (venc["fecha_pago"] <= oo)
        venc = venc.assign(pagado=pagado.astype(int),
                           impago_monto=np.where(pagado, 0.0, venc["monto"]),
                           impago=(~pagado).astype(int),
                           atraso_pag=np.where(pagado, (venc["fecha_pago"] - venc["fecha_vencimiento"]).dt.days.clip(lower=0), np.nan),
                           antig=np.where(~pagado, (oo - venc["fecha_vencimiento"]).dt.days, 0),
                           tarde=(pagado & ((venc["fecha_pago"] - venc["fecha_vencimiento"]).dt.days > 7)).astype(int))
        g = venc.groupby("id_estudiante")
        out["saldo_pendiente_soles"] = g["impago_monto"].sum().reindex(out.index).fillna(0).round(2)
        out["cuotas_vencidas_impagas"] = g["impago"].sum().reindex(out.index).fillna(0)
        tot = g["monto"].sum().reindex(out.index)
        out["pct_obligaciones_vencidas_impagas"] = (out["saldo_pendiente_soles"] / tot).where(tot > 0, 0.0).round(4)
        out["dias_atraso_promedio_pagos"] = g["atraso_pag"].mean().reindex(out.index).round(2)
        out["max_dias_atraso_vigente"] = g["antig"].max().reindex(out.index).fillna(0)
        out["cuotas_pagadas_con_atraso_acum"] = g["tarde"].sum().reindex(out.index).fillna(0)

    # --- S ---
    for n in ["edad_ingreso", "tipo_colegio", "region_procedencia"]:
        out[n] = est[n].where(ok_adm)
    if j >= 1:
        en = _filtrar(raw["encuesta_socioeconomica"], "fecha_respuesta", o).set_index("id_estudiante")
        out["encuesta_respondida"] = out.index.isin(en.index).astype(int)
        for n in ["ingreso_hogar_rango", "trabaja", "horas_trabajo_semana", "apoyo_economico_familiar",
                  "primera_generacion_universitaria"]:
            out[n] = en[n].reindex(out.index)

    # --- B ---
    if j >= 1:
        lm = _filtrar(raw["lms_semanal"], "fecha_fin_semana", o)
        cj = lm[lm["ciclo_regular"] == j]
        g = cj.groupby("id_estudiante")
        out["accesos_ultimo_ciclo"] = g["accesos"].sum().reindex(out.index).fillna(0)
        out["dias_activos_ultimo_ciclo"] = g["dias_activos"].sum().reindex(out.index).fillna(0)
        out["actividades_entregadas_ultimo_ciclo"] = g["actividades_entregadas"].sum().reindex(out.index).fillna(0)
        asig = g["actividades_asignadas"].sum().reindex(out.index)
        out["pct_actividades_entregadas_ultimo_ciclo"] = (out["actividades_entregadas_ultimo_ciclo"] / asig).where(asig > 0).round(4)
        a2 = cj[cj["semana"] >= 9].groupby("id_estudiante")["accesos"].sum().reindex(out.index).fillna(0)
        a1 = cj[cj["semana"] <= 8].groupby("id_estudiante")["accesos"].sum().reindex(out.index).fillna(0)
        out["tendencia_accesos_ultimo_ciclo"] = ((a2 + 1) / (a1 + 1)).round(4)
        ult = _filtrar(lm, "fecha_ultima_actividad", o).groupby("id_estudiante")["fecha_ultima_actividad"].max()
        ini1 = est["cohorte"].map(lambda c: pd.Timestamp(calendario(int(c))["inicio_clases"]))
        ref_f = ult.reindex(out.index).fillna(ini1)
        out["dias_desde_ultima_actividad"] = (o - ref_f).dt.days
        out["accesos_acum"] = lm.groupby("id_estudiante")["accesos"].sum().reindex(out.index).fillna(0)

    # orden y nombres según el diccionario
    cols = [v["nombre"] for v in variables_en_ventana(t)]
    out = out[cols]
    out.columns = [col_wide(t, VAR_INDEX[n]) for n in cols]
    return out


def fecha_maxima_usada(raw: dict, t: str) -> pd.Series:
    """Fecha máxima de los registros que el constructor puede leer para cada estudiante en t."""
    est = raw["estudiantes_admision"]
    o = _origenes(est, t)
    fechas = [est.set_index("id_estudiante")["fecha_admision"], est.set_index("id_estudiante")["fecha_registro_financiamiento"]]
    for tab, col in [("matricula_ciclos", "fecha_registro_estado"), ("cursos_notas", "fecha_registro_nota"),
                     ("cursos_notas", "fecha_retiro"), ("pagos_cuotas", "fecha_vencimiento"),
                     ("lms_semanal", "fecha_fin_semana"), ("lms_semanal", "fecha_ultima_actividad"),
                     ("encuesta_socioeconomica", "fecha_respuesta")]:
        f = _filtrar(raw[tab], col, o)
        fechas.append(f.groupby("id_estudiante")[col].max())
    pg = raw["pagos_cuotas"]
    pg_ok = pg[pg["fecha_pago"].notna() & (pg["fecha_pago"] <= pg["id_estudiante"].map(o))]
    fechas.append(pg_ok.groupby("id_estudiante")["fecha_pago"].max())
    return pd.concat(fechas, axis=1).max(axis=1).reindex(o.index)


# =============================================================================
# 6. ETIQUETA (definición operacional del paper) Y TRAYECTORIAS
# =============================================================================
def determinar_etiqueta(codigos: list, h: int = H):
    """codigos: estados observados de los ciclos 1..L ('M','N','R','F').
    e_i = primer ciclo j ≥ 2 sin matrícula cuyo siguiente ciclo regular NO reservado tampoco tiene matrícula.
    Los ciclos con reserva aprobada se omiten al evaluar la consecutividad.
    Devuelve (estado_etiqueta, Y, e_i si e_i ≤ H)."""
    L = len(codigos)
    for j in range(2, h + 1):
        if j > L:
            return "desconocida", np.nan, np.nan
        s = codigos[j - 1]
        if s in ("M", "R"):
            continue
        if s == "N":
            k = j + 1
            while k <= L and codigos[k - 1] == "R":
                k += 1
            if k > L:
                return "desconocida", np.nan, np.nan
            if codigos[k - 1] == "N":
                return "conocida", 1, j
            continue
    return "conocida", 0, np.nan


def inicio_observado(codigos: list):
    """Primer e_i observable en todo el seguimiento (para análisis de sensibilidad con otro H)."""
    L = len(codigos)
    for j in range(2, L + 1):
        if codigos[j - 1] != "N":
            continue
        k = j + 1
        while k <= L and codigos[k - 1] == "R":
            k += 1
        if k > L:
            return np.nan
        if codigos[k - 1] == "N":
            return j
    return np.nan


def etiqueta_alternativa(codigos: list, h: int = H):
    """Implementación independiente (cadena sin reservas) usada solo para validar."""
    pares = [(idx + 1, s) for idx, s in enumerate(codigos) if s != "R"]
    cadena = "".join(s for _, s in pares)
    pos = cadena.find("NN")
    while pos != -1 and pares[pos][0] < 2:
        pos = cadena.find("NN", pos + 1)
    if pos != -1 and pares[pos][0] <= h:
        return "conocida", 1, pares[pos][0]
    L = len(codigos)
    if L < h:
        return "desconocida", np.nan, np.nan
    for idx, (ciclo, s) in enumerate(pares):
        if 2 <= ciclo <= h and s == "N" and idx == len(pares) - 1:
            return "desconocida", np.nan, np.nan
    return "conocida", 0, np.nan


def construir_resultados(raw: dict) -> pd.DataFrame:
    est = raw["estudiantes_admision"].set_index("id_estudiante")
    m = raw["matricula_ciclos"].sort_values(["id_estudiante", "ciclo_regular"])
    filas = []
    for sid, g in m.groupby("id_estudiante", sort=False):
        cod = [COD[s] for s in g["estado_matricula"]]
        fall = g[g["fallecimiento_registrado"] == 1]
        ciclo_f = int(fall["ciclo_regular"].min()) + 1 if len(fall) else None   # primer ciclo con baja
        estado, y, e = determinar_etiqueta(cod)
        if ciclo_f is not None and ciclo_f <= H + 1:
            estado, y, e = "excluida_fallecimiento", np.nan, np.nan
        e_obs = inicio_observado([s for s in cod if s != "F"])
        sep = int(g["separacion_academica"].max())
        ret = np.nan
        if y == 1:
            ret = int(any(s == "M" for s in cod[int(e):]))
        filas.append(dict(id_estudiante=sid, OUT_estado_etiqueta=estado, OUT_y_desercion=y,
                          OUT_ciclo_inicio_desercion=e, OUT_ciclo_inicio_observado=e_obs,
                          OUT_separacion_academica=sep if y == 1 else (0 if estado == "conocida" else np.nan),
                          OUT_retorno_posterior_al_evento=ret,
                          OUT_fallecimiento_registrado=int(ciclo_f is not None),
                          trayectoria_codificada="".join(cod), ciclos_observados=len(cod)))
    return pd.DataFrame(filas).set_index("id_estudiante").reindex(est.index)


def particion_cohortes(est: pd.DataFrame) -> pd.DataFrame:
    filas = []
    etiquetadas = [c for c in range(1, N_COHORTES + 1) if ultimo_ciclo_observado(c) >= H + 1]
    CL = len(etiquetadas)
    CD = CL - N_COHORTES_PRUEBA
    F = CD - C0
    for c in range(1, N_COHORTES + 1):
        cal = calendario(c)
        rol = ("prueba" if c in etiquetadas[CD:] else "desarrollo") if c in etiquetadas else "sin_seguimiento_completo"
        fila = dict(cohorte=c, periodo_ingreso=cal["periodo"], fecha_origen_T0=origen(c, "T0"),
                    fecha_origen_T1=origen(c, "T1"), fecha_origen_T2=origen(c, "T2"), fecha_origen_T3=origen(c, "T3"),
                    n_estudiantes=int((est["cohorte"] == c).sum()), ultimo_ciclo_observado=ultimo_ciclo_observado(c),
                    cohorte_con_seguimiento_completo=int(c in etiquetadas), rol_particion=rol)
        for f in range(1, F + 1):
            entrenamiento = list(range(1, C0 + f))
            interna = C0 + f - 1
            if c == C0 + f:
                r = "validacion"
            elif c == interna:
                r = "interna_ajuste_hiperparametros_y_calibracion"
            elif c in entrenamiento:
                r = "ajuste"
            else:
                r = "no_usada"
            fila[f"fold_{f}"] = r
        filas.append(fila)
    return pd.DataFrame(filas)


def construir_longitudinal(raw: dict, res: pd.DataFrame) -> pd.DataFrame:
    est = raw["estudiantes_admision"].set_index("id_estudiante")
    m = raw["matricula_ciclos"].copy()
    m["cohorte"] = m["id_estudiante"].map(est["cohorte"])
    m["periodo_ingreso"] = m["id_estudiante"].map(est["periodo_ingreso"])
    m["fecha_cierre_matricula"] = [pd.Timestamp(calendario(int(c) + int(k) - 1)["cierre_matricula"]) for c, k in zip(m["cohorte"], m["ciclo_regular"])]
    m["fecha_cierre_notas"] = [pd.Timestamp(calendario(int(c) + int(k) - 1)["cierre_notas"]) for c, k in zip(m["cohorte"], m["ciclo_regular"])]
    m["ventana_que_cierra"] = m["ciclo_regular"].map({1: "T1", 2: "T2", 3: "T3"}).fillna("ninguna")
    m["activo_en_ciclo"] = ((m["estado_matricula"] == ESTADO_M) & (m["retiro_total"] == 0)).astype(int)
    # agregados del ciclo k a su propio cierre de notas (registros fechados ≤ cierre de notas del ciclo)
    cu = raw["cursos_notas"]
    cal = cu[cu["nota_final"].notna()].copy()
    cal["pond"] = cal["nota_final"] * cal["creditos"]
    cal["desap"] = (cal["nota_final"] < NOTA_APROBATORIA).astype(int)
    cal["aprob_cred"] = np.where(cal["nota_final"] >= NOTA_APROBATORIA, cal["creditos"], 0)
    cal["pin"] = cal["pct_inasistencia"] * cal["creditos"]
    g = cal.groupby(["id_estudiante", "ciclo_regular"])
    agg = pd.DataFrame({
        "promedio_ciclo": (g["pond"].sum() / g["creditos"].sum()).round(3),
        "creditos_aprobados_ciclo": g["aprob_cred"].sum(),
        "cursos_desaprobados_ciclo": g["desap"].sum(),
        "pct_inasistencia_ciclo": (g["pin"].sum() / g["creditos"].sum()).round(2),
    })
    agg["cursos_retirados_ciclo"] = cu[cu["retirado"] == 1].groupby(["id_estudiante", "ciclo_regular"]).size()
    pg = raw["pagos_cuotas"].copy()
    pg["cierre"] = [pd.Timestamp(calendario(int(est.at[s, "cohorte"]) + int(k) - 1)["cierre_notas"]) for s, k in zip(pg["id_estudiante"], pg["ciclo_regular"])]
    pg["impaga_al_cierre"] = (pg["fecha_pago"].isna() | (pg["fecha_pago"] > pg["cierre"])).astype(int)
    pg["monto_impago_al_cierre"] = pg["monto"] * pg["impaga_al_cierre"]
    gp = pg.groupby(["id_estudiante", "ciclo_regular"])
    agg["monto_facturado_ciclo"] = gp["monto"].sum().round(2)
    agg["cuotas_impagas_al_cierre_ciclo"] = gp["impaga_al_cierre"].sum()
    agg["monto_impago_al_cierre_ciclo"] = gp["monto_impago_al_cierre"].sum().round(2)
    lm = raw["lms_semanal"].groupby(["id_estudiante", "ciclo_regular"])
    agg["accesos_lms_ciclo"] = lm["accesos"].sum()
    agg["dias_activos_lms_ciclo"] = lm["dias_activos"].sum()
    agg["pct_actividades_entregadas_ciclo"] = (lm["actividades_entregadas"].sum() / lm["actividades_asignadas"].sum()).round(4)
    m = m.merge(agg, left_on=["id_estudiante", "ciclo_regular"], right_index=True, how="left")
    det = m["ciclo_regular"] <= CICLOS_DETALLADOS
    for col in ["cursos_retirados_ciclo", "cuotas_impagas_al_cierre_ciclo", "monto_impago_al_cierre_ciclo"]:
        m.loc[det & (m["estado_matricula"] == ESTADO_M), col] = m.loc[det & (m["estado_matricula"] == ESTADO_M), col].fillna(0)
    m["fecha_disponibilidad_agregados"] = m["fecha_cierre_notas"].where(det & (m["estado_matricula"] == ESTADO_M))
    m["uso_permitido_fila"] = np.where(m["ciclo_regular"] <= 3,
                                       "agregados utilizables solo desde la ventana que cierra este ciclo; estado de matrícula de ciclos posteriores = resultado",
                                       "solo construcción de Y (posterior a T3; nunca predictor)")
    orden = ["id_estudiante", "cohorte", "periodo_ingreso", "ciclo_regular", "periodo_academico",
             "fecha_cierre_matricula", "fecha_cierre_notas", "ventana_que_cierra", "estado_matricula",
             "fecha_registro_estado", "activo_en_ciclo", "retiro_total", "fecha_retiro_total", "cambio_programa",
             "separacion_academica", "fecha_separacion", "fallecimiento_registrado", "fecha_fallecimiento",
             "creditos_matriculados", "cursos_matriculados", "cursos_retirados_ciclo", "promedio_ciclo",
             "creditos_aprobados_ciclo", "cursos_desaprobados_ciclo", "pct_inasistencia_ciclo",
             "monto_facturado_ciclo", "cuotas_impagas_al_cierre_ciclo", "monto_impago_al_cierre_ciclo",
             "accesos_lms_ciclo", "dias_activos_lms_ciclo", "pct_actividades_entregadas_ciclo",
             "fecha_disponibilidad_agregados", "uso_permitido_fila"]
    return m[orden].sort_values(["id_estudiante", "ciclo_regular"]).reset_index(drop=True)


def construir_todo(semilla: int) -> dict:
    raw = simular(semilla)
    est = raw["estudiantes_admision"]
    res = construir_resultados(raw)
    part = particion_cohortes(est)
    wide = est[["id_estudiante", "cohorte", "periodo_ingreso"]].set_index("id_estudiante").copy()
    wide["rol_particion"] = wide["cohorte"].map(part.set_index("cohorte")["rol_particion"])
    wide["cohorte_con_seguimiento_completo"] = wide["cohorte"].map(part.set_index("cohorte")["cohorte_con_seguimiento_completo"])
    for t in VENTANAS:
        wide[f"fecha_origen_{t}"] = wide["cohorte"].map(lambda c, t=t: pd.Timestamp(origen(int(c), t)))
    for t in VENTANAS:
        wide[f"en_riesgo_{t}"] = poblacion_en_riesgo(raw, t)
    snaps = []
    for t in VENTANAS:
        snap = construir_snapshot(raw, t)
        snaps.append(snap.where(wide[f"en_riesgo_{t}"].reindex(snap.index) == 1))
    wide = pd.concat([wide] + snaps, axis=1).copy()
    out_cols = ["OUT_estado_etiqueta", "OUT_y_desercion", "OUT_ciclo_inicio_desercion", "OUT_ciclo_inicio_observado",
                "OUT_separacion_academica", "OUT_retorno_posterior_al_evento", "OUT_fallecimiento_registrado"]
    wide = wide.join(res[out_cols])
    wide = wide.reset_index().sort_values("id_estudiante").reset_index(drop=True)
    long = construir_longitudinal(raw, res)
    return dict(raw=raw, wide=wide, long=long, part=part, res=res)


# =============================================================================
# 7. EXPORTACIÓN
# =============================================================================
def _fmt(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df


def csv_bytes(df: pd.DataFrame) -> bytes:
    return _fmt(df).to_csv(index=False, lineterminator="\n").encode("utf-8")


def archivos_csv(res: dict) -> dict:
    d = {
        "dataset_sintetico_longitudinal.csv": res["long"],
        "dataset_sintetico_wide.csv": res["wide"],
        "particion_temporal_cohortes.csv": res["part"],
        "ids_cohortes_prueba_bloqueadas.csv": res["wide"].loc[res["wide"]["rol_particion"] == "prueba", ["id_estudiante", "cohorte"]],
    }
    for k, v in res["raw"].items():
        d[f"fuentes_crudas/{k}.csv"] = v.sort_values(list(v.columns[:2])).reset_index(drop=True)
    return d


def huellas(res: dict) -> dict:
    return {k: hashlib.sha256(csv_bytes(v)).hexdigest() for k, v in archivos_csv(res).items()}


def escribir_xlsx(ruta: str, hojas: list):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    wb.remove(wb.active)
    negro = Font(name="Arial", size=9, color="000000")
    negrita = Font(name="Arial", size=9, bold=True, color="000000")
    fondo = PatternFill("solid", fgColor="E7E6E6")
    borde = Border(bottom=Side(style="thin", color="999999"))
    ws0 = wb.create_sheet("leeme")
    ws0.cell(row=1, column=1, value="DATOS 100 % SINTÉTICOS — no atribuibles a ninguna institución. Generados por generar_dataset_sintetico.py.").font = negrita
    ws0.cell(row=3, column=1, value="hoja").font = negrita
    ws0.cell(row=3, column=2, value="contenido").font = negrita
    for q, (nombre, _df, nota) in enumerate(hojas, start=4):
        ws0.cell(row=q, column=1, value=nombre[:31]).font = negro
        ws0.cell(row=q, column=2, value=nota or "").font = negro
    ws0.column_dimensions["A"].width = 28
    ws0.column_dimensions["B"].width = 120
    for nombre, df, nota in hojas:
        ws = wb.create_sheet(nombre[:31])
        fila0 = 1
        df = _fmt(df)
        for jcol, col in enumerate(df.columns, start=1):
            cell = ws.cell(row=fila0, column=jcol, value=str(col))
            cell.font, cell.fill, cell.border = negrita, fondo, borde
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        for irow, fila in enumerate(df.itertuples(index=False), start=fila0 + 1):
            for jcol, val in enumerate(fila, start=1):
                if isinstance(val, float) and np.isnan(val):
                    val = None
                elif isinstance(val, (np.integer,)):
                    val = int(val)
                elif isinstance(val, (np.floating,)):
                    val = float(val)
                elif isinstance(val, (np.bool_,)):
                    val = bool(val)
                elif val is pd.NA or val is pd.NaT:
                    val = None
                cell = ws.cell(row=irow, column=jcol, value=val)
                cell.font = negro
                cell.alignment = Alignment(wrap_text=isinstance(val, str) and len(val) > 40, vertical="top")
        for jcol, col in enumerate(df.columns, start=1):
            largo = max([len(str(col))] + [len(str(x)) for x in df[col].head(200).tolist()])
            ws.column_dimensions[get_column_letter(jcol)].width = min(60, max(10, largo + 2))
        ws.freeze_panes = ws.cell(row=fila0 + 1, column=2)
    wb.save(ruta)


def tabla_diccionario() -> pd.DataFrame:
    filas = []
    for v in VARS:
        cols = [col_wide(t, v) for t in VENTANAS if ORD[v["alfa"]] <= ORD[t]]
        rango = (", ".join(v["cats"]) if v["cats"] else f"[{v['rmin']}, {v['rmax']}]")
        filas.append({
            "nombre_tecnico": v["nombre"], "descripcion": v["desc"], "bloque": f"{v['bloque']} — {NOMBRE_BLOQUE[v['bloque']]}",
            "tipo_dato": v["tipo"], "unidad_o_categorias": v["unidad"], "rango_o_valores_validos": rango,
            "primera_ventana_admisible_alfa": v["alfa"], "comportamiento_temporal": v["tv"],
            "fuente_sintetica": v["fuente"], "regla_generacion": v["gen"], "regla_disponibilidad": v["disp"],
            "riesgo_fuga_informacion": v["fuga"], "uso_permitido_y_restricciones": v["uso"],
            "verificacion_institucional": v["verif"], "columnas_en_wide": "; ".join(cols)})
    return pd.DataFrame(filas)


def tabla_columnas_admin() -> pd.DataFrame:
    filas = [
        ("id_estudiante", "Identificador sintético aleatorio SYN-XXXXXXXX (no codifica cohorte ni historia).", "texto", "Clave. PROHIBIDO como predictor."),
        ("cohorte", "Índice cronológico de cohorte (1 = más antigua).", "entero 1–12", "Solo partición temporal. PROHIBIDO como predictor."),
        ("periodo_ingreso", "Periodo sintético de ingreso (AAAA-S).", "texto", "Solo partición. PROHIBIDO como predictor."),
        ("rol_particion", "desarrollo / prueba / sin_seguimiento_completo.", "categoría", "Solo partición. PROHIBIDO como predictor."),
        ("cohorte_con_seguimiento_completo", "1 si la cohorte tiene observado el ciclo H+1 a la fecha de corte.", "0/1", "Derivado del seguimiento. PROHIBIDO como predictor."),
        ("fecha_origen_T0..T3", "o_c(t) de la cohorte: cierre de matrícula del ciclo 1 (T0) y cierre de notas del ciclo j (Tj).", "fecha", "Solo auditoría temporal. PROHIBIDO como predictor (equivale a la cohorte)."),
        ("en_riesgo_T0..T3", "Pertenencia a R(t) calculada con registros fechados ≤ o(t).", "0/1", "FILTRO DE POBLACIÓN. PROHIBIDO como predictor (se relaciona con el resultado)."),
        ("OUT_estado_etiqueta", "conocida / desconocida / excluida_fallecimiento.", "categoría", "RESULTADO. Nunca predictor."),
        ("OUT_y_desercion", "Y = 1 si e_i ≤ H = 4; 0 si los registros deciden que e_i > H; NaN si no se puede decidir.", "0/1/NaN", "ETIQUETA. Nunca predictor. Una sola columna (no se replica por ventana)."),
        ("OUT_ciclo_inicio_desercion", "e_i cuando e_i ≤ H.", "entero 2–4", "RESULTADO. Nunca predictor."),
        ("OUT_ciclo_inicio_observado", "Primer e_i observable en todo el seguimiento (incluye e_i > H; para sensibilidad con H mayor).", "entero", "RESULTADO. Nunca predictor."),
        ("OUT_separacion_academica", "1 si el evento coincide con una separación académica registrada (sensibilidad i).", "0/1/NaN", "RESULTADO. Nunca predictor."),
        ("OUT_retorno_posterior_al_evento", "1 si tras el evento hay una matrícula posterior observada (Y no cambia).", "0/1/NaN", "RESULTADO. Nunca predictor."),
        ("OUT_fallecimiento_registrado", "1 si hay baja por fallecimiento registrada en el seguimiento observado.", "0/1", "RESULTADO/EXCLUSIÓN. Nunca predictor."),
    ]
    return pd.DataFrame(filas, columns=["columna", "descripcion", "tipo", "uso"])


def tabla_longitudinal() -> pd.DataFrame:
    filas = [
        ("id_estudiante, cohorte, periodo_ingreso", "Identificación del episodio (uno por estudiante)."),
        ("ciclo_regular", "Ciclo regular contado desde el ingreso (1..8, truncado a la fecha de corte; veranos ignorados)."),
        ("periodo_academico", "Periodo calendario sintético del ciclo."),
        ("fecha_cierre_matricula, fecha_cierre_notas", "Calendario del ciclo; el cierre de notas del ciclo j es o(Tj)."),
        ("ventana_que_cierra", "T1/T2/T3 para los ciclos 1–3; 'ninguna' para ciclos ≥ 4."),
        ("estado_matricula", "matriculado / no_matriculado / reserva_aprobada / baja_por_fallecimiento."),
        ("fecha_registro_estado", "Fecha del registro de matrícula, reserva o constatación de no matrícula (cierre de matrícula)."),
        ("activo_en_ciclo", "Matriculado y sin retiro total (definición de 'activo' del paper)."),
        ("retiro_total, fecha_retiro_total", "Retiro de todos los cursos del ciclo (sigue contando como matriculado para e_i; ver supuestos)."),
        ("cambio_programa", "Cambio de programa registrado en la matrícula (no es evento; el episodio continúa)."),
        ("separacion_academica, fecha_separacion", "Registro administrativo posterior al cierre de notas (evento; sensibilidad i)."),
        ("fallecimiento_registrado, fecha_fallecimiento", "Caso especial: excluido de la etiqueta."),
        ("creditos_matriculados … pct_actividades_entregadas_ciclo", "Agregados del ciclo calculados con registros fechados ≤ cierre de notas de ese ciclo (solo ciclos 1–4 matriculados)."),
        ("fecha_disponibilidad_agregados", "Fecha desde la que los agregados del ciclo existen (cierre de notas)."),
        ("uso_permitido_fila", "Restricción de uso de la fila."),
    ]
    return pd.DataFrame(filas, columns=["columnas", "descripcion"])


def tabla_fuentes() -> pd.DataFrame:
    filas = [
        ("estudiantes_admision.csv", "Un registro por episodio: admisión, financiamiento asignado y datos socioeconómicos de admisión.", "fecha_admision, fecha_registro_financiamiento"),
        ("matricula_ciclos.csv", "Estado por ciclo regular, retiro total, cambio de programa, separación y fallecimiento.", "fecha_registro_estado, fecha_retiro_total, fecha_separacion, fecha_fallecimiento"),
        ("cursos_notas.csv", "Cursos de los ciclos 1–4: créditos, retiro, nota final e inasistencia.", "fecha_retiro, fecha_registro_nota, fecha_cierre_ciclo"),
        ("pagos_cuotas.csv", "Derecho de matrícula y cuotas de pensión de los ciclos 1–4 con vencimiento y pago.", "fecha_vencimiento, fecha_pago (NaT = sin pago observado a la fecha de corte)"),
        ("lms_semanal.csv", "Actividad semanal en la plataforma virtual (ciclos 1–4).", "fecha_fin_semana, fecha_ultima_actividad"),
        ("encuesta_socioeconomica.csv", "Encuesta del ciclo 1 (solo quienes respondieron).", "fecha_respuesta"),
    ]
    return pd.DataFrame(filas, columns=["archivo", "contenido", "campos_de_fecha_de_registro"])


def tabla_matriz() -> pd.DataFrame:
    filas = []
    for v in VARS:
        fila = {"variable": v["nombre"], "bloque": v["bloque"], "primera_ventana_admisible": v["alfa"],
                "regla_disponibilidad": v["disp"]}
        for t in VENTANAS:
            if ORD[v["alfa"]] <= ORD[t]:
                fila[t] = "DISPONIBLE"
                if v["tv"] == "valor a o(t)":
                    fila[f"justificacion_{t}"] = f"Valor calculado con registros fechados ≤ o({t})."
                else:
                    fila[f"justificacion_{t}"] = f"Registro fechado antes de o({v['alfa']}) ≤ o({t}); valor sin cambios."
            else:
                fila[t] = "NO DISPONIBLE"
                fila[f"justificacion_{t}"] = f"Primer registro posterior a o({t}); α = {v['alfa']}."
            fila[f"columna_{t}"] = col_wide(t, v) if ORD[v["alfa"]] <= ORD[t] else ""
        filas.append(fila)
    cols = ["variable", "bloque", "primera_ventana_admisible", "T0", "T1", "T2", "T3",
            "justificacion_T0", "justificacion_T1", "justificacion_T2", "justificacion_T3", "regla_disponibilidad",
            "columna_T0", "columna_T1", "columna_T2", "columna_T3"]
    return pd.DataFrame(filas)[cols]


def tabla_conjuntos() -> pd.DataFrame:
    filas = []
    for t in VENTANAS:
        adm = conjuntos_admisibles(t)
        for s in CONJUNTOS:
            if s in adm:
                n = len(columnas_conjunto(t, s))
                filas.append(dict(ventana=t, conjunto=s, estado="aplicable (escenario)", n_columnas=n,
                                  es_s_t_mas=int(s == conjunto_mas_completo(t)), motivo=""))
            else:
                falt = [b for b in s.split("+") if b not in bloques_admisibles(t)]
                filas.append(dict(ventana=t, conjunto=s, estado="no aplicable", n_columnas=0, es_s_t_mas=0,
                                  motivo=f"Bloque(s) {', '.join(falt)} sin variables con α ≤ {t}"))
    return pd.DataFrame(filas)


def tabla_ventanas() -> pd.DataFrame:
    return pd.DataFrame([
        ("T0", "Cierre de la matrícula del ciclo 1", "Admisión, financiamiento asignado y matrícula del ciclo 1; sin notas, pagos de pensión, encuesta ni plataforma", "Matriculados en el ciclo 1", "2, 3, 4"),
        ("T1", "Cierre de notas del ciclo 1", "T0 + notas, retiros, inasistencia, pagos, encuesta y plataforma registrados hasta o(T1)", "Activos en el ciclo 1", "2, 3, 4"),
        ("T2", "Cierre de notas del ciclo 2", "T1 + registros del ciclo 2", "Activos en los ciclos 1–2", "3, 4"),
        ("T3", "Cierre de notas del ciclo 3", "T2 + registros del ciclo 3", "Activos en los ciclos 1–3", "4"),
    ], columns=["ventana", "origen_o_t", "informacion_admisible", "poblacion_R_t", "inicios_e_i_aun_posibles_con_H4"])


# =============================================================================
# 8. VALIDACIONES AUTOMÁTICAS
# =============================================================================
def auc(y, s):
    y = np.asarray(y, dtype=float)
    s = np.asarray(s, dtype=float)
    ok = ~np.isnan(y) & ~np.isnan(s)
    y, s = y[ok], s[ok]
    n1, n0 = (y == 1).sum(), (y == 0).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    r = pd.Series(s).rank(method="average").to_numpy()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def _iguales(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    a = a.sort_index()
    b = b.sort_index()[a.columns]
    try:
        pd.testing.assert_frame_equal(a, b, check_dtype=False, check_exact=False, rtol=1e-9)
        return True
    except AssertionError:
        return False


def perturbar_futuro(raw: dict, t: str, rng) -> dict:
    """Altera TODO registro con fecha > o_c(t): si el snapshot de t cambia, hay fuga."""
    est = raw["estudiantes_admision"]
    o = _origenes(est, t)
    p = {k: v.copy() for k, v in raw.items()}
    m = p["matricula_ciclos"]
    fut = m["fecha_registro_estado"] > m["id_estudiante"].map(o)
    m.loc[fut, "estado_matricula"] = rng.choice([ESTADO_M, ESTADO_N, ESTADO_R], fut.sum())
    m.loc[fut, "creditos_matriculados"] = rng.integers(1, 40, fut.sum())
    rtf = m["fecha_retiro_total"] > m["id_estudiante"].map(o)
    m.loc[rtf, "retiro_total"] = 1 - m.loc[rtf, "retiro_total"]
    cu = p["cursos_notas"]
    fut = cu["fecha_cierre_ciclo"] > cu["id_estudiante"].map(o)
    cu.loc[fut, "nota_final"] = rng.uniform(0, 20, fut.sum()).round(1)
    cu.loc[fut, "pct_inasistencia"] = rng.uniform(0, 70, fut.sum()).round(1)
    cu.loc[fut, "creditos"] = rng.integers(1, 9, fut.sum())
    pg = p["pagos_cuotas"]
    oo = pg["id_estudiante"].map(o)
    fut = pg["fecha_vencimiento"] > oo
    pg.loc[fut, "monto"] = pg.loc[fut, "monto"] * 7 + 1
    fp = pg["fecha_pago"] > oo
    pg.loc[fp, "fecha_pago"] = pg.loc[fp, "fecha_pago"] + pd.to_timedelta(rng.integers(1, 300, fp.sum()), unit="D")
    lm = p["lms_semanal"]
    fut = lm["fecha_fin_semana"] > lm["id_estudiante"].map(o)
    lm.loc[fut, "accesos"] = rng.integers(0, 500, fut.sum())
    lm.loc[fut, "actividades_entregadas"] = rng.integers(0, 3, fut.sum())
    en = p["encuesta_socioeconomica"]
    fut = en["fecha_respuesta"] > en["id_estudiante"].map(o)
    en.loc[fut, "horas_trabajo_semana"] = rng.integers(0, 60, fut.sum())
    en.loc[fut, "trabaja"] = 1 - en.loc[fut, "trabaja"]
    return p


def validar(res: dict, semilla: int) -> tuple:
    raw, wide, long, part = res["raw"], res["wide"], res["long"], res["part"]
    ctr = []

    def reg(cod, nombre, ok, detalle, categoria="obligatoria"):
        ctr.append(dict(codigo=cod, control=nombre, categoria=categoria,
                        resultado=("SUPERADO" if ok else "FALLIDO") if ok is not None else "INFORMATIVO",
                        detalle=detalle))

    rng = np.random.default_rng(semilla + 999)
    W = wide.set_index("id_estudiante")
    pred_cols = [c for c in wide.columns if c[:3] in ("T0_", "T1_", "T2_", "T3_")]

    # V01 unicidad
    est = raw["estudiantes_admision"]
    ok = (wide["id_estudiante"].is_unique and est["id_estudiante"].is_unique
          and long.groupby("id_estudiante")["cohorte"].nunique().max() == 1
          and not long.duplicated(["id_estudiante", "ciclo_regular"]).any()
          and set(long["id_estudiante"]) == set(wide["id_estudiante"]))
    reg("V01", "Unicidad del identificador y una sola cohorte por estudiante", ok,
        f"{wide['id_estudiante'].nunique()} ids únicos en {len(wide)} filas wide; "
        f"máx. cohortes por id en longitudinal = {long.groupby('id_estudiante')['cohorte'].nunique().max()}; "
        f"duplicados (id, ciclo) = {int(long.duplicated(['id_estudiante', 'ciclo_regular']).sum())}.")

    # V02 coherencia matrícula–ciclos–evento
    errores = 0
    g = long.groupby("id_estudiante")
    consecutivos = g["ciclo_regular"].apply(lambda s: list(s) == list(range(1, len(s) + 1))).all()
    per_ok = all(long["periodo_academico"] == [periodo_label(int(c) + int(k) - 1) for c, k in zip(long["cohorte"], long["ciclo_regular"])])
    c1 = (long.loc[long["ciclo_regular"] == 1, "estado_matricula"] == ESTADO_M).all()
    rt_ok = (long.loc[long["retiro_total"] == 1, "estado_matricula"] == ESTADO_M).all()
    agg_ok = long.loc[long["estado_matricula"] != ESTADO_M, ["creditos_matriculados", "promedio_ciclo", "accesos_lms_ciclo"]].isna().all().all()
    for sid, tray in res["res"]["trayectoria_codificada"].items():
        a = determinar_etiqueta(list(tray))
        b = etiqueta_alternativa(list(tray))
        if res["res"].at[sid, "OUT_estado_etiqueta"] == "excluida_fallecimiento":
            continue
        if not (a[0] == b[0] and (a[1] == b[1] or (np.isnan(a[1]) and np.isnan(b[1])))
                and (a[2] == b[2] or (np.isnan(a[2]) and np.isnan(b[2])))):
            errores += 1
    y1 = W[W["OUT_y_desercion"] == 1]
    mal_ev = 0
    for sid, e in y1["OUT_ciclo_inicio_desercion"].items():
        tray = res["res"].at[sid, "trayectoria_codificada"]
        e = int(e)
        k = e + 1
        while tray[k - 1] == "R":
            k += 1
        if not (tray[e - 1] == "N" and tray[k - 1] == "N"):
            mal_ev += 1
    ok = consecutivos and per_ok and c1 and rt_ok and agg_ok and errores == 0 and mal_ev == 0
    reg("V02", "Coherencia entre matrícula, ciclos y evento sintético", ok,
        f"Ciclos consecutivos desde 1: {consecutivos}; periodo = cohorte + ciclo − 1: {per_ok}; ciclo 1 siempre matriculado: {c1}; "
        f"retiro total solo en matriculados: {rt_ok}; agregados vacíos si no matriculado: {agg_ok}; "
        f"discrepancias entre dos implementaciones independientes de Y: {errores}; eventos sin dos ciclos no reservados sin matrícula: {mal_ev}.")

    # V03 horizonte
    e = W["OUT_ciclo_inicio_desercion"].dropna()
    eo = W["OUT_ciclo_inicio_observado"]
    tard = W[(eo > H) & (W["OUT_estado_etiqueta"] == "conocida")]
    ok = e.between(2, H).all() and (tard["OUT_y_desercion"] == 0).all() and (W.loc[W["OUT_y_desercion"] == 1, "OUT_ciclo_inicio_observado"] <= H).all()
    reg("V03", "Aplicación del horizonte H = 4", ok,
        f"e_i de los eventos ∈ {{{', '.join(str(int(x)) for x in sorted(e.unique()))}}}; estudiantes con inicio observado > H y etiqueta conocida: "
        f"{len(tard)} (todos con Y = 0: {(tard['OUT_y_desercion'] == 0).all()}).")

    # V04 desconocidas: la etiqueta conocida no puede cambiar con ningún futuro no observado
    import itertools
    tr_all = res["res"]["trayectoria_codificada"]
    estados_et = res["res"]["OUT_estado_etiqueta"]
    robusta_mal = indecidible_mal = 0
    for sid, tray in tr_all.items():
        if estados_et[sid] == "excluida_fallecimiento" or "F" in tray:
            continue
        faltan = max(0, min(4, H + 3 - len(tray)))
        ys = set()
        for comp in itertools.product("MNR", repeat=faltan):
            ext = list(tray) + list(comp)
            ext_ok = all(not (ext[q] == "R" and ext[q - 1] == "R" and q >= 2 and ext[q - 2] == "R") for q in range(len(ext)))
            if not ext_ok:
                continue
            ys.add(determinar_etiqueta(ext)[1])
        if estados_et[sid] == "conocida":
            robusta_mal += int(len(ys) != 1 or list(ys)[0] != res["res"].at[sid, "OUT_y_desercion"])
        else:
            indecidible_mal += int(len(ys) < 2)
    desc = W[W["OUT_estado_etiqueta"] == "desconocida"]
    ok = robusta_mal == 0 and indecidible_mal == 0 and W.loc[W["OUT_estado_etiqueta"] != "conocida", "OUT_y_desercion"].isna().all()
    reg("V04", "Etiquetas desconocidas cuando no hay seguimiento suficiente", ok,
        f"{len(desc)} etiquetas desconocidas (por cohorte: {desc.groupby('cohorte').size().to_dict()}). Se completó cada trayectoria con todos los "
        f"futuros posibles no observados (M/N/R): etiquetas conocidas que cambiarían = {robusta_mal}; desconocidas que en realidad eran decidibles = "
        f"{indecidible_mal}. En las cohortes sin ciclo H+1 observado las etiquetas que sí se deciden no son una muestra al azar; por eso esas cohortes "
        f"se excluyen completas (rol sin_seguimiento_completo).")

    # V05 reservas y dos ciclos consecutivos: casos del cuadro de casos especiales + patrones observados
    casos = [("MNMMM", 0, None, "interrupción de un ciclo con retorno"), ("MNN", 1, 2, "dos ciclos sin matrícula"),
             ("MRNN", 1, 3, "reserva omitida antes del evento"), ("MNRN", 1, 2, "reserva intermedia omitida al evaluar consecutividad"),
             ("MNRMM", 0, None, "no matrícula, reserva y retorno"), ("MMMNN", 1, 4, "inicio en el ciclo H"),
             ("MMMMNN", 0, None, "inicio en el ciclo H+1 (fuera del horizonte)"), ("MMMN", None, None, "ciclo H+1 no observado"),
             ("MMMNR", None, None, "reserva activa a la fecha de corte"), ("MMMNRN", 1, 4, "evento confirmado después de una reserva"),
             ("MMR", None, None, "ciclo H no observado"), ("MMMM", 0, None, "matriculado hasta H: e_i ≥ H+1"),
             ("MMMR", 0, None, "reserva en el ciclo H: e_i ≥ H+1"), ("MNNM", 1, 2, "retorno posterior al evento no cambia Y"),
             ("MRRNN", 1, 4, "dos reservas seguidas omitidas")]
    mal_casos = []
    for tray, y_esp, e_esp, desc_c in casos:
        est_c, y_c, e_c = determinar_etiqueta(list(tray))
        ok_c = (np.isnan(y_c) if y_esp is None else y_c == y_esp) and (np.isnan(e_c) if e_esp is None else e_c == e_esp)
        if not ok_c:
            mal_casos.append(f"{tray}: {desc_c}")
    tr = tr_all
    def patron_nrn(s):
        for q in range(1, min(len(s), H)):
            if s[q] == "N" and q + 1 < len(s) and s[q + 1] == "R":
                return True
        return False
    nrn = tr.apply(patron_nrn)
    ev_nrn = W.loc[nrn[nrn].index, ["OUT_y_desercion", "OUT_ciclo_inicio_desercion"]]
    def patron_nm(s):
        return any(s[q] == "N" and s[q + 1:].lstrip("R")[:1] == "M" for q in range(1, min(len(s), H)))
    nm = tr.apply(patron_nm)
    una_y1 = W.loc[nm[nm].index][W.loc[nm[nm].index, "OUT_y_desercion"] == 1]
    ok_una = all(tr[s_][int(W.at[s_, "OUT_ciclo_inicio_desercion"]) - 1] == "N" and
                 tr[s_][int(W.at[s_, "OUT_ciclo_inicio_desercion"]):].lstrip("R")[:1] == "N" for s_ in una_y1.index)
    ok = not mal_casos and ok_una and nrn.sum() > 0
    reg("V05", "Reservas omitidas y dos ciclos consecutivos sin matrícula", ok,
        f"{len(casos) - len(mal_casos)}/{len(casos)} casos de prueba del cuadro de casos especiales con el resultado esperado"
        f"{' (fallan: ' + '; '.join(mal_casos) + ')' if mal_casos else ''}. En la base: episodios con alguna reserva = {int(tr.str.contains('R').sum())}; "
        f"patrones N seguido de reserva con N ≤ H = {int(nrn.sum())} (Y = 1: {int((ev_nrn['OUT_y_desercion'] == 1).sum())}, Y = 0: "
        f"{int((ev_nrn['OUT_y_desercion'] == 0).sum())}, desconocidos: {int(ev_nrn['OUT_y_desercion'].isna().sum())}); interrupciones de un ciclo "
        f"seguidas de matrícula = {int(nm.sum())}, que no cuentan como evento (las {len(una_y1)} con Y = 1 tienen otro par sin matrícula posterior: {ok_una}).")

    # V06 sin registros posteriores al corte
    detalles, ok6 = [], True
    for t in VENTANAS:
        snap = construir_snapshot(raw, t)
        fmax = fecha_maxima_usada(raw, t)
        oo = _origenes(est, t)
        viol = int((fmax > oo).sum())
        pert = perturbar_futuro(raw, t, rng)
        snap2 = construir_snapshot(pert, t)
        r1, r2 = poblacion_en_riesgo(raw, t), poblacion_en_riesgo(pert, t)
        igual = _iguales(snap, snap2) and r1.equals(r2)
        mascara = W[f"en_riesgo_{t}"] == 1
        guardado = W.loc[mascara, list(snap.columns)]
        coincide = _iguales(guardado, snap.loc[guardado.index])
        ok6 = ok6 and viol == 0 and igual and coincide
        detalles.append(f"{t}: registros con fecha > o(t) leídos = {viol}; snapshot invariante al alterar todo registro posterior a o(t) = {igual}; wide = recálculo = {coincide}")
    reg("V06", "Ausencia de información registrada después del corte de cada ventana", ok6, " | ".join(detalles))

    # V07 etiqueta fuera de predictores
    prohibidos = [c for c in pred_cols if c.startswith("OUT_") or "en_riesgo" in c or "cohorte" in c or "id_" in c
                  or "fecha" in c or "estado_matricula" in c or "separacion" in c or "programa_cambio" in c]
    y = W["OUT_y_desercion"]
    lab = W[(W["rol_particion"] == "desarrollo") & y.notna()]
    iguales_y = []
    auc_max, auc_var = 0.0, ""
    diag = []
    for t in VENTANAS:
        sub = lab[lab[f"en_riesgo_{t}"] == 1]
        for c in [c for c in pred_cols if c.startswith(t + "_")]:
            col = pd.to_numeric(sub[c], errors="coerce") if sub[c].dtype != object else None
            if col is None or col.notna().sum() == 0:
                # categórica: AUC de la tasa de eventos por categoría (diagnóstico, ajustada en las mismas filas)
                tasas = sub.groupby(sub[c].astype(str))["OUT_y_desercion"].transform("mean")
                a = auc(sub["OUT_y_desercion"], tasas)
                tipo = "categórica (tasa por categoría)"
            else:
                a = auc(sub["OUT_y_desercion"], col)
                tipo = "numérica"
                if col.notna().all() and np.array_equal(col.to_numpy(dtype=float), sub["OUT_y_desercion"].to_numpy(dtype=float)):
                    iguales_y.append(c)
            a2 = max(a, 1 - a) if not np.isnan(a) else np.nan
            diag.append(dict(ventana=t, columna=c, tipo=tipo, n=len(sub), eventos=int(sub["OUT_y_desercion"].sum()),
                             auc_univariada_orientada=round(a2, 4) if not np.isnan(a2) else np.nan,
                             faltantes_pct=round(100 * sub[c].isna().mean(), 2)))
            if not np.isnan(a2) and a2 > auc_max:
                auc_max, auc_var = a2, c
    ok = (not prohibidos) and (not iguales_y) and auc_max < 0.85 and not any(c.startswith("OUT_") for c in pred_cols)
    reg("V07", "Ausencia de la etiqueta y sus derivados entre los predictores", ok,
        f"Columnas predictoras: {len(pred_cols)}; nombres prohibidos entre predictores: {prohibidos or 'ninguno'}; "
        f"predictores idénticos a Y: {iguales_y or 'ninguno'}; máxima AUC univariada orientada (cohortes de desarrollo) = {auc_max:.3f} ({auc_var}); umbral de alerta 0,85.")

    # V08 identificadores y proxies
    labw = W[W["OUT_y_desercion"].notna() & (W["cohorte_con_seguimiento_completo"] == 1)].copy()
    a_id = auc(labw["OUT_y_desercion"], pd.Series(labw.index).rank().to_numpy())
    a_fila = auc(labw["OUT_y_desercion"], np.arange(len(labw)))
    tasa_coh = labw.groupby("cohorte")["OUT_y_desercion"].transform("mean")
    a_coh = auc(labw["OUT_y_desercion"], tasa_coh)
    a_area = auc(labw["OUT_y_desercion"], labw.groupby("T0_A_area_programa")["OUT_y_desercion"].transform("mean"))
    vals = [max(x, 1 - x) for x in [a_id, a_fila, a_coh]]
    ok = all(v < 0.60 for v in vals) and wide["id_estudiante"].str.fullmatch(r"SYN-[A-Z2-9]{8}").all()
    reg("V08", "Identificadores, orden y cohorte no revelan el resultado", ok,
        f"AUC orientada del rango del id = {vals[0]:.3f}; del orden de filas = {vals[1]:.3f}; de la tasa por cohorte (ajustada en los mismos datos) = {vals[2]:.3f}; "
        f"umbral 0,60. Id con formato aleatorio SYN-XXXXXXXX sin cohorte. (Referencia: AUC de la tasa por área de programa = {max(a_area, 1 - a_area):.3f}.)")

    # V09 disponibilidad de bloques por ventana
    det9, ok9 = [], True
    for t in VENTANAS:
        cols_t = [c for c in pred_cols if c.startswith(t + "_")]
        esperado = [col_wide(t, v) for v in variables_en_ventana(t)]
        bl = sorted({c.split("_")[1] for c in cols_t})
        sub = W[W[f"en_riesgo_{t}"] == 1]
        cobertura = {b: round(float(sub[[c for c in cols_t if c.split('_')[1] == b]].notna().any(axis=1).mean()), 3) for b in bl}
        ok9 = ok9 and cols_t == esperado and bl == sorted(bloques_admisibles(t)) and all(x > 0.5 for x in cobertura.values())
        det9.append(f"{t}: bloques {'+'.join(bl)}; columnas = matriz: {cols_t == esperado}; cobertura por bloque en R(t) {cobertura}")
    # evidencia empírica de α: ningún registro de esas fuentes antes de o(T0)
    o0 = _origenes(est, "T0")
    pg = raw["pagos_cuotas"]
    pens_t0 = int((pg[pg["concepto"] != "derecho_matricula"]["fecha_vencimiento"] <= pg[pg["concepto"] != "derecho_matricula"]["id_estudiante"].map(o0)).sum())
    lms_t0 = int((raw["lms_semanal"]["fecha_fin_semana"] <= raw["lms_semanal"]["id_estudiante"].map(o0)).sum())
    enc_t0 = int((raw["encuesta_socioeconomica"]["fecha_respuesta"] <= raw["encuesta_socioeconomica"]["id_estudiante"].map(o0)).sum())
    not_t0 = int((raw["cursos_notas"]["fecha_registro_nota"] <= raw["cursos_notas"]["id_estudiante"].map(o0)).sum())
    ok9 = ok9 and pens_t0 == 0 and lms_t0 == 0 and enc_t0 == 0 and not_t0 == 0
    reg("V09", "Disponibilidad correcta de los bloques en cada ventana", ok9,
        " | ".join(det9) + f" | Registros con fecha ≤ o(T0): cuotas de pensión {pens_t0}, plataforma {lms_t0}, encuesta {enc_t0}, notas {not_t0}.")

    # V10 los ocho conjuntos
    det10, ok10 = [], True
    for t in VENTANAS:
        adm = conjuntos_admisibles(t)
        n_ok = 0
        for s in CONJUNTOS:
            if s in adm:
                ids_x, X = construir_matriz(wide, t, s)
                bl = set(s.split("+"))
                esperado = [c for c in pred_cols if c.startswith(t + "_") and c.split("_")[1] in bl]
                ok10 = ok10 and list(X.columns) == esperado and len(X) == int(W[f"en_riesgo_{t}"].sum()) \
                    and not any(c.startswith("OUT_") for c in X.columns)
                n_ok += 1
            else:
                try:
                    construir_matriz(wide, t, s)
                    ok10 = False
                except ConjuntoNoAplicable:
                    pass
        det10.append(f"{t}: Σ_t = {{{', '.join(adm)}}} ({n_ok}/8); s_t+ = {conjunto_mas_completo(t)}")
    esperado_t0 = ["A", "A+F", "A+S", "A+F+S"]
    ok10 = ok10 and conjuntos_admisibles("T0") == esperado_t0 and all(conjuntos_admisibles(t) == CONJUNTOS for t in ["T1", "T2", "T3"])
    reg("V10", "Reconstrucción exacta de los ocho conjuntos de información", ok10,
        " | ".join(det10) + ". Los pares no aplicables lanzan ConjuntoNoAplicable y no se rellenan.")

    # V11 sin transformaciones ajustadas con otras cohortes (pureza fila a fila)
    sub_ids = set(rng.choice(est["id_estudiante"].to_numpy(), 300, replace=False))
    raw_sub = {k: v[v["id_estudiante"].isin(sub_ids)].reset_index(drop=True) for k, v in raw.items()}
    ok11 = True
    for t in VENTANAS:
        a = construir_snapshot(raw, t).loc[sorted(sub_ids)]
        b = construir_snapshot(raw_sub, t).loc[sorted(sub_ids)]
        ok11 = ok11 and _iguales(a, b)
    test_ids = set(W.index[W["rol_particion"] == "prueba"])
    raw_dev = {k: v[~v["id_estudiante"].isin(test_ids)].reset_index(drop=True) for k, v in raw.items()}
    a = construir_snapshot(raw, "T2").drop(index=list(test_ids))
    b = construir_snapshot(raw_dev, "T2")
    ok11 = ok11 and _iguales(a, b)
    reg("V11", "Ausencia de transformaciones ajustadas con cohortes de validación o prueba", ok11,
        "Cada variable es función solo de los registros del propio estudiante: recalcular con 300 estudiantes aislados y recalcular "
        "sin las cohortes de prueba produce valores idénticos. No hay imputación, escalamiento ni codificación ajustados en el dataset "
        "(se dejan al pipeline, dentro de cada bloque de entrenamiento).")

    # V12 reproducibilidad
    h1 = huellas(res)
    res2 = construir_todo(semilla)
    h2 = huellas(res2)
    res3 = construir_todo(semilla + 1)
    h3 = huellas(res3)
    iguales = all(h1[k] == h2[k] for k in h1)
    distintas = sum(h1[k] != h3[k] for k in h1)
    reg("V12", "Reproducibilidad exacta con la misma semilla", iguales and distintas > 0,
        f"Archivos con hash SHA-256 idéntico al regenerar con semilla {semilla}: {sum(h1[k] == h2[k] for k in h1)}/{len(h1)}; "
        f"con semilla {semilla + 1} cambian {distintas}/{len(h1)} (control negativo).")

    # Controles complementarios
    anid = all(((W[f"en_riesgo_{VENTANAS[i]}"] >= W[f"en_riesgo_{VENTANAS[i + 1]}"]).all()) for i in range(3))
    t0_all = (W["en_riesgo_T0"] == 1).all()
    onset_ok = True
    for jj, t in enumerate(VENTANAS[1:], start=1):
        ee = W.loc[(W[f"en_riesgo_{t}"] == 1) & (W["OUT_y_desercion"] == 1), "OUT_ciclo_inicio_desercion"]
        onset_ok = onset_ok and (ee > jj).all()
    reg("V13", "Poblaciones anidadas R(T3) ⊆ R(T2) ⊆ R(T1) ⊆ R(T0) y eventos aún por ocurrir", anid and t0_all and onset_ok,
        f"Anidamiento: {anid}; R(T0) = todos los matriculados en el ciclo 1: {t0_all}; en R(Tj) todos los eventos tienen e_i > j: {onset_ok}.",
        "complementaria")

    fuera = []
    for v in VARS:
        for t in VENTANAS:
            if ORD[v["alfa"]] > ORD[t]:
                continue
            c = col_wide(t, v)
            if v["cats"]:
                malos = set(W[c].dropna().astype(str)) - set(map(str, v["cats"]))
                if malos:
                    fuera.append(f"{c}: {malos}")
            else:
                x = pd.to_numeric(W[c], errors="coerce").dropna()
                if len(x) and (x.min() < v["rmin"] or x.max() > v["rmax"]):
                    fuera.append(f"{c}: [{x.min()}, {x.max()}]")
    reg("V14", "Rangos y categorías válidos según el diccionario", not fuera,
        f"Columnas fuera de rango: {fuera or 'ninguna'}.", "complementaria")

    fc = pd.Timestamp(FECHA_CORTE_DATOS)
    tarde = 0
    for tab, cols in COLS_FECHA.items():
        for col in cols:
            tarde += int((raw[tab][col] > fc).sum())
    reg("V15", "Ningún registro posterior a la fecha de corte de datos", tarde == 0,
        f"Registros con fecha > {FECHA_CORTE_DATOS}: {tarde}. Último periodo observado: {periodo_label(P_OBS)}.", "complementaria")

    dev = part.loc[part["rol_particion"] == "desarrollo", "cohorte"].tolist()
    pru = part.loc[part["rol_particion"] == "prueba", "cohorte"].tolist()
    folds = [c for c in part.columns if c.startswith("fold_")]
    ok_f = True
    for f in folds:
        val = part.loc[part[f] == "validacion", "cohorte"].tolist()
        aj = part.loc[part[f].isin(["ajuste", "interna_ajuste_hiperparametros_y_calibracion"]), "cohorte"].tolist()
        ok_f = ok_f and len(val) == 1 and max(aj) < val[0] and val[0] in dev and not (set(aj) & set(pru))
    ok = max(dev) < min(pru) and ok_f and len(folds) >= 2
    reg("V16", "Partición cronológica (desarrollo antes que prueba; rolling-origin por cohorte)", ok,
        f"Desarrollo = cohortes {dev}; prueba = {pru}; sin seguimiento completo = "
        f"{part.loc[part['rol_particion'] == 'sin_seguimiento_completo', 'cohorte'].tolist()}; folds = {len(folds)} (c0 = {C0}); "
        f"cada fold entrena con cohortes anteriores a su cohorte de validación y nunca usa cohortes de prueba: {ok_f}.", "complementaria")

    return pd.DataFrame(ctr), pd.DataFrame(diag)


# =============================================================================
# 9. TABLAS DEL REPORTE DE CALIDAD
# =============================================================================
def tablas_calidad(res: dict) -> dict:
    W, long, part = res["wide"].set_index("id_estudiante"), res["long"], res["part"]
    pred_cols = [c for c in W.columns if c[:3] in ("T0_", "T1_", "T2_", "T3_")]
    t = {}
    t["resumen"] = pd.DataFrame([
        ("Episodios (estudiantes sintéticos)", len(W)),
        ("Cohortes", W["cohorte"].nunique()),
        ("Filas del archivo longitudinal (estudiante × ciclo)", len(long)),
        ("Variables predictoras lógicas", len(VARS)),
        ("Columnas predictoras en wide (variable × ventana)", len(pred_cols)),
        ("Columnas totales en wide", W.shape[1] + 1),
        ("Etiqueta conocida", int((W["OUT_estado_etiqueta"] == "conocida").sum())),
        ("Etiqueta desconocida", int((W["OUT_estado_etiqueta"] == "desconocida").sum())),
        ("Excluida por fallecimiento", int((W["OUT_estado_etiqueta"] == "excluida_fallecimiento").sum())),
        ("Y = 1 (todas las cohortes)", int((W["OUT_y_desercion"] == 1).sum())),
        ("Y = 0 (todas las cohortes)", int((W["OUT_y_desercion"] == 0).sum())),
        ("Fecha de corte de datos (sintética)", str(FECHA_CORTE_DATOS)),
        ("Último periodo observado", periodo_label(P_OBS)),
    ], columns=["indicador", "valor"])
    # etiquetas por cohorte
    g = W.groupby("cohorte")
    t["etiquetas_por_cohorte"] = pd.DataFrame({
        "periodo_ingreso": g["periodo_ingreso"].first(),
        "rol_particion": g["rol_particion"].first(),
        "n": g.size(),
        "conocida": g["OUT_estado_etiqueta"].apply(lambda s: (s == "conocida").sum()),
        "desconocida": g["OUT_estado_etiqueta"].apply(lambda s: (s == "desconocida").sum()),
        "excluida_fallecimiento": g["OUT_estado_etiqueta"].apply(lambda s: (s == "excluida_fallecimiento").sum()),
        "y1": g["OUT_y_desercion"].apply(lambda s: (s == 1).sum()),
        "y0": g["OUT_y_desercion"].apply(lambda s: (s == 0).sum()),
    }).reset_index()
    t["etiquetas_por_cohorte"]["prevalencia_y1_entre_conocidas"] = (t["etiquetas_por_cohorte"]["y1"] / (t["etiquetas_por_cohorte"]["y1"] + t["etiquetas_por_cohorte"]["y0"])).round(4)
    # población por ventana y rol
    filas = []
    for v in VENTANAS:
        for rol in ["desarrollo", "prueba", "sin_seguimiento_completo"]:
            sub = W[(W[f"en_riesgo_{v}"] == 1) & (W["rol_particion"] == rol)]
            y = sub["OUT_y_desercion"]
            filas.append(dict(ventana=v, rol_particion=rol, n_en_riesgo=len(sub), eventos_y1=int((y == 1).sum()),
                              no_eventos_y0=int((y == 0).sum()), sin_etiqueta=int(y.isna().sum()),
                              prevalencia=round(float((y == 1).sum() / max(1, y.notna().sum())), 4)))
        sub = W[(W[f"en_riesgo_{v}"] == 1) & (W["rol_particion"] == "desarrollo")]
        for coh, ss in sub.groupby("cohorte"):
            y = ss["OUT_y_desercion"]
            filas.append(dict(ventana=v, rol_particion=f"desarrollo · cohorte {coh}", n_en_riesgo=len(ss),
                              eventos_y1=int((y == 1).sum()), no_eventos_y0=int((y == 0).sum()),
                              sin_etiqueta=int(y.isna().sum()),
                              prevalencia=round(float((y == 1).sum() / max(1, y.notna().sum())), 4)))
    t["clases_por_ventana_y_rol"] = pd.DataFrame(filas)
    # e_i
    e = W.loc[W["OUT_y_desercion"] == 1, "OUT_ciclo_inicio_desercion"].value_counts().sort_index()
    eo = W.loc[W["OUT_estado_etiqueta"] == "conocida", "OUT_ciclo_inicio_observado"].value_counts().sort_index()
    t["inicio_desercion"] = pd.DataFrame({"ciclo": sorted(set(e.index) | set(eo.index))}).assign(
        eventos_y1_con_e_i=lambda d: d["ciclo"].map(e).fillna(0).astype(int),
        inicio_observado_entre_etiquetas_conocidas=lambda d: d["ciclo"].map(eo).fillna(0).astype(int))
    casos = [
        ("Episodios con al menos una reserva aprobada", int(W.index.map(res["res"]["trayectoria_codificada"]).str.contains("R").sum())),
        ("Eventos asociados a separación académica (sensibilidad i)", int((W["OUT_separacion_academica"] == 1).sum())),
        ("Eventos con retorno posterior observado (Y no cambia)", int((W["OUT_retorno_posterior_al_evento"] == 1).sum())),
        ("Tasa de retorno entre eventos con seguimiento", round(float(W["OUT_retorno_posterior_al_evento"].mean()), 4)),
        ("Episodios con cambio de programa (no es evento)", int(long.groupby("id_estudiante")["cambio_programa"].max().sum())),
        ("Episodios con retiro total en algún ciclo", int(long.groupby("id_estudiante")["retiro_total"].max().sum())),
        ("Fallecimientos registrados", int(W["OUT_fallecimiento_registrado"].sum())),
    ]
    t["casos_especiales"] = pd.DataFrame(casos, columns=["caso", "valor"])
    # faltantes dentro de R(t)
    filas = []
    for v in VENTANAS:
        sub = W[W[f"en_riesgo_{v}"] == 1]
        for c in [c for c in pred_cols if c.startswith(v + "_")]:
            filas.append(dict(ventana=v, columna=c, n_en_riesgo=len(sub), faltantes=int(sub[c].isna().sum()),
                              faltantes_pct=round(100 * sub[c].isna().mean(), 2),
                              origen_faltante=("estructural: modalidad sin examen" if "puntaje_admision" in c else
                                               "no respondió la encuesta (indicador S_encuesta_respondida)" if c.split("_", 2)[2] in
                                               ["ingreso_hogar_rango", "trabaja", "horas_trabajo_semana", "apoyo_economico_familiar", "primera_generacion_universitaria"] else
                                               "sin ciclo previo / sin cuotas pagadas" if sub[c].isna().any() else "")))
    t["faltantes_en_R_t"] = pd.DataFrame(filas)
    # rangos
    filas = []
    for var in VARS:
        for v in VENTANAS:
            if ORD[var["alfa"]] > ORD[v]:
                continue
            c = col_wide(v, var)
            x = W[c]
            if var["cats"]:
                filas.append(dict(columna=c, tipo="categórica", minimo="", maximo="", media="",
                                  valores_observados="; ".join(f"{k}={n}" for k, n in x.value_counts().items()),
                                  rango_permitido=", ".join(var["cats"])))
            else:
                xn = pd.to_numeric(x, errors="coerce")
                filas.append(dict(columna=c, tipo="numérica", minimo=xn.min(), maximo=xn.max(), media=round(xn.mean(), 3),
                                  valores_observados="", rango_permitido=f"[{var['rmin']}, {var['rmax']}]"))
    t["rangos"] = pd.DataFrame(filas)
    # consistencia longitudinal
    t["estados_longitudinal"] = long.groupby(["ciclo_regular", "estado_matricula"]).size().unstack(fill_value=0).reset_index()
    return t


# =============================================================================
# 10. README
# =============================================================================
def texto_readme(res, ctr, calidad, semilla, hs) -> str:
    W = res["wide"].set_index("id_estudiante")
    resumen = dict(calidad["resumen"].values)
    clases = calidad["clases_por_ventana_y_rol"]
    clases = clases[~clases["rol_particion"].str.contains("·")]
    def tabla_md(df):
        cab = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
        return cab + "".join("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in fila) + " |\n" for fila in df.itertuples(index=False))
    lab = W[W["OUT_estado_etiqueta"] == "conocida"]
    part = res["part"]
    ctr_md = tabla_md(ctr[["codigo", "control", "resultado"]])
    return f"""# Dataset sintético longitudinal para el OE3 — Método temporal de detección temprana de deserción

> **DATOS 100 % SINTÉTICOS.** No provienen de la UPC ni de ninguna otra institución. Las relaciones entre
> variables y riesgo son supuestos artificiales del generador. Sirven para desarrollar y probar el pipeline del
> OE3, **no** como evidencia de que el método funciona con estudiantes reales ni para declarar suficiencia
> predictiva en una universidad.

Versión del generador {VERSION} · semilla {semilla} · fecha de corte sintética {FECHA_CORTE_DATOS}.

## 1. Cómo regenerar

```bash
pip install numpy pandas openpyxl        # Python >= 3.10
python generar_dataset_sintetico.py --salida salida --semilla {semilla}
```

El script no lee archivos externos. Genera todos los archivos, ejecuta las validaciones del punto 11 y escribe
este README con las cifras calculadas. `--sin-validar` omite las validaciones (más rápido). Con la misma semilla,
los CSV son idénticos byte a byte (control V12).

## 2. Fuente metodológica

La estructura sigue la formulación del manuscrito *Temporal Method for Determining Information Sufficiency in
the Early Detection of Academic Dropout Risk Using Machine Learning* (versión revisada el 23-10-2026) y el
objetivo OE3 del trabajo de investigación. El PDF y el .docx no estaban adjuntos en la sesión de generación;
las definiciones se tomaron de la última versión del manuscrito trabajada en la conversación de corrección
técnica. Conviene contrastarlas con el PDF final (ver §7).

## 3. Archivos

| Archivo | Contenido |
|---|---|
| `dataset_sintetico_longitudinal.csv` | Una fila por estudiante × ciclo regular observado (1–8): estado de matrícula, reserva, retiro total, cambio de programa, separación, fallecimiento y agregados del ciclo con su fecha de disponibilidad. |
| `dataset_sintetico_wide.csv` | Una fila por estudiante: columnas administrativas, `en_riesgo_Tk`, snapshots `Tk_B_variable` (valores a o(Tk), solo para R(Tk)) y columnas de resultado `OUT_*` una sola vez. |
| `diccionario_variables.xlsx` | Variables predictoras, columnas administrativas y de resultado, columnas longitudinales, fuentes crudas y convenciones. |
| `matriz_disponibilidad_temporal.xlsx` | Variable × ventana con justificación; Σ_t por ventana; definición de ventanas y R(t). |
| `reporte_calidad_dataset.xlsx` | Controles ejecutados, etiquetas por cohorte, clases por ventana y rol, faltantes, rangos, casos especiales, diagnóstico univariado. |
| `particion_temporal_cohortes.csv` | Rol de cada cohorte (desarrollo/prueba/sin seguimiento) y rol en cada fold rolling-origin. |
| `ids_cohortes_prueba_bloqueadas.csv` | Lista de identificadores de prueba, para registrarla antes del análisis. |
| `fuentes_crudas/*.csv` | Registros fechados (admisión, matrícula, cursos, pagos, plataforma, encuesta) de los que se derivan los snapshots. |
| `generar_dataset_sintetico.py` | Generador, constructor de snapshots, `construir_matriz(wide, t, conjunto)` y validaciones. |

## 4. Cifras de la base generada

- Episodios: **{resumen['Episodios (estudiantes sintéticos)']}** en **{resumen['Cohortes']}** cohortes semestrales ({periodo_label(1)} a {periodo_label(N_COHORTES)}).
- Filas longitudinales: **{resumen['Filas del archivo longitudinal (estudiante × ciclo)']}**. Variables predictoras lógicas: **{len(VARS)}** (A {sum(v['bloque'] == 'A' for v in VARS)}, F {sum(v['bloque'] == 'F' for v in VARS)}, S {sum(v['bloque'] == 'S' for v in VARS)}, B {sum(v['bloque'] == 'B' for v in VARS)}); columnas predictoras en wide: **{resumen['Columnas predictoras en wide (variable × ventana)']}**.
- Etiquetas: conocidas **{resumen['Etiqueta conocida']}**, desconocidas **{resumen['Etiqueta desconocida']}**, excluidas por fallecimiento **{resumen['Excluida por fallecimiento']}**.
- Y = 1: **{resumen['Y = 1 (todas las cohortes)']}**; Y = 0: **{resumen['Y = 0 (todas las cohortes)']}** (prevalencia entre conocidas {(lab['OUT_y_desercion'] == 1).mean():.3f}). La prevalencia es un parámetro artificial, no una estimación.
- Partición: desarrollo = cohortes {part.loc[part['rol_particion'] == 'desarrollo', 'cohorte'].tolist()}, prueba = {part.loc[part['rol_particion'] == 'prueba', 'cohorte'].tolist()}, sin seguimiento completo = {part.loc[part['rol_particion'] == 'sin_seguimiento_completo', 'cohorte'].tolist()}; {sum(c.startswith('fold_') for c in part.columns)} folds con c0 = {C0}.

Población en riesgo y clases por ventana:

{tabla_md(clases)}
## 5. Diseño temporal implementado

- **Ventanas y orígenes.** o_c(T0) = cierre de matrícula del ciclo 1; o_c(Tj) = cierre de notas del ciclo j. Solo se usan registros con fecha ≤ o_c(t). El constructor de snapshots filtra cada fuente cruda por su fecha de registro.
- **Bloques y Σ_t.** Σ_T0 = {{{', '.join(conjuntos_admisibles('T0'))}}} (B no tiene registros antes de clases); Σ_T1 = Σ_T2 = Σ_T3 = los ocho conjuntos. s_T0+ = {conjunto_mas_completo('T0')}; s_Tj+ = A+F+S+B. `construir_matriz` lanza `ConjuntoNoAplicable` para los pares sin bloque disponible.
- **Poblaciones.** R(T0) = matriculados en el ciclo 1; R(Tj) = R(Tj−1) ∩ activos en el ciclo j (matriculado y sin retiro de todos los cursos a o(Tj)). Los snapshots solo se llenan para R(t).
- **Etiqueta.** e_i = primer ciclo j ≥ 2 sin matrícula cuyo siguiente ciclo regular no reservado tampoco tiene matrícula; reservas omitidas; Y = 1 si e_i ≤ H = 4. La etiqueta se decide solo con los registros observados a la fecha de corte; si no alcanzan, queda desconocida. Retornos posteriores no cambian Y.
- **Partición.** Cohortes etiquetadas ordenadas; las {N_COHORTES_PRUEBA} más recientes son de prueba; en desarrollo, rolling-origin con cohorte interna para hiperparámetros y calibración (ver `particion_temporal_cohortes.csv`).

## 6. Mecanismo generador (supuestos artificiales)

Cuatro latentes por estudiante, nunca exportadas: ses ~ N(0,1); z_acad = 0,35·ses + ruido; z_motiv = 0,20·z_acad + ruido;
z_fin = −0,55·ses + ruido. En cada ciclo se sortean un choque N(0,1), una dificultad financiera (Bernoulli) y un
desenganche ≥ 0. Esas cantidades generan notas, inasistencia, retiros, pagos y actividad del ciclo (fórmulas en
el diccionario). **Después** de generar el ciclo k se decide la matrícula del ciclo k+1:

P(no matrícula) = σ(β0,k + u_cohorte + área − 0,40·z_motiv − 0,15·(promedio_k − 12)/2 + 0,5·fracción_créditos_desaprobados
+ 0,6·dificultad_fin + 0,50·deuda_al_cierre + 0,30·[horas>20] + 0,70·desenganche + 0,30·choque + 0,20·z_fin
+ 0,35·[horas>20]·[créditos≥22] + 0,3·[promedio_acum<10,5] + 1,3·[retiro_total]), con β0 = {B0_RIESGO}, u_cohorte ~ N(0; 0,12).

P(reserva) = σ(−3,8 + 0,5·dificultad_fin + 0,3·choque). Tras no matricularse: retorno con prob. σ(−0,85 + 0,3·z_motiv) tras un
ciclo y 0,06 después. Tras una reserva: matrícula 0,55, nueva reserva 0,15 (máximo dos seguidas), no matrícula 0,30.
Separación académica si promedio acumulado < 9,5 y ≥ 5 desaprobados (prob. 0,4). Fallecimiento 0,0006 por ciclo.
Cambio de programa 0,02 por ciclo. Ciclos ≥ 5: riesgo con latentes y ruido. Las deudas impagas se regularizan
**después** de o(Tk) (al matricularse o más tarde), lo que crea registros futuros que el constructor debe ignorar.

Consecuencias buscadas: la señal está repartida entre bloques (ningún predictor univariado supera la AUC indicada
en V07); hay ruido individual y solapamiento; hay no linealidades e interacciones (umbral de inasistencia,
trabajo × carga, promedio acumulado bajo), por lo que ninguna familia de modelos está favorecida por construcción
(no se verificó entrenando modelos).

## 7. Supuestos y ambigüedades documentadas

1. **Retiro total.** El paper define e_i con "no matriculado" y "activo" como matriculado sin retiro de todos los cursos. Se adoptó la lectura literal: un ciclo con retiro total cuenta como matriculado para e_i, pero excluye al estudiante de R(t). Si la institución trata el retiro total como no matrícula, cambia Y.
2. **Etiqueta por estudiante vs. por cohorte.** El paper etiqueta a un estudiante si los registros deciden si e_i ≤ H (un estudiante matriculado hasta el ciclo H ya tiene Y = 0 sin esperar al ciclo H+1). En las cohortes sin ciclo H+1 observado, los casos que no se pueden decidir no son aleatorios (en la cohorte 11, quienes no se matricularon en el ciclo 4; en la cohorte 12, todos los que siguen matriculados), así que las etiquetas conocidas de esas cohortes estarían sesgadas. Se marcan con `rol_particion = sin_seguimiento_completo` y se excluyen completas de los experimentos supervisados; sirven para probar el manejo de etiquetas desconocidas.
3. **Fallecimiento.** Se excluye el episodio si la baja ocurre en los ciclos 1..H+1 observados; después se conserva la etiqueta.
4. **Reserva en R(t).** Un estudiante con reserva en el ciclo j no está activo y sale de R(Tj) aunque luego retorne (R anidado, lectura literal).
5. **Asistencia.** Se supone disponible solo como consolidado al cierre de notas.
6. **Encuesta socioeconómica.** Aplicada en las semanas 3–6 del ciclo 1 (α = T1); el bloque S en T0 solo contiene datos del registro de admisión. Toda la disponibilidad es un supuesto pendiente de verificación institucional.
7. **Transferencias externas.** No se distinguen de la deserción, como prevé el paper (no hay columna de motivo).
8. **Calendario.** Fechas sintéticas anteriores a 2020 para no simular el periodo de clases remotas de emergencia; no hay choques de calendario.
9. **Partición.** {N_COHORTES_PRUEBA} cohortes de prueba; c0 = {C0}; el número exacto de cohortes de prueba en el estudio real depende de los datos.

## 8. Controles ejecutados

{ctr_md}
El detalle de cada control está en `reporte_calidad_dataset.xlsx` (hoja `controles`).

## 9. Limitaciones

- Todo es artificial: variables, disponibilidad, fechas, tasas y relaciones. Las métricas, SHAP o LIME calculados con esta base describen el comportamiento de los modelos sobre este mecanismo, no factores de deserción reales.
- El tamaño (≈4.000 episodios, 12 cohortes) es un parámetro de simulación, no una garantía de suficiencia estadística. En T3, con H = 4, solo quedan eventos con inicio en el ciclo 4, por lo que esa ventana tiene pocos eventos.
- La deriva entre cohortes es mínima (efecto aleatorio pequeño); los datos reales pueden tener cambios curriculares, de política o de modalidad.
- No se fijan τ_k, δ_k, ε_a, ε_b, q, n_min ni p_min: son decisiones previas del estudio, no del dataset.

## 10. Uso posterior en el OE3

1. Cargar `dataset_sintetico_wide.csv` y `particion_temporal_cohortes.csv`; registrar `ids_cohortes_prueba_bloqueadas.csv` y no leer `OUT_*` de esas filas hasta el congelamiento.
2. Excluir cohortes `sin_seguimiento_completo` y estudiantes con `OUT_estado_etiqueta ≠ conocida` (contarlos e informarlos).
3. Para cada ventana t y conjunto s: `ids, X = construir_matriz(wide, t, s, cohortes=...)`; si lanza `ConjuntoNoAplicable`, registrar el par como no aplicable.
4. Ajustar imputación (con indicadores), one-hot, escalamiento (LR, SVM) y calibración Platt solo en las cohortes de ajuste / interna de cada fold.
5. Entrenar LR-L2, RF, XGBoost, LightGBM y SVM-RBF con el mismo presupuesto N_h; generar predicciones fuera de fold sobre V(t).
6. Calcular AUC-ROC, Brier escalado y Recall@q (más métricas secundarias), aplicar la compuerta de calibración y la regla de suficiencia con bootstrap pareado estratificado (cohorte × resultado), comparando sobre V(t').
7. Calcular SHAP sobre el modelo seleccionado y congelado de cada escenario, con su ventana y sus columnas; LIME solo para casos individuales de esa misma ventana. Si una variable domina, revisar su evidencia de disponibilidad en la matriz.

Huellas SHA-256 de los CSV (para verificar reproducibilidad):

{chr(10).join(f'- `{k}`: `{v[:16]}…`' for k, v in hs.items())}
"""


# =============================================================================
# 11. PRINCIPAL
# =============================================================================
def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera el dataset sintético del OE3 (datos 100 % sintéticos).")
    ap.add_argument("--salida", default="salida")
    ap.add_argument("--semilla", type=int, default=SEMILLA_DEFECTO)
    ap.add_argument("--sin-validar", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    os.makedirs(os.path.join(a.salida, "fuentes_crudas"), exist_ok=True)
    res = construir_todo(a.semilla)
    hs = huellas(res)
    for nombre, df in archivos_csv(res).items():
        with open(os.path.join(a.salida, nombre), "wb") as fh:
            fh.write(csv_bytes(df))
    convenciones = pd.DataFrame([
        ("Datos", "100 % sintéticos; no atribuibles a ninguna institución."),
        ("Nombre de columna predictora", "{Ventana}_{Bloque}_{variable}, p. ej. T2_F_saldo_pendiente_soles = valor a o(T2)."),
        ("Selección del conjunto s en t", "Columnas que empiezan por t_ y cuyo bloque ∈ s; usar construir_matriz()."),
        ("Población", "Filtrar en_riesgo_t = 1; fuera de R(t) los snapshots están vacíos a propósito."),
        ("Resultado", "Columnas OUT_*; nunca predictores; la etiqueta aparece una sola vez."),
        ("Prohibidos como predictores", "id_estudiante, cohorte, periodo_ingreso, rol_particion, cohorte_con_seguimiento_completo, fecha_origen_*, en_riesgo_*, OUT_*."),
        ("Faltantes", "NaN; imputar dentro del bloque de entrenamiento. S_encuesta_respondida = 0 indica bloque de encuesta ausente."),
        ("Nota aprobatoria", f"{NOTA_APROBATORIA} (escala 0–20, parámetro sintético)."),
        ("Horizonte", f"H = {H} ciclos regulares; etiqueta confirmada normalmente con el ciclo H+1."),
    ], columns=["convencion", "detalle"])
    escribir_xlsx(os.path.join(a.salida, "diccionario_variables.xlsx"), [
        ("variables_predictoras", tabla_diccionario(), "DATOS SINTÉTICOS · Variables lógicas j con bloque b(j) y primera ventana admisible α(j)."),
        ("admin_y_resultado", tabla_columnas_admin(), "Columnas no predictoras del archivo wide."),
        ("longitudinal", tabla_longitudinal(), "Columnas de dataset_sintetico_longitudinal.csv."),
        ("fuentes_crudas", tabla_fuentes(), "Registros fechados en fuentes_crudas/."),
        ("convenciones", convenciones, None),
    ])
    escribir_xlsx(os.path.join(a.salida, "matriz_disponibilidad_temporal.xlsx"), [
        ("variable_x_ventana", tabla_matriz(), "DATOS SINTÉTICOS · DISPONIBLE si α(j) ⪯ t. Disponibilidad = supuesto sintético pendiente de verificación institucional."),
        ("conjuntos_por_ventana", tabla_conjuntos(), "Σ_t = conjuntos cuyos bloques tienen al menos una variable con α ⪯ t."),
        ("ventanas_y_poblaciones", tabla_ventanas(), "Orígenes o(t) y poblaciones anidadas R(t) (H = 4)."),
    ])
    calidad = tablas_calidad(res)
    if a.sin_validar:
        ctr = pd.DataFrame([dict(codigo="—", control="Validaciones omitidas (--sin-validar)", categoria="", resultado="NO EJECUTADO", detalle="")])
        diag = pd.DataFrame()
    else:
        ctr, diag = validar(res, a.semilla)
    hojas = [("controles", ctr, "Resultado real de cada comprobación ejecutada por validar()."),
             ("resumen", calidad["resumen"], "DATOS SINTÉTICOS."),
             ("etiquetas_por_cohorte", calidad["etiquetas_por_cohorte"], None),
             ("clases_por_ventana_y_rol", calidad["clases_por_ventana_y_rol"], "Población R(t) por rol de partición; prevalencia entre etiquetas conocidas."),
             ("inicio_desercion", calidad["inicio_desercion"], "Distribución de e_i (eventos) y del inicio observado (incluye e_i > H, que dan Y = 0)."),
             ("casos_especiales", calidad["casos_especiales"], None),
             ("faltantes_en_R_t", calidad["faltantes_en_R_t"], "Faltantes calculados dentro de R(t)."),
             ("rangos", calidad["rangos"], None),
             ("estados_longitudinal", calidad["estados_longitudinal"], "Filas del longitudinal por ciclo y estado."),
             ("huellas_sha256", pd.DataFrame(list(hs.items()), columns=["archivo", "sha256"]), None)]
    if len(diag):
        hojas.insert(6, ("diagnostico_univariado", diag, "Diagnóstico del mecanismo sintético (cohortes de desarrollo, etiquetas conocidas). No es un resultado de la investigación."))
    escribir_xlsx(os.path.join(a.salida, "reporte_calidad_dataset.xlsx"), hojas)
    with open(os.path.join(a.salida, "README_dataset.md"), "w", encoding="utf-8") as fh:
        fh.write(texto_readme(res, ctr, calidad, a.semilla, hs))
    import shutil
    if os.path.abspath(__file__) != os.path.abspath(os.path.join(a.salida, "generar_dataset_sintetico.py")):
        shutil.copy(os.path.abspath(__file__), os.path.join(a.salida, "generar_dataset_sintetico.py"))
    print(ctr[["codigo", "resultado"]].to_string(index=False))
    print(f"Listo en {time.time() - t0:.1f} s → {os.path.abspath(a.salida)}")
    return 0 if (ctr["resultado"] != "FALLIDO").all() else 1


if __name__ == "__main__":
    sys.exit(main())
