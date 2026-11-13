# Pruebas del hito F3.7

Con F3.7, el proyecto tiene 402 funciones de prueba, que con sus parámetros suman 903 casos: 876 hasta F3.6 y 27 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones y protocolos son ficticios. Los resultados del reporte y de los gráficos no son conclusiones sobre estudiantes reales ni sobre el método.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

La demostración (`suficiencia evaluacion demostracion`) acepta ahora `--reporte reports\<carpeta>`, y el visor tiene la página "Resultados (Fase 3)".

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_reporte_resultados.py` (9 funciones, 13 casos) | Un registro sin origen declarado se trata como sintético; una tabla sintética sin columna de rótulo, o con una fila sin rótulo, se rechaza; el texto debe empezar con la leyenda; el reporte sintético lleva la leyenda y el rótulo en cada fila de cada tabla; el reporte comparativo tiene R0, controles, intervalos, anticipación, reducción, estado, interpretabilidad y limitaciones, y ningún seudónimo; si alguna parte es sintética, el reporte es sintético; un reporte alterado sin rótulo se rechaza; cada gráfico sintético lleva el rótulo en el título y la leyenda al pie, y dibuja exactamente lo que devolvieron los servicios | PI-16, RF-M6-04, RF-M6-07, RF-UI-03 |
| `tests/integration/test_exportacion_resultados.py` (4 funciones, 4 casos) | La exportación escribe el texto, un CSV por tabla y el Excel, todos con el rótulo y con su huella; un reporte sin rótulo no se exporta ni escribe nada; la exportación solo va a `reports/` y no sobrescribe; la exportación de experimentos del registro lleva el rótulo en cada fila, también en una corrida sin origen declarado | PI-16, RF-M6-03 |
| `tests/integration/test_evaluacion_final.py` (modificada) | La evaluación final, la comparación y la explicación declaran `origen_datos: sintetico` en el registro; la demostración exporta su reporte rotulado con `--reporte` | PI-16 |
| `tests/integration/test_visor.py` (modificada; 2 funciones y 1 caso nuevos) | La página de resultados se ejecuta con el aviso; sin el historial ampliado explica cómo generarlo; con él, la demostración desde el visor muestra cuatro gráficos Plotly rotulados y las dos descargas, y no escribe en el registro del proyecto | PI-16, RF-UI-03 |
| `tests/architecture/test_alcance_h2_0.py` (modificada) | Plotly deja de estar postergada | — |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | Los reportes de `reports/` y el historial ampliado quedan ignorados por git; los módulos nuevos deben versionarse | PA-04 |

## 3. Criterios de aceptación de F3.7

| Criterio (plan de la Fase 3) | Cómo se comprueba |
| --- | --- |
| Páginas de resultados con rótulo sintético | `test_visor.py`; PI-16 en `test_reporte_resultados.py` |
| Exportación rotulada; sin rótulo se rechaza | PI-16 en `test_exportacion_resultados.py` |
| Rótulo en los registros | PI-16 en `test_evaluacion_final.py` |
| Gráficos con Plotly | RF-UI-03 en `test_reporte_resultados.py` y `test_visor.py` |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 902 casos pasan y 1 se omite fuera de un repositorio git (en Windows, se omite la prueba del enlace simbólico).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| Reporte sin la leyenda | `test_reporte_resultados.py` | Detectado |
| Tablas sin la columna de rótulo | `test_reporte_resultados.py` | Detectado |
| Exportación sin comprobar el rótulo | `test_exportacion_resultados.py` | Detectado |
| Gráfico sin el rótulo en el título | `test_reporte_resultados.py` | Detectado |
| Exportación del registro sin el rótulo | `test_exportacion_resultados.py` | Detectado |
| Origen no declarado tratado como real | `test_reporte_resultados.py` | Detectado |
| Evaluación final registrada sin su origen | `test_evaluacion_final.py` | Detectado |
