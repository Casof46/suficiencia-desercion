# Pruebas del hito F4.3

Con F4.3, el proyecto tiene 419 funciones de prueba que, con sus parámetros, suman 945 casos: 909 hasta F4.1 y 36 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones son ficticias. Ningún resultado es una conclusión sobre estudiantes reales ni sobre el método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

El ensayo completo (generar el dataset, prepararlo y recorrer el método en demostración) se ejecuta con `workspace\tareas\verificar_f43.cmd`. Tarda unos 10 minutos en Linux y no forma parte de `verificar.py`.

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Requisito o prueba de la especificación |
| --- | --- | --- |
| `tests/integration/test_ensayo_oe3.py` (12 funciones, 27 casos) | El preprocesamiento admite una categórica entre numéricas, con los dos perfiles (D-203). La conversión arma una fila por estudiante y ciclo: valor a o(T0) en todas las filas para las variables desde T0, valor a o(Tk) en la fila del ciclo k, `retiro_total`, enteros sin decimales y rechazo de datos incoherentes. El historial se escribe con fin de línea LF en cualquier sistema (D-208). Las huellas detectan archivos faltantes o distintos, y el script no escribe nada en ese caso ni fuera de `data/`. La comparación de etiquetas mira solo las cohortes de desarrollo. El diccionario tiene las 40 variables (A 15, F 9, S 9, B 7). Las configuraciones del ensayo son ficticias y coherentes: 28 escenarios factibles, una lectura por variable y la partición del generador. El objetivo del ensayo coincide con el generador en 14 de sus casos especiales, y las 2 diferencias conocidas quedan fijadas | PI-01, PI-08 (fuga temporal), RF-M1-06, RF-M2-03, RNF-19 |
| `tests/architecture/test_privacidad_repositorio.py` (9 casos nuevos) | `data/oe3/`, el historial del ensayo y su reporte no se versionan; el generador, el script y las configuraciones del ensayo sí | PA-04 |
| `tests/integration/test_entrenamiento.py`, `test_evaluacion_final.py`, `test_preparacion_desarrollo.py` (modificadas) | Copian solo los `.yaml` de `config/ejemplos/`, sin la subcarpeta `oe3/` | — |

## 3. Criterios de aceptación de F4.3

| Criterio (plan de la Fase 4) | Cómo se comprueba |
| --- | --- |
| Traer o regenerar el dataset del OE3 y comprobar sus huellas antes de usarlo | `test_las_huellas_*`, `test_el_script_no_usa_archivos_con_otras_huellas`; ejecución en `verificar_f43.cmd` |
| Diccionario y configuraciones ficticias para sus 40 variables y 12 cohortes | `test_el_diccionario_del_ensayo_*`, `test_las_configuraciones_del_ensayo_*` |
| El método completo en demostración | `evaluacion demostracion` con los 28 escenarios factibles en `verificar_f43.cmd` |
| Supuestos documentados como EJEMPLO FICTICIO, sin cerrar DP-01 | `decisiones_f4_3.md`; `test_diferencias_conocidas_entre_el_motor_y_el_generador` |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 944 casos pasan y 1 se omite (fuera de un repositorio git; en Windows, la prueba del enlace simbólico).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| El preprocesamiento vuelve a poner primero las numéricas y después las categóricas | `test_el_preprocesamiento_admite_categoricas_entre_numericas` | Detectado |
| El script no comprueba las huellas | `test_el_script_no_usa_archivos_con_otras_huellas` | Detectado |
| La conversión no marca el retiro total | `test_la_conversion_arma_una_fila_por_estudiante_y_ciclo` | Detectado |
| La fila del ciclo k lleva el valor de la ventana siguiente (fuga temporal) | `test_la_conversion_arma_una_fila_por_estudiante_y_ciclo` | Detectado |
| La comparación de etiquetas incluye la prueba | `test_la_concordancia_solo_mira_las_cohortes_de_desarrollo` | Detectado |
| Objetivo del ensayo: el reingreso anula el evento | `test_el_objetivo_del_ensayo_coincide_con_el_generador_en_sus_casos` | Detectado |
| Objetivo del ensayo: las reservas cuentan como ausencia | `test_el_objetivo_del_ensayo_coincide_con_el_generador_en_sus_casos` | Detectado |
| Experimentos del ensayo: una variable desde T1 leída con `primer_registro` | `test_las_configuraciones_del_ensayo_son_ficticias_y_coherentes` | Detectado |
| El historial se escribe con fin de línea CRLF | `test_el_historial_se_escribe_igual_en_cualquier_sistema` | Detectado |

Cada cambio se revirtió después de comprobarlo; con todo restituido, las 27 pruebas del ensayo pasan.
