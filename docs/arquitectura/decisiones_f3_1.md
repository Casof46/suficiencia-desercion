# Decisiones técnicas del hito F3.1 — datos listos para entrenar sin fuga

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx: cada valor que depende de una DP-xx abierta entra como dato obligatorio, con un ejemplo rotulado "EJEMPLO FICTICIO" en `config/ejemplos/`. Continúan la numeración de `decisiones_h2_8.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-127 | Se agrega scikit-learn (1.9.1) como dependencia del motor, con joblib, scipy y threadpoolctl como dependencias suyas, fijadas en `requirements.lock` con hashes y `--exclude-newer 2026-10-28` (regla de dos semanas de D-92). Se quitan de la lista de bibliotecas postergadas de la prueba de alcance de H2.0 | Escribir el preprocesamiento a mano con pandas | El plan de la Fase 3 la asigna a F3.1 (RF-M3-02). Sus imputadores y escaladores separan el ajuste de la transformación, que es justo lo que exige PI-01 | Aplicada |
| D-128 | El generador sintético puede producir un historial **ampliado** de 12 cohortes (2010-1 a 2015-2), con `--ampliado` en `scripts/generar_sintetico.py`. El historial por omisión no cambia. Se corrige un defecto: con muchos estudiantes, la probabilidad de reingreso podía pasar de 1 y el generador fallaba; ahora se limita a 1 | Cambiar las cohortes por omisión | Con 8 cohortes, la partición de ejemplo deja muy pocas cohortes de desarrollo para folds cronológicos. Cambiar el historial por omisión rompería las pruebas de la Fase 2 | Aplicada |
| D-129 | Matrices por escenario (`domain/escenarios/matrices.py`): una fila por unidad etiquetable de la población del diseño principal en la ventana; corte en el periodo índice (nada posterior entra); la lectura de cada variable es un dato obligatorio (DP-03, DP-15): `primer_registro` (solo variables disponibles desde T0) o `ultimo_ciclo` (el registro del periodo índice; si no existe, queda faltante y nunca se toma uno posterior). Una variable sin lectura detiene el programa con DP-03 | Promedios acumulados u otras agregaciones; tomar el último registro disponible | Son las dos lecturas que el diccionario sintético permite sin inventar reglas. Otras agregaciones son decisiones de DP-03 y se agregan cuando se decidan | Aplicada |
| D-130 | Folds rolling-origin por cohortes (`domain/experimentos.py`): esquema expansivo o deslizante, cohortes iniciales, cohorte de calibración opcional (la inmediatamente anterior a la de validación) y ancho del deslizante, todos obligatorios (DP-07). Los folds dependen solo de las cohortes de desarrollo, así que todos los escenarios usan los mismos (PI-08) | Folds por fechas o por proporción de filas | RF-M3-03 pide validación cronológica por cohortes. El ejemplo ficticio (expansivo, 2 iniciales, con calibración) da los 6 folds de la base de trabajo del informe del OE3; no es una recomendación | Aplicada |
| D-131 | mypy ignora la falta de tipos de scikit-learn (`ignore_missing_imports` solo para `sklearn`) | Escribir stubs propios | scikit-learn no publica tipos. El resto del código sigue en modo estricto | Aplicada |
| D-132 | Perfiles de preprocesamiento con nombre (DP-12): imputación numérica (mediana o media), indicador de faltante, escalado (estándar o ninguno) e imputación categórica (más frecuente o categoría "faltante") con codificación one-hot que ignora categorías nuevas. Se ajustan solo con las filas de ajuste de cada fold y luego transforman calibración y validación sin reajustarse (PI-01). Los tipos se toman de la matriz: texto es categórico; número o sí/no, numérico | Un único preprocesamiento para todos los modelos | Cada familia de modelos puede necesitar otro (por ejemplo, los árboles no necesitan escalado). El ejemplo trae dos perfiles ficticios, "lineal" y "arboles" | Aplicada |
| D-133 | `suficiencia experimentos preparar` (servicio `ServicioExperimentos.preparar_desarrollo`): lee el historial, **descarta las cohortes que no son de desarrollo antes de etiquetar**, construye la población, los escenarios (con su verificación anti-fuga), las matrices y los folds, ajusta cada perfil en cada fold e informa filas, eventos y columnas resultantes. No entrena ni escribe en el registro. Sin `--experimentos` busca `config/experimentos.yaml`, que no existe, y se detiene con DP-07 | Etiquetar todo y filtrar después | Si las unidades de la prueba ni se etiquetan, nada de la prueba puede filtrarse al desarrollo. Preparar es una verificación previa; las corridas registradas llegan con el entrenamiento (F3.2) | Aplicada |
| D-134 | scikit-learn se importa solo al preparar el desarrollo (importación diferida en `composicion.py`). Los demás comandos siguen sin cargarlo, y la prueba de cp1252 lo comprueba antes de ejecutar `experimentos preparar` | Importarlo al arrancar | Mantiene el arranque rápido de la línea de comandos y la comprobación de bibliotecas prohibidas de la Fase 2 | Aplicada |
| D-135 | Con D3 como diseño principal, preparar se detiene: D3 mide cobertura sobre la cohorte de admisión y no define una población de entrenamiento | Entrenar con D1 en su lugar sin avisar | Cómo entrenar con D3 depende de DP-04 y DP-17, que siguen abiertas | Aplicada |

## Desviaciones respecto de la documentación anterior

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 3, F3.1 | Pruebas PI-01, PI-07 (folds), PI-08 (cohortes por fold) y PU-12 | Las cuatro, más una prueba de que alterar las filas de la prueba no cambia nada del desarrollo | Refuerza la regla 4 del plan (la prueba sigue sellada) |
| `docs/desarrollo/entorno_reproducible.md` | Comando de bloqueo sin `--extra ui` ni `--exclude-newer` | Se actualiza con ambos | Es el comando que realmente produce el bloqueo vigente |

## No implementado en F3.1

- Modelos, búsqueda de hiperparámetros, desbalance y calibración (F3.2).
- Métricas (F3.3) y cualquier selección (F3.4).
- Valores reales de DP-03, DP-07 o DP-12.
