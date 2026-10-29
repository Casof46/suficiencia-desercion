# Pruebas del hito H2.5

Con H2.5, el proyecto tiene 205 funciones de prueba, que con sus parámetros suman 470 casos: 433 hasta H2.4 y 37 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows):

```powershell
.venv\Scripts\suficiencia poblaciones construir data\sintetico\historial.xlsx --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --clave-efimera
.venv\Scripts\suficiencia poblaciones construir data\sintetico\historial.xlsx --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --configuracion config\ejemplos\poblaciones_ficticio.yaml --clave-efimera
.venv\Scripts\suficiencia poblaciones leer-prueba workspace\particiones\<carpeta> --motivo "prueba del sello"
.venv\Scripts\suficiencia registro ver accesos
.venv\Scripts\suficiencia registro verificar
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_poblaciones.py` (15 funciones, 31 casos) | **PU-10**: quien deserta después de T1 y antes de T2 es positivo en T0 y T1 y no aparece en T2 ni T3; los no etiquetables nunca entran. **PU-11**: D2 es la población en riesgo en T3 e idéntica en todas las ventanas. **Cobertura D3**: el evento previo a la fecha índice cuenta como no detectable. Horizonte relativo. **PU-13** (propiedad): agregar cohortes de prueba no cambia los descriptivos de desarrollo. **PI-07** (propiedad, parte de la partición): toda cohorte de prueba es posterior a las de desarrollo; particiones inválidas. **PI-02**: el sello solo entrega la prueba a la evaluación final y registra cada intento. Configuración: valores nulos que nombran DP-01d, DP-04, DP-05 y DP-17, y configuraciones mal formadas | PU-10, PU-11, PU-13, PI-02, PI-07 |
| `tests/integration/test_poblaciones_servicio.py` (6 funciones, 6 casos) | Construcción completa con el historial sintético: tamaños de cada partición, descriptivos solo de desarrollo, seguimiento por cohorte, índices sin códigos de estudiante. Leer la prueba falla y queda en el registro, que sigue íntegro. Una prueba modificada fuera del programa se detecta. **PU-17**: una auditoría no apta impide construir. Sin configuración: DP-04. Línea de comandos | PI-02, PU-17, RF-M2-06 a 09 |
| `tests/architecture/test_linea_de_comandos.py` (modificada) | La prueba de cp1252 incluye `poblaciones construir` y `leer-prueba` | PA-02 |
| `tests/unit/test_servicios_aplicacion.py` (modificada) | El servicio de escenarios recibe los puertos nuevos | — |

## 3. Criterios de aceptación de H2.5

| Criterio (plan de la Fase 2) | Cómo se comprueba |
| --- | --- |
| Los tres diseños producen las poblaciones esperadas en casos sintéticos | PU-10, PU-11 y la prueba de cobertura D3 |
| Ningún componente distinto de la evaluación final obtiene filas de prueba | PI-02 en unidad e integración; la partición no expone la prueba; control negativo |
| Ningún conteo que dependa del resultado se calcula sobre la prueba | PU-13 (propiedad) y la prueba de integración; control negativo |
| No implementar la elección del diseño principal ni de cohortes reales | Solo existe el ejemplo ficticio; sin `config/poblaciones.yaml`, el programa se detiene (DP-04) |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 469 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 470.

## 4. Controles negativos realizados

| Cambio introducido a propósito | Resultado |
| --- | --- |
| El sello deja leer la prueba a cualquier operación | Fallan las 3 pruebas de PI-02 |
| D1 no excluye a quien desertó antes de la fecha índice | Falla PU-10 |
| La prueba puede ser anterior al desarrollo | Fallan PI-07 y 2 casos de partición inválida |
| Los descriptivos usan todas las cohortes | Fallan PU-13 y la prueba de integración |

En los cuatro casos, al restaurar el archivo vuelven a pasar todas las pruebas.
