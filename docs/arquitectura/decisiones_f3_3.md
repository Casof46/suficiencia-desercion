# Decisiones técnicas del hito F3.3 — métricas e intervalos

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx: qué métricas se calculan (DP-08a), la capacidad de alerta q (DP-08i) y el método, nivel, réplicas y estratificación de los intervalos (DP-08e) entran como datos obligatorios, con un ejemplo rotulado "EJEMPLO FICTICIO". Continúan la numeración de `decisiones_f3_2.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-148 | Métricas propias en el dominio (`domain/evaluacion/metricas.py`), solo con NumPy: AUC-ROC (Mann-Whitney con empates a la mitad), Brier, Brier escalado (1 − Brier / Brier de predecir la prevalencia de la población evaluada), Recall@q y, con un umbral dado, Accuracy, Precision, Recall y F1. PU-07 las compara con scikit-learn | Usar scikit-learn en el dominio | El dominio no puede depender de bibliotecas de aprendizaje automático (RNF-01, contrato de import-linter) | Aplicada |
| D-149 | Recall@q: se alerta a los `floor(q·n)` estudiantes de mayor probabilidad (no más de los que la capacidad permite atender). Los empates en el límite se reparten en proporción, que es lo esperado al desempatar al azar | Redondear hacia arriba; desempatar por el orden de las filas | Redondear hacia arriba superaría la capacidad. Desempatar por orden haría depender la métrica del orden del archivo, y la calibración isotónica produce muchos empates | Aplicada |
| D-150 | Bootstrap percentil (único método por ahora, DP-08e): se remuestrean estudiantes con reemplazo dentro de cada grupo de la estratificación (cohorte × resultado, resultado o ninguna), conservando el tamaño de cada grupo, con la semilla de la configuración. Si en una réplica una métrica no está definida (por ejemplo, AUC-ROC sin positivos), esa réplica se excluye de esa métrica y se informa cuántas réplicas fueron válidas | BCa; intervalos analíticos | La especificación recomienda el bootstrap estratificado por cohorte × resultado (propuesta del manuscrito). Otros métodos se agregan si DP-08e los elige | Aplicada |
| D-151 | Diferencia pareada: Δ = métrica(evaluada) − métrica(referencia), con el signo invertido en las métricas donde menor es mejor (Brier), y las mismas réplicas de estudiantes para las dos configuraciones | Remuestrear cada configuración por separado | Las dos predicen a los mismos estudiantes y la especificación pide el bootstrap pareado (RF-M4-18, PU-24). Se usará en la comparación con R0 (F3.5) | Aplicada |
| D-152 | `suficiencia experimentos metricas`: calcula las métricas con su prevalencia e intervalo sobre las probabilidades de validación fuera de fold de todos los folds juntos, para cada corrida de entrenamiento exitosa de la configuración indicada. Comprueba la huella de cada archivo de predicciones antes de leerlo. El cálculo queda en el registro como experimento exploratorio, con las corridas usadas y la semilla del bootstrap | Calcular por fold; no registrar el cálculo | La especificación calcula la métrica de selección "sobre predicciones de validación fuera de fold". Registrar el cálculo cumple RF-M6-01 | Aplicada |
| D-153 | Las métricas con umbral (Accuracy, Precision, Recall y F1) están implementadas y probadas, pero no se informan todavía | Informarlas con un umbral de ejemplo | El umbral sale de la regla de DP-06 aplicada al modelo seleccionado, que llega en F3.4 | Aplicada |
| D-154 | Las métricas que no están definidas (una sola clase) se guardan como vacías y no como NaN | Guardar NaN | El registro se guarda como JSON, que no admite NaN | Aplicada |

## Desviaciones respecto de la documentación anterior

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 3, F3.3 | Métricas, intervalos y diferencias | Las diferencias pareadas están implementadas y probadas (PU-24), pero el comando aún no compara configuraciones | Qué se compara con qué es la evaluación comparativa de F3.5 (DP-19, DP-20) |
| Prueba de arquitectura de H2.6 | El dominio de evaluación no contiene números decimales | Se mantiene: los valores 0 y ±1 del módulo de métricas se escriben como enteros | La prueba protege contra umbrales escritos en el código |

## No implementado en F3.3

- Intercepto y pendiente de calibración, y curva de calibración (DP-09; nivel N3 salvo que DP-09 los incluya en el criterio).
- DeLong pareado (solo como sensibilidad, si se comprueban sus supuestos).
- Comparación con R0 y controles (F3.5) y selección (F3.4).
- Valores reales de DP-08a, DP-08e o DP-08i.
