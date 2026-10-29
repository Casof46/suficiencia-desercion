# Pruebas del hito H2.4

Con H2.4, el proyecto tiene 184 funciones de prueba, que con sus parámetros suman 433 casos: 326 hasta H2.7 y 107 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows):

```powershell
.venv\Scripts\suficiencia objetivo validar
.venv\Scripts\suficiencia objetivo validar config\ejemplos\objetivo_ficticio.yaml
.venv\Scripts\suficiencia objetivo demostracion
.venv\Scripts\suficiencia objetivo construir data\sintetico\historial.xlsx --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --clave-efimera --salida data\interim\etiquetas.csv
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_objetivo.py` (20 funciones, 100 casos) | **PU-09**: 38 historiales escritos a mano (pausas, reingresos, retiros, traslados, desenlaces excluidos, evento formal, seguimiento incompleto, periodos sin registro y extraordinarios) producen el estado que indican las reglas, cambiando un parámetro a la vez; horizonte relativo a la fecha índice. Propiedades: un positivo siempre tiene periodo del evento dentro del horizonte, un no etiquetable siempre tiene motivo, y lo posterior al horizonte y a la confirmación no cambia la etiqueta. **PU-12**: los no etiquetables nunca llegan al modelado; se cuentan por cohorte y motivo; la marca de análisis de sensibilidad coincide con superar el nivel. **Definición incompleta**: falta de cada una de las 14 secciones, valores nulos que nombran su decisión (DP-01a a DP-01m, DP-18) y 14 definiciones mal formadas | PU-09, PU-12, RF-M1-06, 10 y 11 |
| `tests/integration/test_objetivo_servicio.py` (7 funciones, 7 casos) | El servicio importa, audita y etiqueta un archivo sintético y guarda el resultado sin códigos de estudiante; rechaza datos no sintéticos (DP-02), auditorías no aptas, la falta de definición (DP-01), salidas fuera de `data/` y estados sin categoría. La línea de comandos no muestra la distribución de los estados | PU-17, RF-M1-03, PA-02 |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `objetivo validar`, `demostracion` y `construir` | PA-02 |
| `tests/unit/test_servicios_aplicacion.py` (modificada) | El servicio de datos recibe el lector de la definición del objetivo | — |

## 3. Criterios de aceptación de H2.4

| Criterio (plan de la Fase 2) | Cómo se comprueba |
| --- | --- |
| Sin todos los parámetros, el objetivo no se construye | 14 secciones ausentes y 19 nulas o incompletas: ConfiguracionInvalida o DecisionPendiente con su subcódigo |
| Los casos sintéticos diseñados a mano producen el estado esperado | PU-09 con 38 casos y dos propiedades |
| No implementar ninguna definición de deserción ni valores reales | Solo existe el ejemplo ficticio; `config/objetivo/definicion.yaml` no existe y su ausencia detiene el programa (DP-01) |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 432 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 433.

## 4. Controles negativos realizados

| Cambio introducido a propósito | Resultado |
| --- | --- |
| `para_modelado` deja pasar los no etiquetables | Falla PU-12 |
| El reingreso deja de anular el evento | Fallan 4 casos de PU-09 |
| Un valor nulo toma un valor por omisión en lugar de detenerse | Fallan los 5 casos de campos nulos |

En los tres casos, al restaurar el archivo vuelven a pasar todas las pruebas.
