# Pruebas del hito H2.1

Con H2.1, el proyecto tiene 58 funciones de prueba, que con sus parámetros suman 150 casos: los 84 de H2.0 y 66 nuevos. Se mantienen las cuatro comprobaciones estáticas (ruff check, ruff format, mypy e import-linter), y import-linter tiene ahora 6 contratos en lugar de 4. **No hay pruebas de funciones metodológicas**, porque H2.1 no implementa ninguna.

## 1. Cómo ejecutarlas

Igual que en H2.0:

```powershell
.venv\Scripts\python scripts\verificar.py        # Windows
```

Prueba manual de la línea de comandos:

```powershell
.venv\Scripts\suficiencia estado
.venv\Scripts\suficiencia config validar
.venv\Scripts\suficiencia ejecutar CU-03
```

El último comando debe terminar con el código 3 y el mensaje "El caso de uso CU-03 todavía no está implementado".

## 2. Pruebas nuevas o modificadas en H2.1

| Archivo | Qué demuestra | Requisito o prueba de la especificación |
| --- | --- | --- |
| `tests/architecture/test_contratos_capas.py` (6 funciones, 22 casos) | Los 6 contratos se cumplen (PA-01). **Control negativo** con 17 violaciones; 6 son nuevas: el dominio importa pydantic, la CLI importa el dominio, la persistencia, la interfaz o Streamlit, y la aplicación importa la CLI. Todo módulo de la raíz del paquete está cubierto por algún contrato | PA-01, RNF-01, RF-UI-02, RNF-02 |
| `tests/architecture/test_linea_de_comandos.py` (7 funciones, 15 casos) | `estado` lista los 7 servicios y los 12 casos de uso; un caso de uso de cada servicio se ejecuta desde la CLI y devuelve el código 3 con causa y acción; `config validar` acepta la configuración real y rechaza una inválida; un uso incorrecto devuelve el código 2; el comando `suficiencia` está instalado; la salida se escribe en cp1252 sin cargar Streamlit ni bibliotecas de aprendizaje automático | PA-02, RNF-02, RNF-15 |
| `tests/unit/test_servicios_aplicacion.py` (9 funciones, 24 casos) | Reparto de los 12 casos de uso entre servicios igual al de la sección 6; ninguno figura como disponible; ejecutar cualquiera da un error controlado; contratos inmutables, sin campos desconocidos y con el código validado; validación de la configuración a través del puerto, con una implementación en memoria | RNF-14, RNF-15, sección 6 |
| `tests/unit/test_errores_y_huella.py` (9 funciones, 19 casos) | Todo error lleva causa y acción; `DecisionPendiente` nombra la decisión y rechaza códigos inválidos; huella SHA-256 con el vector oficial de "abc" y rechazo de formatos inválidos | RNF-15, RNF-16 |
| `tests/unit/test_paquete.py` (+1 función) | En la raíz del paquete solo están `__init__` y `cli` | Sección 6 |
| `tests/unit/test_configuracion.py` (modificada) | La configuración declara la especificación 0.5 | D-30 |
| `tests/architecture/test_alcance_h2_0.py` (modificada) | pydantic deja de estar entre las bibliotecas postergadas; la prueba pasa a llamarse `test_no_se_incorporan_bibliotecas_de_hitos_posteriores` | D-20 |

## 3. Criterios de aceptación de H2.1

Del plan de la Fase 2 (paquete de cierre, sección E):

| Criterio | Cómo se comprueba |
| --- | --- |
| El dominio no importa Streamlit ni scikit-learn | Contrato `dominio-sin-dependencias-externas` y su control negativo |
| Cada servicio se invoca desde la CLI | `test_cada_servicio_se_ejecuta_desde_la_linea_de_comandos` (7 servicios) y `test_estado_lista_todos_los_servicios` |
| Prueba negativa con un import prohibido | Control negativo automático (17 violaciones) y control manual de la sección 4 |
| Sin lógica de aprendizaje automático ni interfaz | Contratos de import-linter; `test_no_se_incorporan_bibliotecas_de_hitos_posteriores`; ningún caso de uso disponible |

Resultado esperado de `scripts/verificar.py`: cinco `OK`, 149 casos pasan y 1 se omite si la carpeta no es un repositorio git; en un repositorio git, pasan los 150.

## 4. Resultados reales

Ejecutados el 28 de octubre de 2026 sobre copias limpias del repositorio, sin `.venv` ni cachés, siguiendo los comandos de `entorno_reproducible.md`.

| Entorno | Instalación desde el bloqueo | ruff check | ruff format | mypy | import-linter | pytest | Código de salida |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Linux, Python 3.11.17 | 28 paquetes con hashes verificados (el bloqueo tiene 29; `colorama` solo se instala en Windows); `pip check` sin conflictos | Sin hallazgos | 48 archivos con formato correcto (incluidos los bloques de código de los `.md`) | Sin errores en 35 archivos | 6 contratos cumplidos | 149 pasan, 1 omitida | 0 |
| Linux, Python 3.12.3 | Igual | Igual | Igual | Igual | Igual | 149 pasan, 1 omitida | 0 |
| Linux, Python 3.13.16 | Igual | Igual | Igual | Igual | Igual | 149 pasan, 1 omitida | 0 |
| Linux, Python 3.12.3, con `git init` y `git add -A` | — | — | — | — | — | **150 pasan, 0 omitidas** | 0 |
| Windows | **Pendiente**: debe ejecutarlo el equipo | — | — | — | — | — | — |

Además se descargaron para Windows de 64 bits con Python 3.13 los paquetes del bloqueo, con sus hashes verificados, incluidas las ruedas nuevas `pydantic` y `pydantic-core`. `colorama` no se descargó porque pip evalúa su marcador con el sistema local; es el mismo archivo que H2.0 ya instaló en Windows.

### Controles negativos realizados

- Se añadió a `cli.py` un import directo del dominio: import-linter marcó el contrato `cli-solo-aplicacion` como roto y `scripts/verificar.py` falló. Al restaurar el archivo volvió a terminar con código 0.
- Se quitó el contrato `cli-solo-aplicacion` de `.importlinter`: fallaron los tres casos del control negativo que lo protegen.
- Se añadió el carácter "→" a la salida de `estado`: falló la prueba de cp1252, como corresponde.

## 5. Lo que estas pruebas no cubren

- La ejecución en Windows de esta versión: debe hacerla el equipo.
- Los contratos de cada caso de uso (D-21), que se probarán en su hito.
- Los mensajes de `argparse` que siguen en inglés.
