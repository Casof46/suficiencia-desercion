# Registro del hito F4.2: estabilidad descriptiva y referente R-max

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 13 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F4.3 |
| Base | Plan de la Fase 4 (sección 3, F4.2); especificación Fase 1 v0.6 (RF-M4-22, RF-M5-06, RF-M4-16 con R-max; CMP-5; DP-19d; DP-20g) |
| Autorización | El equipo pidió empezar F4.2 el 13 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier). La asesoría no se ha pronunciado sobre el plan de la Fase 4 |
| Riesgo aceptado | RF-M4-22 y R-max dependen de DP-20 y DP-19d: entran como datos opcionales, apagados por omisión |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `00ede20`); aceptado por el equipo** el 13 de noviembre de 2026, con la desviación de comparar las explicaciones solo entre folds (comunicado por Jorge; pendiente de confirmación de Javier) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/evaluacion/estabilidad.py` | Regla por fold y conteos; correlación de rangos y proporciones por bloque (D-209, D-212) |
| `src/suficiencia/domain/evaluacion/comparacion.py` | `referencia.r_max` y elección de R-max; `comparacion.estabilidad` (D-211, D-213) |
| `src/suficiencia/domain/evaluacion/interpretabilidad.py` | `interpretabilidad.estabilidad: ninguna \| folds` (D-212) |
| `src/suficiencia/application/servicio_evaluacion_final.py` | `estabilidad`: regla por fold y métricas de prueba por cohorte, sin abrir la prueba (D-209, D-210) |
| `src/suficiencia/application/servicio_experimentos.py` | Construcción de R-max al seleccionar (D-213) |
| `src/suficiencia/application/servicio_interpretabilidad.py` | SHAP de los modelos de cada fold y comparación con el congelado (D-212) |
| `src/suficiencia/application/contratos.py`, `reporte_resultados.py`, `servicio_reportes.py`, `demostracion_final.py`, `cli.py` | Contratos, tablas del reporte, paso 11 de la demostración y `suficiencia evaluacion estabilidad` |
| `config/ejemplos/experimentos_ficticio.yaml`, `experimentos_estabilidad_ficticio.yaml` | Las tres funciones apagadas y encendidas (D-214) |
| `workspace/tareas/verificar_f42.cmd` | Verificación en Windows |
| Pruebas y documentación | `test_estabilidad.py`, `test_estabilidad_demostracion.py`, `pruebas_f4_2.md`, `decisiones_f4_2.md`, este registro |

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 956 pasan y 1 se omite (sin git). Demostración con `experimentos_estabilidad_ficticio.yaml`, T1\|A+F y T0\|A en el historial ampliado: R-max construido (T1\|A+F, rf), congelado y evaluado en el único acceso a la prueba; estabilidad de la selección en los 6 folds (T1\|A+F cumple en 3 y la regla lo elige en 2; T0\|A cumple en 1 y es elegido en 1); explicaciones comparadas con los modelos de los 6 folds; reporte rotulado en `reports/estabilidad_f42_linux` |
| Windows 11, Python 3.13.0 (13 de noviembre de 2026) | Cinco `OK`; 6 contratos cumplidos; 956 pasan y 1 se omite (el sistema no permite crear enlaces simbólicos). Demostración con las tres funciones encendidas: R-max (T1\|A+F, rf) construido y evaluado en el único acceso a la prueba; estabilidad de la selección en los 6 folds (T1\|A+F cumple en 3 y es elegido en 2; T0\|A cumple en 1 y es elegido en 1); explicaciones comparadas con los modelos de los folds; reporte rotulado en `reports\estabilidad_f42`. Duró 29 minutos. Evidencia: `workspace\tareas\verificar_f42.log` |

Las cifras de la demostración cambian de una ejecución a otra, porque la clave de seudonimización es aleatoria y cambia el orden de las filas. Son salidas de un ejemplo ficticio, no conclusiones.

## 4. Matriz de criterios de aceptación de F4.2

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Estabilidad de la selección por fold, sin inferencia entre cohortes | Cumplido en Linux y Windows | `test_estabilidad.py`, `test_estabilidad_demostracion.py` |
| 2 | Métricas por cohorte de prueba sin otro acceso a la prueba | Cumplido en Linux y Windows | `test_estabilidad_demostracion.py` |
| 3 | Estabilidad de las explicaciones entre folds | Cumplido en Linux y Windows | `test_estabilidad.py`, `test_estabilidad_demostracion.py` |
| 4 | Referente R-max opcional | Cumplido en Linux y Windows | `test_estabilidad.py`, `test_estabilidad_demostracion.py` |
| 5 | Apagadas por omisión | Cumplido en Linux y Windows | `test_las_funciones_de_f42_estan_apagadas_por_omision` |
| 6 | Verificación en Windows antes del commit | Cumplido | `verificar_f42.log` |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. DP-19d y DP-20g siguen abiertas: las funciones que dependen de ellas solo se encienden en ejemplos ficticios.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | Pendiente de confirmación | |
| Jorge | 13 de noviembre de 2026 | Acepta F4.2, con la estabilidad de las explicaciones solo entre folds, y pide empezar F4.4 |
