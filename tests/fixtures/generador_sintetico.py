"""Generador de historiales de matrícula SINTÉTICOS, solo para pruebas (H2.3).

Todo lo que produce es inventado: no proviene de ninguna institución y sus
probabilidades son supuestos de simulación, no estimaciones. Cada fila lleva
``origen_datos = SINTETICO``. Sigue el diccionario de
``config/ejemplos/diccionario_sintetico.yaml``.

Incluye a propósito los casos especiales que el objetivo deberá tratar en H2.4:
pausas (reserva), reingresos, transferencias (traslado), retiros totales y
seguimiento incompleto en las cohortes más recientes. Los cuatro primeros
estudiantes tienen historiales fijos para que cada caso aparezca siempre.

Nunca se usa para reportar resultados (sección 6 de la especificación).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

ORIGEN = "SINTETICO"
COHORTES = ("2014-1", "2014-2", "2015-1", "2015-2", "2016-1", "2016-2", "2017-1", "2017-2")
FECHA_CORTE = date(2019, 1, 15)
"""Fecha de corte ficticia: las cohortes recientes no completan sus 8 ciclos."""
CICLOS = 8
ESTADOS = ("matriculado", "no_matriculado", "reserva", "retiro_total", "traslado")
COLUMNAS = (
    "codigo_estudiante",
    "origen_datos",
    "cohorte",
    "ciclo",
    "fecha_registro",
    "estado_matricula",
    "puntaje_admision",
    "promedio_ciclo",
    "creditos_aprobados_ciclo",
    "beca_al_ingreso",
    "deuda_vencida_ciclo",
    "tipo_colegio",
    "rango_ingreso_familiar",
    "horas_plataforma_ciclo",
)

# Historiales fijos de los cuatro primeros estudiantes (cohorte 2014-1).
HISTORIALES_FIJOS = {
    "pausa": ("matriculado", "reserva", "matriculado", "matriculado"),
    "reingreso": ("matriculado", "no_matriculado", "matriculado", "matriculado"),
    "transferencia": ("matriculado", "matriculado", "traslado"),
    "retiro_total": ("matriculado", "retiro_total", "no_matriculado", "no_matriculado"),
}


@dataclass(frozen=True)
class ProblemasSembrados:
    """Problemas de calidad introducidos a propósito para probar la auditoría."""

    fila_nula_obligatoria: int
    fila_fuera_de_rango: int
    fila_tipo_invalido: int
    fila_duplicada: int


def _inicio_cohorte(cohorte: str) -> date:
    anio, semestre = cohorte.split("-")
    return date(int(anio), 3 if semestre == "1" else 8, 15)


def _fecha_ciclo(cohorte: str, ciclo: int) -> date:
    return _inicio_cohorte(cohorte) + timedelta(days=183 * (ciclo - 1))


def ciclos_observados(cohorte: str) -> int:
    """Ciclos con fecha anterior al corte: menos de 8 en las cohortes recientes."""
    return sum(1 for c in range(1, CICLOS + 1) if _fecha_ciclo(cohorte, c) <= FECHA_CORTE)


def _siguiente_estado(anterior: str, riesgo: float, rng: np.random.Generator) -> str:
    factor = float(np.exp(0.6 * riesgo))
    if anterior == "matriculado":
        salidas = {
            "no_matriculado": 0.07 * factor,
            "reserva": 0.03 * factor,
            "retiro_total": 0.02 * factor,
            "traslado": 0.015 * factor,
        }
        salidas["matriculado"] = max(0.0, 1.0 - sum(salidas.values()))
    elif anterior == "no_matriculado":
        salidas = {"matriculado": 0.25 / factor, "no_matriculado": 1 - 0.25 / factor}
    elif anterior == "reserva":
        salidas = {"matriculado": 0.6, "reserva": 0.15, "no_matriculado": 0.25}
    else:  # retiro_total
        salidas = {"matriculado": 0.5, "no_matriculado": 0.5}
    estados = list(salidas)
    probabilidades = np.array([salidas[e] for e in estados])
    return str(rng.choice(estados, p=probabilidades / probabilidades.sum()))


def generar_historial(n_estudiantes: int, semilla: int) -> pd.DataFrame:
    """Historial sintético: una fila por estudiante y ciclo observado, todo como texto.

    Con la misma semilla produce exactamente la misma tabla.
    """
    if n_estudiantes < len(HISTORIALES_FIJOS):
        raise ValueError(f"Se necesitan al menos {len(HISTORIALES_FIJOS)} estudiantes.")
    rng = np.random.default_rng(semilla)
    codigos = rng.choice(10**8, size=n_estudiantes, replace=False)
    codigos[0] = 12345  # garantiza un código con ceros a la izquierda: 00012345
    fijos = list(HISTORIALES_FIJOS.values())

    filas: list[dict[str, str]] = []
    for i, codigo in enumerate(codigos):
        cohorte = COHORTES[0] if i < len(fijos) else str(rng.choice(COHORTES))
        riesgo = float(rng.normal())
        puntaje = float(np.clip(rng.normal(60 - 6 * riesgo, 12), 0, 100))
        beca = bool(rng.random() < 0.2)
        colegio = "publico" if rng.random() < 0.55 + 0.1 * riesgo else "privado"
        ingreso = str(rng.choice(["bajo", "medio", "alto"], p=[0.4, 0.4, 0.2]))
        observados = ciclos_observados(cohorte)

        estado = "matriculado"
        for ciclo in range(1, observados + 1):
            if i < len(fijos):
                if ciclo > len(fijos[i]):
                    break
                estado = fijos[i][ciclo - 1]
            elif ciclo > 1:
                estado = _siguiente_estado(estado, riesgo, rng)
            cursa = estado == "matriculado"
            fila = {
                "codigo_estudiante": f"{int(codigo):08d}",
                "origen_datos": ORIGEN,
                "cohorte": cohorte,
                "ciclo": str(ciclo),
                "fecha_registro": _fecha_ciclo(cohorte, ciclo).isoformat(),
                "estado_matricula": estado,
                "puntaje_admision": f"{puntaje:.1f}",
                "promedio_ciclo": (
                    f"{float(np.clip(rng.normal(13 - 1.5 * riesgo, 2.5), 0, 20)):.2f}"
                    if cursa
                    else ""
                ),
                "creditos_aprobados_ciclo": (
                    str(int(np.clip(rng.normal(18 - 3 * riesgo, 4), 0, 30))) if cursa else ""
                ),
                "beca_al_ingreso": "true" if beca else "false",
                "deuda_vencida_ciclo": (
                    ("true" if rng.random() < 0.15 + 0.08 * riesgo else "false") if cursa else ""
                ),
                "tipo_colegio": colegio,
                "rango_ingreso_familiar": ingreso if ciclo >= 1 and rng.random() > 0.05 else "",
                "horas_plataforma_ciclo": (
                    f"{float(np.clip(rng.normal(80 - 20 * riesgo, 25), 0, 500)):.1f}"
                    if cursa
                    else ""
                ),
            }
            filas.append(fila)
            if estado == "traslado":
                break
    return pd.DataFrame(filas, columns=list(COLUMNAS), dtype="object")


def sembrar_problemas(tabla: pd.DataFrame) -> tuple[pd.DataFrame, ProblemasSembrados]:
    """Copia de la tabla con cuatro problemas de calidad en filas conocidas."""
    copia = tabla.copy()
    nula, fuera, invalida = 1, 2, 3
    copia.loc[nula, "puntaje_admision"] = ""
    copia.loc[fuera, "puntaje_admision"] = "150.0"
    copia.loc[invalida, "creditos_aprobados_ciclo"] = "doce"
    duplicada = copia.iloc[[0]]
    copia = pd.concat([copia, duplicada], ignore_index=True)
    return copia, ProblemasSembrados(
        fila_nula_obligatoria=nula + 1,
        fila_fuera_de_rango=fuera + 1,
        fila_tipo_invalido=invalida + 1,
        fila_duplicada=len(copia),
    )
