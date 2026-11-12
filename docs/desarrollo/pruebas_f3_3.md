# Pruebas del hito F3.3

Con F3.3, el proyecto tiene 336 funciones de prueba, que con sus parámetros suman 733 casos: 698 hasta F3.2 y 35 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones son ficticias. Las métricas que producen las pruebas reflejan los supuestos del generador, no resultados del método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows), después de entrenar con `experimentos entrenar`:

```powershell
.venv\Scripts\suficiencia experimentos metricas --experimentos config\ejemplos\experimentos_ficticio.yaml
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_metricas.py` (11 funciones, 30 casos) | AUC-ROC y Brier coinciden con scikit-learn en vectores con empates (propiedad con hypothesis); Accuracy, Precision, Recall y F1 con umbral coinciden con scikit-learn; Brier escalado respecto de la prevalencia; Recall@q con y sin empates; entradas inválidas; el intervalo contiene el valor puntual, se reproduce con la misma semilla, cambia con otra y se ensancha al subir el nivel, con las tres estratificaciones; la estratificación conserva el tamaño de cada grupo; la diferencia pareada usa los mismos estudiantes en cada réplica, vale cero contra sí misma y orienta el Brier para que mayor sea mejor; DP-08a, DP-08e y DP-08i obligatorias; estructuras inválidas | PU-07, PU-20, PU-24 |
| `tests/integration/test_entrenamiento.py` (3 funciones nuevas) | El servicio calcula, para cada corrida registrada, filas, eventos, prevalencia y métricas que coinciden con scikit-learn sobre el archivo de predicciones, con el valor dentro del intervalo; el cálculo queda registrado y se reproduce; se rechazan predicciones modificadas y escenarios sin corridas; línea de comandos | RF-M4-01, RF-M4-03 |
| `tests/unit/test_experimentos.py` (1 función nueva) | El ejemplo declara métricas e intervalos; un `null` detiene con DP-08a o DP-08e | DP como datos |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `experimentos metricas` | PA-02 |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | El módulo de métricas debe versionarse | PA-04 |

## 3. Criterios de aceptación de F3.3

| Criterio (plan de la Fase 3) | Cómo se comprueba |
| --- | --- |
| AUC-ROC, Brier, Recall@q y las secundarias | PU-07 |
| Prevalencia junto a cada métrica | Servicio y línea de comandos |
| Bootstrap pareado | PU-20, PU-24 |
| Diferencias | PU-24 |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 732 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 733.

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| AUC-ROC sin promediar los empates | `test_pu07_auc_y_brier_coinciden_con_scikit_learn` | Detectado |
| Bootstrap sin semilla | `test_pu20_*` | Detectado |
| La referencia se evalúa siempre sobre todos los estudiantes, sin parearla con la réplica | `test_pu24_*` | Detectado |
| El Brier sin invertir el signo | `test_pu24_*` | Detectado |
| El bootstrap ignora la estratificación | `test_la_estratificacion_conserva_el_tamano_de_cada_grupo` | Detectado |
| No se comprueba la huella de las predicciones | `test_metricas_rechazan_*` | Detectado |

La primera versión del control de pares (invertir el orden de las réplicas de la referencia) no se detectó porque no altera ninguna métrica: invertir el orden no cambia qué estudiantes entran. Se reemplazó por un defecto real.
