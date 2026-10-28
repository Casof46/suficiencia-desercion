# Pruebas del hito H2.0

H2.0 tiene 31 funciones de prueba, que con sus parámetros suman 84 casos, más cuatro comprobaciones estáticas: ruff check, ruff format, mypy e import-linter. Solo prueban lo que existe en H2.0: el paquete, la configuración, los contratos de capas, la privacidad del repositorio y el alcance del hito. **No hay pruebas de funciones metodológicas**, porque esas funciones todavía no existen.

## 1. Cómo ejecutarlas

Todas las comprobaciones con un solo comando:

```powershell
.venv\Scripts\python scripts\verificar.py        # Windows
```

```bash
.venv/bin/python scripts/verificar.py            # Linux o macOS
```

Solo las pruebas: `.venv\Scripts\python -m pytest` (Windows) o `.venv/bin/python -m pytest`. Con detalle, añada `-v`.

## 2. Inventario

| Archivo | Qué demuestra | Criterio de H2.0 | Relación con la especificación |
| --- | --- | --- | --- |
| `tests/unit/test_paquete.py` (4 funciones, 8 casos) | El paquete se importa; la versión coincide con la instalada; se prueba el código del repositorio y no una copia; existen exactamente las cinco capas | 4 | Sección 5, sección 6 |
| `tests/unit/test_configuracion.py` (11 funciones, 16 casos) | `config/proyecto.yaml` se lee; la semilla y la tolerancia siguen sin valor; se rechazan archivo inexistente, YAML inválido, claves desconocidas, rutas faltantes o fuera del repositorio y tipos inválidos | 3 | RNF-10, RNF-15, RF-M3-06, RNF-03 |
| `tests/unit/test_sin_red.py` (2 funciones) | Las conexiones y la resolución de nombres están bloqueadas durante todas las pruebas | 5 | RNF-04 (base de PI-05) |
| `tests/architecture/test_contratos_capas.py` (5 funciones, 15 casos) | Los contratos reales se cumplen; **control negativo**: 11 violaciones distintas rompen un contrato; la cadena legítima interfaz → aplicación → dominio no lo rompe; todas las capas están en el contrato; `.importlinter` es solo ASCII (D-19) | 6 | RNF-01, RF-UI-02 (base de PA-01) |
| `tests/architecture/test_privacidad_repositorio.py` (4 funciones, 38 casos) | Telemetría de Streamlit desactivada; 23 rutas sensibles quedan ignoradas por git; 13 archivos del proyecto no quedan ignorados; en un repositorio real, ningún archivo sensible está versionado | 7 | PA-03 (RNF-06), PA-04 (RNF-07) |
| `tests/architecture/test_alcance_h2_0.py` (5 funciones) | Toda dependencia directa está fijada en el bloqueo con versión exacta y hash; no hay bibliotecas de fases posteriores; ningún módulo usa SQLite; la versión mínima de Python es 3.11 | 3, 10 | 5.1, DP-16 |

Comprobaciones estáticas:

| Herramienta | Qué revisa | Configuración |
| --- | --- | --- |
| ruff check | Errores y estilo: E, F, W, I, B, UP, SIM, PTH | `pyproject.toml` |
| ruff format --check | Formato uniforme de los `.py` y de los bloques de código de los `.md` | `pyproject.toml` |
| mypy (estricto) | Tipos en `src`, `tests` y `scripts` | `pyproject.toml` |
| import-linter | Cuatro contratos entre capas | `.importlinter` |

Qué controlan y qué no controlan los contratos: `docs/arquitectura/estructura_repositorio.md`, sección 3.

## 3. Criterios de aceptación de las pruebas de H2.0

- `scripts/verificar.py` termina con código 0 y el resumen muestra `OK` en las cinco comprobaciones.
- pytest: 83 casos pasan y 1 se omite (PA-04 sobre archivos versionados) mientras la carpeta no sea un repositorio git. Con git inicializado, pasan los 84.
- Ninguna prueba se marca como `xfail` ni se desactiva.

## 4. Resultados reales

Las filas de Linux se ejecutaron el 21 de octubre de 2026 sobre copias limpias del repositorio, con 30 funciones y 83 casos, antes de D-19. Cada copia excluía `.venv` y cachés y siguió exactamente los comandos Linux de `entorno_reproducible.md`. Las filas de Windows se ejecutaron el 28 de octubre de 2026 en la PC de un miembro del equipo, la primera antes de D-19 y las otras dos después. Tras D-19 también se repitió en Linux con Python 3.12.3 (83 pasan y 1 se omite), y en una copia con todos los archivos convertidos a fin de línea CRLF, como los deja Git en Windows: las cinco comprobaciones en `OK`.

