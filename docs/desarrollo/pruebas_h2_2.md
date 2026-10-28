# Pruebas del hito H2.2

Con H2.2, el proyecto tiene 87 funciones de prueba, que con sus parámetros suman 206 casos: 150 hasta H2.1 y 56 nuevos o ampliados. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter no cambian. Todas las variables y fechas de las pruebas son ficticias.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual:

```powershell
.venv\Scripts\suficiencia escenarios
.venv\Scripts\suficiencia escenarios --configuracion config\ejemplos\escenarios_ficticio.yaml --variables config\ejemplos\variables_ficticias.yaml
```

El primero debe detenerse por DP-01d. El segundo debe mostrar "EJEMPLO FICTICIO", 32 escenarios (28 factibles y 4 no factibles) y "Verificación anti-fuga: correcta".

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_escenarios.py` (17 funciones, 26 casos) | Exactamente 8 conjuntos y todos con A; catálogo T0 a T3 en orden; sin fecha índice, `DecisionPendiente(DP-01d)`; catálogo incompleto o desordenado rechazado; 32 escenarios únicos; un bloque sin variables vuelve no factible el escenario; cada escenario recibe exactamente sus variables; **propiedad**: para cualquier lista de variables, ninguna aparece antes de su ventana mínima y ninguna disponible se pierde; el canario marcado T3 solo aparece en T3, y el verificador lo detecta si se inserta a mano en T1 | PU-01, PU-02, PU-03, PU-18, PU-19; criterio de CU-04 (9.3) |
| `tests/unit/test_escenarios_yaml.py` (7 funciones, 19 casos) | La configuración del repositorio se detiene por DP-01d; los ejemplos se leen y se declaran ficticios; 8 tipos de catálogo inválido y 6 de variables inválidas se rechazan con mensaje en español; sin el archivo del proyecto la causa es DP-03, y con una ruta indicada que no existe es un error de ruta | PU-18; criterio de H2.2 sobre mensajes en español |
| `tests/unit/test_servicios_aplicacion.py` (+2 funciones, +4 casos) | CU-04 muestra su avance y sigue incompleto; el servicio usa los puertos (con implementaciones en memoria) y propaga el rótulo ficticio | RNF-14, D-34, D-40 |
| `tests/architecture/test_linea_de_comandos.py` (+3 funciones, +3 casos) | `suficiencia escenarios` con los ejemplos, con `--detalle` y con la configuración del proyecto (se detiene por DP-01d); la prueba de cp1252 incluye los comandos nuevos | PA-02 |
| `tests/architecture/test_privacidad_repositorio.py` (+4 casos) | `.hypothesis/` queda fuera de git; `config/escenarios.yaml` y los dos ejemplos se versionan | PA-04 |

## 3. Criterios de aceptación de H2.2

| Criterio (plan de la Fase 2) | Cómo se comprueba |
| --- | --- |
| Exactamente 8 conjuntos y 32 escenarios | PU-01; `test_la_matriz_tiene_32_escenarios_unicos` |
| Ninguna variable posterior a su ventana aparece en ningún caso generado | PU-02 (propiedad) y PU-03 (canario); el servicio ejecuta el verificador antes de devolver la matriz |
| Una configuración inválida se rechaza con mensaje en español | `test_un_catalogo_invalido_se_rechaza_en_espanol` y `test_unas_variables_invalidas_se_rechazan_en_espanol` |
| Factibilidad: un bloque sin variables vuelve no factible el escenario | PU-19 |
| No implementar la asignación real de variables (DP-03) ni fechas índice reales (DP-01d) | La configuración del repositorio deja ambas pendientes; los ejemplos son ficticios y lo declaran |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 205 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 206.

## 4. Resultados reales

Ver `docs/gestion/registro_h2_2.md`, sección 3.

### Control negativo

Se cambió el constructor para que ignorara la ventana mínima, como si hubiera un error de programación que deja entrar variables futuras. Fallaron 13 pruebas: las propiedades de PU-02, el canario de PU-03, PU-19 y las de la CLI y del servicio. En estas dos últimas, el verificador detuvo la generación con `FugaTemporal` antes de mostrar resultados. Al restaurar el archivo, las 205 volvieron a pasar.
