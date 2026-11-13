# Registro del hito F4.1 — reportes desde el registro y comparación de escenarios

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aprobar el plan de la Fase 4 |
| Base | Plan de la Fase 4 (sección 3, F4.1); especificación Fase 1 v0.6 (RF-M6-07, RF-M4-10, RF-M4-14; RNF-19; PI-16) |
| Autorización | El equipo aprobó el plan de la Fase 4 y pidió empezar por F4.1 el 12 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier). La asesoría no se ha pronunciado sobre ese plan |
| Riesgo aceptado | Si la asesoría cambia el formato del reporte comparativo, se ajusta |
| Estado del hito | **Ejecutado y verificado en Linux.** Pendiente: verificación en Windows, commit del equipo y aceptación |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/application/servicio_evaluacion_final.py` | La comparación guarda su resultado completo; lectura de la evaluación, su comparación y su explicación desde el registro (D-195, D-196) |
| `src/suficiencia/application/reporte_resultados.py`, `servicio_reportes.py` | Reporte sin comparación; reporte de los escenarios en validación (D-197, D-198) |
| `src/suficiencia/application/servicio_experimentos.py`, `contratos.py` | Ventana, conjunto y origen de los datos en las métricas (D-199) |
| `src/suficiencia/cli.py` | `suficiencia evaluacion reporte` y `experimentos metricas --reporte` |
| `src/suficiencia/ui/graficos.py`, `visor.py` | Página "Escenarios en validación" (D-200) |
| Pruebas y documentación | `pruebas_f4_1.md`, `decisiones_f4_1.md`, este registro |

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 908 pasan y 1 se omite (sin git) |
| Windows 11 | Pendiente |

La página de validación se revisó en Linux con Chromium, con 25 corridas de 5 escenarios entrenadas en un proyecto temporal.

## 4. Matriz de criterios de aceptación de F4.1

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Reporte comparativo de una evaluación registrada | Cumplido en Linux | `test_evaluacion_final.py`, `test_exportacion_resultados.py` |
| 2 | Escenarios por ventana y conjunto (tabla y gráfico) | Cumplido en Linux | `test_reporte_resultados.py`, `test_visor.py` |
| 3 | Los cinco modelos de cada escenario en el reporte y en el visor | Cumplido en Linux | `test_reporte_resultados.py`, `test_visor.py` |
| 4 | Verificación en Windows antes del commit | Pendiente | — |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | Pendiente | |
| Jorge | Pendiente | |
