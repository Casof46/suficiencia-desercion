# Pruebas del hito F4.1

Con F4.1, el proyecto tiene 407 funciones de prueba, que con sus parámetros suman 909 casos: 903 hasta F3.7 y 6 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones son ficticias. Ningún resultado es una conclusión sobre estudiantes reales ni sobre el método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Requisito o prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_reporte_resultados.py` (3 funciones nuevas) | Un reporte sin comparación lo dice y no tiene sus tablas; el reporte de validación lleva el rótulo, una matriz ventana × conjunto por familia con la primera métrica declarada, «·» donde no hay corrida, todas las corridas en su tabla y sus limitaciones; los gráficos de validación llevan el rótulo y dibujan los valores registrados, sin rellenar celdas vacías | RF-M4-10, RF-M4-14, PI-16 |
| `tests/integration/test_evaluacion_final.py` (modificada) | Lo leído del registro (evaluación, comparación y última explicación) coincide con lo que devolvieron los servicios al ejecutarse, y produce el mismo reporte; cada evaluación cuenta los accesos hasta ella; una evaluación sin comparación se reporta indicándolo; `evaluacion reporte` exporta el reporte rotulado; un identificador que no es una evaluación final se rechaza | RF-M6-07, PI-16 |
| `tests/integration/test_entrenamiento.py` (modificada) | Las métricas traen la ventana, el conjunto y el origen de los datos; `experimentos metricas --reporte` exporta el reporte rotulado de los escenarios | RF-M4-10, RF-M4-14, PI-16 |
| `tests/integration/test_exportacion_resultados.py` (1 función nueva) | Una evaluación sin comparación ni explicación se lee del registro; una comparación registrada sin su resultado completo pide repetirla | RF-M6-07 |
| `tests/integration/test_visor.py` (1 función y 1 caso nuevos) | La página "Escenarios en validación" se ejecuta con el aviso; con corridas registradas muestra la matriz y las familias con el rótulo, y las dos descargas | RF-M4-10, RF-M4-14, PI-16 |

## 3. Criterios de aceptación de F4.1

| Criterio (plan de la Fase 4) | Cómo se comprueba |
| --- | --- |
| Reporte comparativo de una evaluación registrada | `test_evaluacion_final.py`, `test_exportacion_resultados.py` |
| Tabla y gráfico de escenarios por ventana y conjunto | `test_reporte_resultados.py`, `test_visor.py` |
| Los cinco modelos de cada escenario en validación, en el reporte y en el visor | `test_reporte_resultados.py`, `test_visor.py`, `test_entrenamiento.py` |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 908 casos pasan y 1 se omite fuera de un repositorio git (en Windows, se omite la prueba del enlace simbólico).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| La comparación no guarda su resultado completo | `test_evaluacion_final.py` | Detectado |
| Accesos contados hasta hoy y no hasta la evaluación | `test_evaluacion_final.py` | Detectado |
| Se lee la primera comparación en lugar de la última | `test_evaluacion_final.py` | Detectado |
| La matriz mezcla familias | `test_reporte_resultados.py` | Detectado |
| Reporte de validación sin la leyenda | `test_reporte_resultados.py` | Detectado |
| Celda sin corrida rellenada con cero | `test_reporte_resultados.py` | Detectado |
