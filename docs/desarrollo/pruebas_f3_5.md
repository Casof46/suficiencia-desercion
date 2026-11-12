# Pruebas del hito F3.5

Con F3.5, el proyecto tiene 369 funciones de prueba, que con sus parámetros suman 813 casos: 769 hasta F3.4 y 44 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones y protocolos son ficticios. Los estados C1 a C8 de las pruebas y de la demostración no son conclusiones sobre el método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

La demostración de F3.4 (`suficiencia evaluacion demostracion`) incluye ahora R0, los controles y la comparación.

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_comparacion.py` (15 funciones, 42 casos) | R0 elige la familia de mejor métrica sin consultar otra regla, con empates por orden; el conjunto más completo de cada ventana; R0-fam por familia seleccionada, R-ven solo cuando hace falta y nunca igual a R0; no inferioridad demostrada, no concluyente o pérdida según la posición del intervalo, y una diferencia no significativa nunca es no inferior; anticipación, reducción de bloques y variables y cobertura temprana en casos escritos a mano, con R0 que no alerta a quien deserta antes de `t_ref`; cada combinación da el estado esperado de C1 a C8, cualquier falla de validez da C7 y ningún estado es "superior"; DP-19 y DP-20 obligatorias; estructuras inválidas | PU-22, PU-23, PU-25, PU-26, PU-27 |
| `tests/integration/test_evaluacion_final.py` (modificada) | La selección construye R0 en el conjunto más completo de T3 con la familia de mayor AUC-ROC recalculada, los R0-fam y el R-ven esperados; sin R0 congelada la comparación es C7 y no abre la prueba; una evaluación inexistente se rechaza; la demostración congela y evalúa selección, R0 y controles en un solo acceso y la comparación no agrega accesos | PU-22, PU-23, PI-15 |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La salida en cp1252 incluye la comparación | PA-02 |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | Las predicciones de prueba en `workspace/evaluacion_final/` quedan ignoradas por git; el módulo nuevo debe versionarse | PA-04 |

PU-24 (diferencia pareada) ya existía desde F3.3; ahora se usa en la comparación.

## 3. Criterios de aceptación de F3.5

| Criterio (plan de la Fase 3) | Cómo se comprueba |
| --- | --- |
| R0 y controles (DP-19) | PU-22, PU-23 |
| Diferencias pareadas | PU-24 |
| No inferioridad | PU-25 |
| Anticipación | PU-26 |
| Estados C1 a C8 (DP-20) | PU-27 |
| Sin nuevo acceso a la prueba | PI-15 |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 812 casos pasan y 1 se omite fuera de un repositorio git (en Windows, se omite la prueba del enlace simbólico).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| R0 con un margen como la regla del método | PU-22 | Detectado |
| R-ven aunque el seleccionado ya sea el más completo | PU-23 | Detectado |
| No inferioridad con el valor puntual en lugar del límite unilateral | PU-25 | Detectado |
| Cobertura de R0 sin descontar a quien deserta antes de `t_ref` | PU-26 | Detectado |
| Clasificación sin comprobar la validez | PU-27 | Detectado |
| C8 evaluado después de la no inferioridad | PU-27 | Detectado |
| La comparación registra un acceso a la prueba | PI-15 (integración) | Detectado |
