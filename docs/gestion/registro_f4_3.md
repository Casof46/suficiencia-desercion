# Registro del hito F4.3: ensayo general con el dataset sintético del OE3

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F4.1 |
| Base | Plan de la Fase 4 (sección 3, F4.3); README del dataset sintético del OE3 (proyecto TP1) |
| Autorización | El equipo pidió empezar F4.3 el 12 de noviembre de 2026, recuperando el generador del dataset de la conversación en que se hizo (comunicado por Jorge; pendiente de confirmación de Javier). La asesoría no se ha pronunciado sobre el plan de la Fase 4 |
| Riesgo aceptado | Las definiciones del generador difieren en parte de las del motor; se documentan como supuestos del ejemplo ficticio (DP-01 sigue abierta) |
| Estado del hito | **Ejecutado y verificado en Linux y Windows.** Pendiente: commit del equipo y aceptación |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `scripts/oe3/generar_dataset_sintetico.py` | Generador del dataset del OE3, recuperado y sin cambios (D-201) |
| `scripts/preparar_ensayo_oe3.py` | Comprobación de las 10 huellas, conversión al formato del motor y comparación de etiquetas en desarrollo (D-202, D-206) |
| `src/suficiencia/experimentation/pipelines.py` | Corrección del orden de columnas del preprocesamiento (D-203) |
| `config/ejemplos/oe3/` | Diccionario, objetivo, poblaciones, escenarios y experimentos FICTICIOS del ensayo (D-204, D-205) |
| `pyproject.toml` | El generador y `data/` quedan fuera de ruff; el generador, fuera de mypy |
| `workspace/tareas/verificar_f43.cmd` | Verificación en Windows: comprobaciones, dataset, conversión y método completo |
| Pruebas y documentación | `test_ensayo_oe3.py`, `pruebas_f4_3.md`, `decisiones_f4_3.md`, este registro; `verificar_f43b.cmd` (D-208) |

## 2. Dependencias añadidas

Ninguna. El generador usa numpy, pandas y openpyxl, que ya estaban en el entorno.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 944 pasan y 1 se omite (sin git), con D-208. Generador con semilla 20261023: sus 16 controles `SUPERADO` y las 10 huellas coinciden con el README. Historial del ensayo: 27 534 filas, 4050 estudiantes y 12 cohortes; huella `f06e7098b231fee6…`. Etiquetas de desarrollo: coinciden 2655 de 2681 (apartado «Diferencias entre el motor y el generador» de `decisiones_f4_3.md`). Método completo en demostración, con los 28 escenarios factibles, en 8 minutos: 140 corridas exitosas de 140; prueba sellada de 698 unidades; selección, congelamiento, evaluación final con un solo acceso, comparación con R0 y controles, y 34 configuraciones explicadas; reporte rotulado en `reports/ensayo_oe3_linux` |
| Windows 11, Python 3.13.0 (12 de noviembre de 2026) | `verificar_f43.cmd`: cinco `OK`; 6 contratos cumplidos; 943 pasan y 1 se omite (el sistema no permite crear enlaces simbólicos). Generador: sus 16 controles `SUPERADO` y las 10 huellas coinciden. Etiquetas de desarrollo: coinciden 2655 de 2681, como en Linux. Método completo con los 28 escenarios en unos 22 minutos: 140 corridas exitosas de 140; prueba sellada de 698 unidades; un solo acceso a la prueba; 34 configuraciones explicadas; reporte rotulado en `reports\ensayo_oe3`. La regla (T0\|A) y el estado de la comparación (C4) coinciden con Linux. En 3 de los 28 escenarios (T0\|A+S, T0\|A+F+S y T3\|A), la familia seleccionada fue otra: con el margen de selección de 0,01, pequeñas diferencias numéricas entre sistemas y versiones cambian cuál queda primera. El historial del ensayo tuvo otra huella (`0e2fddee…`) por el fin de línea CRLF; se corrigió (D-208). `verificar_f43b.cmd` (12 y 13 de noviembre de 2026), con la corrección: cinco `OK`; 944 pasan y 1 se omite; el historial del ensayo tiene la misma huella que en Linux, `f06e7098b231fee6…`. Evidencia: `workspace\tareas\verificar_f43.log` y `verificar_f43b.log` |

Salidas de la demostración (no son conclusiones): con el criterio ficticio de F3.4 (límite inferior del AUC mayor que 0,5), la regla marcó el escenario T0|A, y la comparación con R0 dio el estado C4. Ambos resultados dependen de un criterio inventado y de relaciones inventadas por el generador. No dicen qué ventana o qué bloques bastan en una universidad real.

## 4. Matriz de criterios de aceptación de F4.3

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Dataset del OE3 regenerado con su script y su semilla, y huellas comprobadas antes de usarlo | Cumplido en Linux y Windows | 10 de 10 huellas; `test_ensayo_oe3.py` |
| 2 | Diccionario y configuraciones ficticias para 40 variables y 12 cohortes | Cumplido en Linux y Windows | `config/ejemplos/oe3/`; `test_ensayo_oe3.py` |
| 3 | El método completo en demostración | Cumplido en Linux y Windows | Salida de `evaluacion demostracion`; `reports/ensayo_oe3_linux` |
| 4 | Supuestos documentados como EJEMPLO FICTICIO; ninguna DP-xx cerrada | Cumplido | `decisiones_f4_3.md` |
| 5 | Verificación en Windows antes del commit | Cumplido | `verificar_f43.log`, `verificar_f43b.log` |

## 5. Hallazgos del ensayo

1. **Error del motor corregido** (D-203). El entrenamiento fallaba en las cinco familias cuando una variable categórica quedaba entre numéricas. El historial de prueba anterior no lo mostraba.
2. **Diferencias de reglas entre el motor y el generador**, documentadas para la discusión de DP-01 y DP-04 (apartado «Diferencias entre el motor y el generador» de `decisiones_f4_3.md`). La principal: cómo se confirma el evento cuando hay reservas al final del horizonte o en el ciclo H+1. No se cambió el motor.
3. **Desviación del plan:** se usan el archivo ancho y el longitudinal, no solo el ancho (D-202). Queda a decisión del equipo.

## 6. Decisiones metodológicas

Ninguna DP-xx se resolvió.

## 7. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | Pendiente | |
| Jorge | Pendiente | |
