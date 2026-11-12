# Pruebas del hito F3.4

Con F3.4, el proyecto tiene 354 funciones de prueba, que con sus parámetros suman 769 casos: 733 hasta F3.3 y 36 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones y protocolos son ficticios. Los resultados de la regla en las pruebas y en la demostración no son conclusiones sobre el método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Demostración manual (Windows), con el historial ampliado de F3.1:

```powershell
.venv\Scripts\suficiencia evaluacion demostracion data\sintetico\ampliado.csv --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --poblaciones config\ejemplos\poblaciones_ampliado_ficticio.yaml --escenarios config\ejemplos\escenarios_ficticio.yaml --experimentos config\ejemplos\experimentos_ficticio.yaml --protocolo config\ejemplos\protocolo_evaluacion_final_ficticio.yaml --escenario "T1|A+F"
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_seleccion.py` (11 funciones, 25 casos) | Sin margen gana la mejor familia y con margen la primera del orden; en las métricas donde menor es mejor se invierte la orientación; faltan familias o valores no definidos; umbral fijo, por cuantil (alerta a la fracción q) y por Recall mínimo (el mayor umbral que lo alcanza); DP-10, DP-06 y DP-08i obligatorias; reglas inválidas | RF-M4-07, RF-M4-08 |
| `tests/integration/test_evaluacion_final.py` (6 funciones, 6 casos) | La selección coincide con la regla aplicada a las métricas recalculadas de los archivos de predicciones y el umbral con el cuantil de la familia elegida, sin ningún acceso a la prueba; exige las cinco familias; `ultimo_fold` no usa la última cohorte; sin protocolo la evaluación final se rechaza sin abrir la prueba; una configuración cambiada se rechaza; la prueba se abre una vez para todas las configuraciones y la evaluación queda como confirmatoria; repetir sin justificación se rechaza y con justificación queda registrada; un modelo modificado se rechaza; la demostración completa no toca el registro del proyecto y su línea de comandos; la demostración exige protocolo ficticio | PI-09, PI-10, PI-15, PU-05; RF-M4-09 |
| `tests/integration/test_entrenamiento.py` (1 función nueva) | Con la raíz por otro camino que la carpeta de trabajo (enlace simbólico), los archivos de la corrida se encuentran igual | D-165 |
| `tests/architecture/test_sin_criterio_por_defecto.py` (modificada) | Los únicos protocolos en `config/` son los dos ejemplos ficticios | D-164 |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `evaluacion demostracion` | PA-02 |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | El modelo final en `workspace/seleccion/` queda ignorado por git; los archivos nuevos deben versionarse | PA-04 |

## 3. Criterios de aceptación de F3.4

| Criterio (plan de la Fase 3) | Cómo se comprueba |
| --- | --- |
| Modelo por escenario (DP-10) y umbral (DP-06) solo con validación | `test_seleccion.py`; `test_seleccion_con_validacion_*` |
| Congelamiento con huella | `test_evaluacion_final_unica_*` (PI-09) |
| Evaluación final con apertura única (demostración) | `test_evaluacion_final_unica_*` (PI-15); demostración |
| Regla de suficiencia sobre resultados reales del motor | Evaluación final y demostración (D-161) |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 768 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 769 (en Windows, la prueba del enlace simbólico se omite si el sistema no permite crearlo: en la PC del equipo pasan 768 y se omite 1).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| La selección ignora el margen | `test_sin_margen_gana_*` | Detectado |
| El Brier sin invertir la orientación al seleccionar | `test_en_las_metricas_donde_menor_es_mejor_*` | Detectado |
| El cuantil del umbral al revés (q en lugar de 1 − q) | `test_umbral_fijo_cuantil_y_recall_minimo` | Detectado |
| La evaluación final no controla la repetición | `test_evaluacion_final_unica_*` | Detectado |
| No se comprueba la huella del modelo | `test_evaluacion_final_unica_*` | Detectado |
| La prueba se abre una vez por configuración | `test_evaluacion_final_unica_*` | Detectado |
| La evaluación final no exige el protocolo aprobado | `test_evaluacion_final_unica_*` | Detectado |
| El umbral se elige con las predicciones de otra familia | `test_seleccion_con_validacion_*` | Detectado |
| Rutas del registro sin resolver, con el nombre de la carpeta como respaldo (el defecto encontrado en Windows) | `test_rutas_del_registro_con_la_raiz_por_otro_camino` | Detectado |
