# Pruebas del hito F3.2

Con F3.2, el proyecto tiene 321 funciones de prueba, que con sus parámetros suman 698 casos: 645 hasta F3.1 y 53 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones son ficticias. Las probabilidades que producen las pruebas reflejan los supuestos del generador, no resultados del método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows), con el historial ampliado de F3.1, solo un escenario y una familia:

```powershell
.venv\Scripts\suficiencia experimentos entrenar data\sintetico\ampliado.csv --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --poblaciones config\ejemplos\poblaciones_ampliado_ficticio.yaml --escenarios config\ejemplos\escenarios_ficticio.yaml --experimentos config\ejemplos\experimentos_ficticio.yaml --clave-efimera --escenario "T1|A+F" --familia lr
.venv\Scripts\suficiencia registro ver experimentos
```

Sin `--escenario` ni `--familia` se entrenan los 28 escenarios con las cinco familias.

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/integration/test_entrenamiento.py` (10 funciones, 19 casos) | Cada una de las cinco familias da una probabilidad entre 0 y 1 por fila de validación en cada fold; la búsqueda elige, entre las combinaciones declaradas, la de mejor puntaje en la cohorte de calibración (recalculado con modelos nuevos); el desbalance de XGBoost es negativos / positivos del ajuste del fold y las demás familias usan pesos balanceados; la calibración Platt o isotónica no vuelve a ajustar el modelo; dos ejecuciones iguales dan exactamente las mismas probabilidades en las cinco familias; un hiperparámetro inexistente se rechaza; el servicio registra 10 corridas exploratorias con semillas, versiones de las bibliotecas y archivos cuyas huellas coinciden, sin seudónimos ni cohortes de prueba en las predicciones; mismas combinaciones y folds por familia en dos escenarios; al repetir, se omiten las corridas completas; una corrida que falla queda registrada junto a la exitosa y se reintenta al repetir; escenarios no factibles, inexistentes y familias desconocidas se rechazan; línea de comandos con código 0 y con código 1 si una corrida falla | PI-06, PI-08 (búsqueda), PI-11, PI-12; RF-M3-04 a 09, 11 |
| `tests/unit/test_experimentos.py` (6 funciones nuevas, 30 casos) | El ejemplo declara las cinco familias, la búsqueda, el desbalance, la calibración y la semilla; las combinaciones dependen solo de la familia, la búsqueda y la semilla (malla completa en orden estable; aleatoria reproducible); un `null` detiene con DP-06, DP-07, DP-09 o DP-12; estructuras inválidas se rechazan (faltan familias, parámetros reservados, perfil inexistente, valores repetidos, semilla inválida, búsqueda o calibración sin cohorte de calibración) | RF-M3-04, RF-M3-06; DP como datos |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `experimentos entrenar` (un escenario, una familia); los demás comandos siguen sin cargar scikit-learn, XGBoost ni LightGBM | PA-02, D-147 |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | Los modelos y las predicciones en `workspace/experimentos/` quedan ignorados por git; los módulos nuevos deben versionarse | PA-04 |
| `tests/architecture/test_alcance_h2_0.py` (modificada) | XGBoost y LightGBM ya no figuran como postergadas | D-136 |

## 3. Criterios de aceptación de F3.2

| Criterio (plan de la Fase 3) | Cómo se comprueba |
| --- | --- |
| Fábrica de LR, RF, XGBoost, LightGBM y SVM | `test_pi06_*` |
| Búsqueda con espacio y presupuesto como datos (DP-07) | `test_la_busqueda_*`, `test_pi08_*`, servicio |
| Desbalance dentro del fold (DP-06) | `test_rf_m3_05_*` |
| Calibración (DP-09) | `test_rf_m3_09_*` |
| Semillas | `test_pi11_*`, semillas en el registro |
| Corridas registradas | `test_servicio_*`, `test_pi12_*` |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 697 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 698.

## 4. Controles negativos realizados

Cada defecto se introdujo a propósito, se ejecutó la prueba indicada y se restauró el código.

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| La búsqueda se queda con la peor combinación | `test_la_busqueda_elige_la_mejor_combinacion_en_la_cohorte_de_calibracion` | Detectado |
| El peso de desbalance se calcula con todas las filas de la matriz | `test_rf_m3_05_*` | Detectado |
| La calibración vuelve a ajustar el modelo con la cohorte de calibración | `test_rf_m3_09_*` | Detectado |
| Random Forest sin semilla | `test_pi11_*` | Detectado |
| Las corridas completas no se omiten al repetir | `test_servicio_registra_guarda_archivos_y_reanuda` | Detectado |
| Una corrida fallida detiene el lote | `test_pi12_*` | Detectado |

PI-08 para la búsqueda aleatoria se garantiza por diseño: `combinaciones_a_evaluar` no recibe el escenario ni el fold, y la prueba unitaria comprueba que la misma semilla da las mismas combinaciones.
