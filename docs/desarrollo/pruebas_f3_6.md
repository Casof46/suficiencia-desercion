# Pruebas del hito F3.6

Con F3.6, el proyecto tiene 387 funciones de prueba, que con sus parámetros suman 876 casos: 813 hasta F3.5 y 63 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos o inventados y todas las configuraciones y protocolos son ficticios. Las importancias de las pruebas y de la demostración describen asociaciones de modelos entrenados con datos inventados: no son conclusiones sobre estudiantes reales ni sobre el método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

La demostración de F3.4 (`suficiencia evaluacion demostracion`) incluye ahora las explicaciones de las configuraciones congeladas.

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_interpretabilidad.py` (13 funciones, 38 casos) | El ejemplo de DP-11 se lee; un `null` detiene con DP-11; alcances, niveles, partición (la prueba no se admite), muestras y sección local inválidos se rechazan; cada familia tiene su explicador y su escala; la importancia de cada bloque es la suma exacta de las de sus variables, en un caso escrito a mano y como propiedad con datos generados (hypothesis); las columnas de una variable se suman y la importancia global es el promedio del valor absoluto; las muestras son reproducibles, sin repetición y dentro de la partición | PU-21, RF-M5-05 |
| `tests/integration/test_explicadores.py` (5 funciones, 19 casos) | Con las cinco familias y sin calibración, con Platt o con isotónica: el explicador corresponde a la familia; el valor base más las contribuciones reproduce la salida del modelo (error menor que 10⁻⁵); una variable descartada contribuye cero; LIME da un peso por variable; con la misma semilla las explicaciones son idénticas aunque el generador global de NumPy esté en otro estado, y ese generador queda como estaba. Cada columna preprocesada se asocia con su variable. Un modelo de otra familia o con otra forma se rechaza. Un Random Forest con pesos de clase en el que SHAP con muestra de fondo no cumple la aditividad sí la cumple con el explicador elegido (error menor que 10⁻⁹) | PU-21, RF-M5-01 a 03 |
| `tests/integration/test_evaluacion_final.py` (modificada) | Después de la evaluación final: se explican todas las configuraciones congeladas sin agregar accesos a la prueba; el explicador corresponde a la familia elegida; la suma de bloques coincide con la de variables; el registro es exploratorio y guarda partición (`desarrollo`), muestras con sus cohortes (todas de desarrollo) y semilla; las tablas existen; con la misma semilla se repiten las importancias; con `escenario_suficiente` solo se explica la del escenario suficiente, o se rechaza si la regla no eligió uno; DP-11 en `null` detiene; un identificador que no es una evaluación final se rechaza; un modelo modificado después de congelarse se rechaza. La demostración explica las configuraciones congeladas con un solo acceso a la prueba | PI-13, PI-15 |
| `tests/unit/test_experimentos.py` (modificada) | La sección `interpretabilidad` es obligatoria: un `null` detiene con DP-11 | — |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La salida en cp1252 incluye las explicaciones | PA-02 |
| `tests/architecture/test_alcance_h2_0.py` (modificada) | SHAP y LIME dejan de estar postergadas | — |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | Las tablas de `workspace/explicaciones/` quedan ignoradas por git; los módulos nuevos deben versionarse | PA-04 |

## 3. Criterios de aceptación de F3.6

| Criterio (plan de la Fase 3) | Cómo se comprueba |
| --- | --- |
| SHAP con el explicador según el modelo | PU-21; `test_explicadores.py` |
| LIME local | `test_explicadores.py`; PI-13 |
| Importancia por bloque (DP-11) | PU-21 |
| Solo configuraciones congeladas, con partición, muestra y semilla registradas | PI-13 |
| Sin nuevo acceso a la prueba | PI-15 |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 875 casos pasan y 1 se omite fuera de un repositorio git (en Windows, se omite la prueba del enlace simbólico).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| Importancia del bloque como promedio y no como suma | PU-21 | Detectado |
| SVM con el explicador de árboles | PU-21 | Detectado |
| Importancia global sin valor absoluto | `test_interpretabilidad.py` | Detectado |
| Solo la primera columna de cada variable | `test_interpretabilidad.py` | Detectado |
| `KernelExplainer` sin restaurar el generador global | `test_explicadores.py` | Detectado |
| `KernelExplainer` sin semilla | `test_explicadores.py` | Detectado |
| LIME sin semilla | `test_explicadores.py` | Detectado |
| Alcance `escenario_suficiente` ignorado | PI-13 (integración) | Detectado |
| Explicación registrada sin semilla | PI-13 (integración) | Detectado |
| Modelo leído sin verificar su huella | PI-13 (integración) | Detectado |
| `TreeExplainer` con muestra de fondo en lugar de las coberturas de los árboles | `test_explicadores.py` (aditividad del Random Forest con pesos) | Detectado |
