# Pruebas del hito H2.6

Con H2.6, el proyecto tiene 271 funciones de prueba, que con sus parámetros suman 584 casos: 486 hasta H2.D y 98 nuevos (83 de la versión inicial del 4 de noviembre y 15 del ajuste del 11 de noviembre: grupos de comparadores, orden de conjuntos y configuración de VS Code). Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los protocolos, criterios, límites, configuraciones y resultados de estas pruebas son **EJEMPLOS FICTICIOS**. Prueban que el motor aplica lo que recibe, no proponen valores.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows):

```powershell
.venv\Scripts\suficiencia protocolo demostracion
.venv\Scripts\suficiencia protocolo ver
.venv\Scripts\suficiencia estado
```

La demostración trabaja en un registro temporal y no escribe en `workspace/registro.sqlite`. Antes y después de ejecutarla, `protocolo ver` debe decir "No hay ninguna versión del protocolo".

**No ejecute `protocolo borrador config\ejemplos\protocolo_ficticio.yaml` en el proyecto real.** El programa no aprobaría el ejemplo, pero el borrador quedaría para siempre en el registro, que solo admite agregar.

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_suficiencia.py` (24 funciones, 45 casos) | **PU-04**: la regla devuelve el escenario esperado y también "ningún escenario cumple". Un empate que el desempate no resuelve no se fuerza. El orden del desempate lo fija el criterio. Cada condición puede hacer fallar al escenario. Un valor faltante nunca cuenta como cumple. Métricas donde menor es mejor. Igualar el límite depende de `inclusivo`. Sin procedimientos implementados, la regla se detiene por DP-08f. Un procedimiento puede quitar escenarios, no agregarlos. Propiedad: el escenario suficiente siempre cumple y es de la ventana más temprana. **Ajuste**: la no inferioridad se exige frente a todos los comparadores del grupo; un grupo vacío o incompleto nunca cumple; cada escenario puede tener distinto número de comparadores; desempate por un orden explícito de conjuntos y órdenes mal formados. Cada `null` nombra su subcódigo (DP-08a a DP-08g); ningún campo ausente toma un valor | PU-04 |
| `tests/unit/test_protocolo.py` (16 funciones, 25 casos) | **PU-06**: una versión aprobada no se edita, y un cambio crea una versión nueva y una desviación con los experimentos afectados. Solo se aprueba la huella revisada y la última versión. Aprobar exige las nueve decisiones previas a CU-05. Una secuencia de registros alterada se detecta. **PU-05**: sin protocolo vigente se rechazan la regla confirmatoria, el congelamiento y la evaluación final; una versión reemplazada ya no vale; en modo exploratorio un borrador basta y queda marcado. **PI-09**: cambiar cualquiera de 10 campos de una configuración congelada hace que la evaluación final la rechace | PU-05, PU-06, PI-09 |
| `tests/integration/test_protocolo_servicio.py` (7 funciones, 7 casos) | Por los servicios y con SQLite: un protocolo ficticio se guarda pero no se aprueba; uno real exige las decisiones registradas. PU-05 y PU-06 con corridas confirmatorias reales del registrador: la corrida sin protocolo no se ejecuta, la desviación marca la corrida afectada y el registro sigue íntegro. PI-09 por los servicios, sin ningún acceso a la prueba. La demostración no escribe en el registro del proyecto. Comandos `protocolo` | PU-05, PU-06, PI-09 |
| `tests/architecture/test_sin_criterio_por_defecto.py` (5 funciones, 13 casos) | Criterio de aceptación: no hay procedimientos de multiplicidad implementados; ningún campo del criterio ni de la configuración tiene valor por omisión; no hay archivo de protocolo por omisión; el dominio de evaluación no contiene ningún número decimal; el único protocolo en `config/` es el ejemplo ficticio y lo declara | Criterio de aceptación de H2.6 |
| `tests/architecture/test_entorno_vscode.py` (3 funciones, 6 casos) | Los archivos de `.vscode/` son JSON válido; las tareas y la depuración usan solo el intérprete de `.venv`, corren en la carpeta del repositorio, apuntan a archivos que existen y no cambian la red del visor | D-120 |
| `tests/architecture/test_privacidad_repositorio.py` (modificada) | `.vscode/settings.json` y `.vscode/tasks.json` deben versionarse | PA-04 |
| `tests/integration/test_registro_trazabilidad.py` (modificada) | La corrida confirmatoria de PI-03 aprueba antes el protocolo ficticio en su registro temporal; la integridad cuenta las seis tablas | PI-03 (D-116) |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `protocolo demostracion`, `borrador`, `ver` y `registro ver protocolos` | PA-02 |

## 3. Criterios de aceptación de H2.6

| Criterio (plan de la Fase 2) | Cómo se comprueba |
| --- | --- |
| No existe ningún criterio, umbral ni procedimiento de multiplicidad por defecto en el código ni en `config/` | `test_sin_criterio_por_defecto.py`; los `null` del criterio detienen el programa con el subcódigo de DP-08 |
| Un protocolo aprobado no puede editarse | PU-06 en unidad e integración; el registro solo admite agregar (H2.7) |
| La evaluación rechaza una huella distinta | PI-09 con cada campo de la configuración, en unidad y por los servicios |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 583 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 584.

## 4. Controles negativos realizados

| Cambio introducido a propósito | Resultado |
| --- | --- |
| Una versión aprobada se puede editar | Fallan 3 pruebas (PU-06) |
| La evaluación final no compara la huella | Fallan 12 pruebas (PI-09) |
| Sin protocolo vigente se permite lo confirmatorio | Fallan 5 pruebas (PU-05) |
| Un valor faltante cuenta como cumple | Falla 1 prueba |
| Se agrega un procedimiento de multiplicidad por defecto | Fallan 2 pruebas, entre ellas la de arquitectura |
| Se aprueba sin desviación con experimentos confirmatorios | Fallan 3 pruebas |
| El servicio aprueba un protocolo ficticio | Fallan 2 pruebas |
| La no inferioridad basta frente a un solo comparador del grupo (ajuste) | Falla 1 prueba |
| El orden explícito de conjuntos se ignora (ajuste) | Falla 1 prueba |

En los nueve casos, al restaurar el archivo vuelven a pasar todas las pruebas.
