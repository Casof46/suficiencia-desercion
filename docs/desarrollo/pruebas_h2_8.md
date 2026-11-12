# Pruebas del hito H2.8

Con H2.8, el proyecto tiene 280 funciones de prueba, que con sus parámetros suman 600 casos: 584 hasta H2.6 y 16 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

En VS Code: Terminal > Ejecutar tarea > "1. Verificar todo".

Prueba manual (Windows):

```powershell
.venv\Scripts\suficiencia decisiones
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/acceptance/test_casos_de_uso_sinteticos.py` (6 funciones, 6 casos) | **CU-03**: por la línea de comandos, cada estudiante tiene estado de etiqueta, motivo si no es etiquetable, periodo del evento si es positivo y último periodo observado, sin códigos de estudiante; sin definición aprobada se detiene por DP-01. **CU-04**: 32 escenarios (28 factibles), anti-fuga correcta, partición con sus cuatro grupos y prueba sellada; leerla se rechaza y queda registrado. **CU-05**: borrador, aprobación solo con las decisiones registradas, versión aprobada con su huella, inmutable, con DP-19 y DP-20 incluidas; el ejemplo ficticio nunca se aprueba. **PI-11** (parte determinista): dos ejecuciones con la misma clave dan exactamente las mismas etiquetas y las mismas huellas de partición | CU-03, CU-04, CU-05, PI-11 |
| `tests/unit/test_decisiones.py` (3 funciones, 8 casos) | El catálogo del repositorio lista DP-01 a DP-20 sin ningún campo de decisión ni de valor; solo el código exacto registra una decisión (DP-08h no cierra DP-08); catálogos inválidos se rechazan | RF-M6-05 |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `decisiones` | PA-02 |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | El catálogo y las pruebas de aceptación deben versionarse | PA-04 |

## 3. Criterios de aceptación de H2.8

| Criterio (plan de la Fase 2) | Cómo se comprueba |
| --- | --- |
| Salida completa de pytest adjunta | `docs/gestion/evidencia_fase_2/pytest_windows.txt` |
| Instalación verificada desde el README en un entorno limpio | Clon nuevo + pasos del README, en Linux y en Windows (`docs/gestion/evidencia_fase_2/`) |
| Lista de limitaciones conocidas | `docs/gestion/informe_cierre_fase_2.md`, sección 6 |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 599 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 600.

## 4. Controles negativos realizados

| Cambio introducido a propósito | Resultado |
| --- | --- |
| Un subcódigo registrado cuenta como la decisión completa | Falla 1 prueba |
| La seudonimización ignora la clave del entorno | Falla PI-11 |

En los dos casos, al restaurar el archivo vuelven a pasar todas las pruebas.