| Entorno | Instalación desde el bloqueo | ruff check | ruff format | mypy | import-linter | pytest | Código de salida |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Linux, Python 3.11.17, pip 24.0 | 24 paquetes, hashes verificados; `pip check` sin conflictos | Sin hallazgos | Todos los archivos con formato correcto (ruff también revisa los bloques de código de los `.md`) | Sin errores en 15 archivos | 4 contratos cumplidos | 82 pasan, 1 omitida | 0 |
| Linux, Python 3.12.3, pip 24.0 | Igual | Sin hallazgos | Igual | Igual | Igual | 82 pasan, 1 omitida | 0 |
| Linux, Python 3.13.16, pip 26.2.1 | Igual | Sin hallazgos | Igual | Igual | Igual | 82 pasan, 1 omitida | 0 |
| Linux, Python 3.12.3, con `git init` y `git add -A` (sin commit) | — | — | — | — | — | **83 pasan, 0 omitidas** | 0 |
| Windows, Python 3.13.0, en la PC de Jorge (28 de octubre de 2026, antes de D-19) | Desde el bloqueo, sin errores | Sin hallazgos | 25 archivos con formato correcto | Sin errores en 15 archivos | 4 contratos cumplidos, con los nombres mal mostrados (D-19) | 82 pasan, 1 omitida | 0 |
| Windows, Python 3.13.0, tras D-19 | Sin reinstalar (las dependencias no cambiaron) | Sin hallazgos | 25 archivos con formato correcto | Sin errores en 15 archivos | 4 contratos cumplidos, nombres bien mostrados | 83 pasan, 1 omitida | 0 |
| Windows, Python 3.13.0, tras `git init`, `git add .` y el primer commit (`cb9a955`) | — | Sin hallazgos | Igual | Igual | Igual | **84 pasan, 0 omitidas** | 0 |
| macOS | **No comprobado** | — | — | — | — | — | — |

En la última fila se crearon antes archivos sensibles ficticios (`data/raw/m.xlsx`, `workspace/r.sqlite`, `reports/x.csv` y `.env`). Tras `git add -A`, ninguno quedó preparado para versionar; de `data/` solo se preparó `data/README.md`.

### Controles negativos realizados durante H2.0

- Se añadió temporalmente `from suficiencia import ui` al dominio. `scripts/verificar.py` terminó con código 1, con el contrato de capas roto y las pruebas fallando. Al restaurar el archivo volvió a terminar con código 0.
- Se quitó temporalmente `allow_indirect_imports = True` de `.importlinter`. La prueba `test_usos_legitimos_no_rompen_los_contratos` falló, lo que demuestra que protege la corrección D-15.

### Defectos encontrados y corregidos durante H2.0

| Defecto | Corrección |
| --- | --- |
| `python -m importlinter.cli` termina con código 0 sin comprobar nada; el script de verificación habría dado un falso OK | `scripts/verificar.py` llama a la misma función que el comando `lint-imports`, y la documentación advierte que no se use `-m` |
| El contrato de la interfaz habría rechazado la cadena legítima `ui → application → domain` desde H2.1 | `allow_indirect_imports = True` y una prueba de regresión (D-15) |
| hatchling necesita `editables` para la instalación editable | Añadido a las dependencias de desarrollo y al bloqueo (D-06) |
| En Windows, import-linter mostraba mal las tildes de los nombres de los contratos ("aplicaciÃ³n"): lee `.importlinter` con la codificación regional (cp1252), no con UTF-8. Con letras como "Á" o "Í", la lectura fallaría | `.importlinter` solo en ASCII y la prueba `test_la_configuracion_de_contratos_es_ascii` (D-19). Control negativo: añadir "Á" al archivo hace fallar la prueba |

## 5. Lo que estas pruebas no cubren

- La instalación en macOS: debe hacerla el equipo, si alguien usará ese sistema.
- PA-01 y PA-02 completas, con servicios reales y la línea de comandos: corresponden a H2.1.
- Cualquier lógica del método (ventanas, escenarios, anti-fuga, objetivo, protocolo): hitos H2.2 y siguientes.
- La cobertura de código: su meta (RNF-11) aún no está fijada.
