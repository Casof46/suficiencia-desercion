# Pruebas del hito F3.1

Con F3.1, el proyecto tiene 305 funciones de prueba, que con sus parámetros suman 645 casos: 600 hasta H2.8 y 45 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones son ficticias. Los conteos que muestran las pruebas reflejan los supuestos del generador, no resultados del método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows), con un historial ampliado generado antes:

```powershell
.venv\Scripts\python scripts\generar_sintetico.py --semilla 7 --estudiantes 1200 --ampliado --salida data\sintetico\ampliado.csv
.venv\Scripts\suficiencia experimentos preparar data\sintetico\ampliado.csv --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --poblaciones config\ejemplos\poblaciones_ampliado_ficticio.yaml --escenarios config\ejemplos\escenarios_ficticio.yaml --experimentos config\ejemplos\experimentos_ficticio.yaml --clave-efimera
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_matrices.py` (9 funciones, 9 casos) | `ultimo_ciclo` lee el periodo índice y `primer_registro` la admisión; sin registro en el periodo índice el valor queda faltante; cambiar cualquier valor posterior al periodo índice no cambia los predictores (propiedad con hypothesis); una variable posterior a la ventana se rechaza como fuga; `primer_registro` solo para variables de T0; un escenario no factible no se construye; los no etiquetables nunca entran, aunque una población los trajera; DP-03 obligatoria | PU-12; fuga temporal (RF-M2-04) |
| `tests/unit/test_experimentos.py` (8 funciones, 24 casos) | El ejemplo es ficticio y se lee completo; sin `config/experimentos.yaml` se detiene con DP-07; folds del ejemplo como en el informe del OE3; esquema deslizante; para cualquier combinación válida, la validación es posterior a ajuste y calibración y los papeles no se cruzan (propiedad con hypothesis); un `null` detiene con DP-07, DP-03 o DP-12; estructuras inválidas se rechazan | PI-07 (folds) |
| `tests/integration/test_preparacion_desarrollo.py` (7 funciones, 7 casos) | Las matrices solo tienen cohortes de desarrollo y alterar las filas de la prueba no cambia nada; la mediana del imputador y la media del escalador son las del ajuste de cada fold y no las de todos los datos; el servicio ajusta cada perfil solo con las filas de ajuste de los mismos folds en todos los escenarios; las columnas fuera del ajuste coinciden aunque aparezca una categoría nueva; DP-07 sin configuración; D3 como diseño principal se rechaza; línea de comandos | PI-01, PI-08 (cohortes por fold) |
| `tests/unit/test_datos_sinteticos.py` (1 función nueva) | El historial ampliado tiene 12 cohortes, cada fila es sintética, ninguna unidad tiene más ciclos que los observables y el historial por omisión no cambia; con 1500 estudiantes no falla | D-128 |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `experimentos preparar`; los demás comandos siguen sin cargar scikit-learn | PA-02, D-134 |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | Los ejemplos ficticios nuevos, el preprocesamiento y el plan de la Fase 3 deben versionarse | PA-04 |
| `tests/architecture/test_alcance_h2_0.py` (modificada) | scikit-learn y joblib ya no figuran como postergadas | D-127 |

## 3. Criterios de aceptación de F3.1

| Criterio (plan de la Fase 3) | Cómo se comprueba |
| --- | --- |
| Generador sintético ampliado | `test_datos_sinteticos.py` |
| Matrices por ventana y escenario solo con desarrollo | `test_matrices.py`; `test_las_matrices_solo_tienen_desarrollo_y_la_prueba_no_influye` |
| Folds rolling-origin por cohortes, DP-07 como datos | `test_experimentos.py` |
| Preprocesamiento ajustado dentro de cada fold, DP-12 como datos | `test_pi01_*` |
| PI-01, PI-07 (folds), PI-08 (cohortes por fold), PU-12 | Tabla de la sección 2 |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 644 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 645.

## 4. Controles negativos realizados

Cada defecto se introdujo a propósito, se ejecutaron las pruebas indicadas y se restauró el código.

| Cambio introducido a propósito | Pruebas | Resultado |
| --- | --- | --- |
| `ultimo_ciclo` lee el último registro de la unidad, aunque sea posterior al periodo índice | `test_matrices.py` | Detectado |
| La matriz deja de descartar los no etiquetables | `test_matrices.py` | Detectado (la primera versión no lo detectaba; se agregó la prueba con un no etiquetable en la población) |
| La cohorte de validación entra también en el ajuste | `test_experimentos.py` | Detectado |
| El servicio ajusta el preprocesamiento con todas las filas de la matriz | `test_preparacion_desarrollo.py` | Detectado |
| El desarrollo deja de descartar las cohortes de prueba antes de etiquetar | `test_preparacion_desarrollo.py` | Detectado |
| Se quita el rechazo de D3 como diseño principal | `test_preparacion_desarrollo.py` | Detectado |
