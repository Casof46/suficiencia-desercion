# Pruebas del hito F4.2

Con F4.2, el proyecto tiene 431 funciones de prueba que, con sus parámetros, suman 957 casos: 945 hasta F4.3 y 12 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones son ficticias. Ningún resultado es una conclusión sobre estudiantes reales ni sobre el método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Requisito o prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_estabilidad.py` (7 funciones) | La regla se aplica en cada fold y se cuentan los folds evaluables, los que cumplen y los elegidos; sin folds, o con escenarios distintos entre folds, se rechaza. Spearman usa rangos (con empates promediados) y no está definida con menos de dos variables o importancias constantes. Las proporciones por bloque suman 1. R-max elige el mejor valor según el sentido de la métrica y desempata por escenario y familia. Las tres funciones están apagadas por omisión y sus valores se validan | RF-M4-22, RF-M5-06, RF-M4-16 (R-max), PU-23 |
| `tests/integration/test_estabilidad_demostracion.py` (5 funciones) | Con las funciones encendidas, la demostración construye R-max, lo congela, lo evalúa en el mismo acceso a la prueba y lo incluye en la comparación descriptiva. La estabilidad de la selección cubre los 6 folds de desarrollo (nunca una cohorte de prueba) y elige a lo sumo un escenario por fold. Las métricas por cohorte suman las filas y eventos de cada configuración, sin otro acceso a la prueba. Cada configuración trae la estabilidad de sus explicaciones en los 6 folds. El reporte rotulado incluye las tablas nuevas. Con la función apagada, el servicio y la línea de comandos se niegan | RF-M4-22, RF-M5-06, RF-M4-16, PI-15, PI-16 |
| `tests/integration/test_evaluacion_final.py` (modificada) | Con la configuración de ejemplo, la demostración no construye R-max ni describe la estabilidad | D-211, D-214 |

## 3. Criterios de aceptación de F4.2

| Criterio (plan de la Fase 4) | Cómo se comprueba |
| --- | --- |
| Estabilidad de la selección por fold de desarrollo, sin inferencia entre cohortes | `test_estabilidad.py`, `test_estabilidad_demostracion.py` |
| Métricas por cohorte de prueba sin abrir de nuevo la prueba | `test_estabilidad_demostracion.py` |
| Estabilidad de las explicaciones entre folds | `test_estabilidad.py`, `test_estabilidad_demostracion.py` |
| Referente R-max opcional | `test_estabilidad.py`, `test_estabilidad_demostracion.py` |
| Funciones sujetas a decisiones abiertas, apagadas por omisión | `test_las_funciones_de_f42_estan_apagadas_por_omision`, `test_evaluacion_final.py` |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 956 casos pasan y 1 se omite (fuera de un repositorio git; en Windows, la prueba del enlace simbólico).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| Se cuentan como "cumple" todos los folds evaluables | `test_la_regla_se_aplica_en_cada_fold_y_se_cuenta` | Detectado |
| Spearman con los valores en lugar de los rangos | `test_correlacion_de_rangos` | Detectado |
| R-max desempata con el último candidato | `test_r_max_elige_el_mejor_y_desempata_por_escenario_y_familia` | Detectado |
| R-max ignora el sentido de la métrica | `test_r_max_elige_el_mejor_y_desempata_por_escenario_y_familia` | Detectado |
| CMP-5 encendida por omisión | `test_las_funciones_de_f42_estan_apagadas_por_omision` | Detectado |
| La demostración describe la estabilidad aunque esté apagada | `test_demostracion_completa_sin_tocar_el_registro_del_proyecto` | Detectado |
| Métricas por cohorte sin separar las cohortes | `test_estabilidad_de_la_seleccion_por_fold_sin_abrir_la_prueba` | Detectado |
| La regla de cada fold usa todas las filas de validación | `test_estabilidad_de_la_seleccion_por_fold_sin_abrir_la_prueba` | Detectado |

Cada cambio se revirtió después de comprobarlo.
