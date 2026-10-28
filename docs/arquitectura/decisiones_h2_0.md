# Decisiones técnicas del hito H2.0

Estas son decisiones **técnicas y reversibles** tomadas para construir H2.0. Ninguna resuelve una decisión metodológica DP ni acepta una recomendación REC. Las decisiones del método se registrarán en `docs/decisiones/` cuando el equipo y la asesoría las tomen.

Estados: **Aplicada**, implementada en H2.0 · **Provisional**, implementada y sujeta a una decisión pendiente del equipo · **Pendiente**, no resuelta.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-01 | Python mínimo 3.11, recomendado 3.12 | Solo 3.12 o 3.13; admitir 3.10 | La especificación pide 3.11 o superior (5.1); `tomllib` existe desde 3.11; 3.12 tiene amplio soporte de las bibliotecas científicas que llegarán después. Comprobado en 3.11, 3.12 y 3.13 | Aplicada |
| D-02 | Nombre del paquete `suficiencia` | `suficiencia_desercion`, `metodo_suficiencia` | Es el nombre de la sección 6 de la especificación. **Depende de REC-05, no aceptada.** Cambiarlo afecta a `pyproject.toml`, `src/suficiencia/`, `.importlinter` y los imports de las pruebas | Provisional |
| D-03 | Estructura `src/` con instalación editable | Paquete en la raíz; `pythonpath` en pytest | La sección 6 de la especificación lo pide: las pruebas importan el paquete instalado, no archivos sueltos | Aplicada |
| D-04 | Dependencias de ejecución mínimas: solo PyYAML | Instalar ya la lista completa de 5.1; el contrato provisional del documento de auditoría (pandas, NumPy, pyarrow, openpyxl, pydantic, PyYAML) | La instrucción de H2.0 pide no instalar bibliotecas que todavía no se usan. H2.0 solo lee YAML. **Desviación** respecto del plan de la auditoría (sección G), registrada abajo | Aplicada |
| D-05 | Bloqueo universal `requirements.lock` con hashes, generado con `uv pip compile --universal` | pip-tools (`pip-compile`); `pip freeze`; `uv.lock` con `uv sync` | pip-tools y `pip freeze` resuelven para una sola plataforma y omiten, por ejemplo, `colorama`, que pytest necesita en Windows; con `--require-hashes` la instalación en Windows fallaría. El archivo resultante se instala con `pip` normal; `uv` solo lo necesita quien regenera el bloqueo. **Desviación menor** respecto de 5.1, que nombraba pip-tools como herramienta condicional sustituible | Aplicada |
| D-06 | Backend `hatchling` y `editables` fijados en el bloqueo; instalación con `--no-build-isolation` | setuptools; aislamiento de construcción por defecto | Con aislamiento, pip descargaría el backend sin versión fija. Así toda la instalación queda fijada y verificada por hash | Aplicada |
| D-07 | Herramientas: pytest, ruff (lint y formato), mypy estricto, import-linter | flake8, isort y black por separado; pylint; pyright | Una herramienta por función. import-linter es el que nombra la especificación (`.importlinter`, PA-01) | Aplicada |
| D-08 | Sin pytest-cov ni hypothesis en H2.0 | Incluirlos ya | La meta de cobertura (RNF-11) se fija al aprobar la Fase 1; hypothesis se necesita desde H2.2 (PU-02). Se añadirán en el hito que los use | Aplicada |
| D-09 | Configuración en `config/proyecto.yaml`, leída en `persistence` | `configs/`; TOML; leer desde el dominio | `config/` es el nombre de la especificación. YAML cumple RNF-10. La lectura de archivos es entrada y salida, por eso no va en el dominio | Aplicada |
| D-10 | `semilla_global` y `tolerancia_metricas` quedan en `null` | Fijar valores de ejemplo | La semilla se fija en el hito que la use (RF-M3-06); la tolerancia, después de medir (RNF-03, 5.2). Un valor de ejemplo podría tomarse por definitivo | Aplicada |
| D-11 | No se usa SQLite y una prueba lo impide | Crear ya el registro en SQLite | DP-16 sigue pendiente | Provisional (hasta DP-16) |
| D-12 | Las pruebas bloquean la red desde `tests/conftest.py` | pytest-socket | Cumple RNF-04 sin otra dependencia | Aplicada |
| D-13 | `.streamlit/config.toml` con telemetría desactivada, sin instalar Streamlit | Esperar a la fase de interfaz | La auditoría asigna PA-03 a H2.0; el archivo no instala ni ejecuta nada | Aplicada |
| D-14 | `scripts/verificar.py` como punto único de comprobación | Makefile; nox; tox | Windows no incluye `make`; nox y tox añaden dependencias | Aplicada |
| D-15 | Contrato `ui-solo-aplicacion` con `allow_indirect_imports = True` | Valor por defecto (prohibir también cadenas indirectas) | Con el valor por defecto, la cadena legítima `ui → application → domain` rompería el contrato desde H2.1. Defecto encontrado y corregido durante H2.0 | Aplicada |
| D-16 | Sin `.env.example` | Incluir uno | H2.0 no usa variables de entorno | Aplicada |
| D-17 | Copia de referencia de la especificación v0.4 y de los diagramas en `docs/` | Solo un enlace al documento en línea | Permite trabajar sin conexión y versionar junto al código la versión que se implementa. La vigente sigue siendo la del documento en línea | Aplicada |
| D-18 | El repositorio se entrega sin historial git | Crear un commit inicial | Hacer commits corresponde al equipo, con su identidad. Ver `README.md` | Aplicada |
| D-19 | `.importlinter` solo en ASCII, con una prueba que lo exige | Configurar UTF-8 en cada PC (`PYTHONUTF8=1`); mover los contratos a `pyproject.toml` | import-linter lee el archivo `.ini` con la codificación regional; en Windows (cp1252) las tildes se mostraban mal y letras como "Á" harían fallar la lectura. Exigir una variable de entorno sería fácil de olvidar. Defecto hallado en la primera ejecución en Windows | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Auditoría final, sección G (H2.0) | Registrar la matriz de versiones compatibles de las bibliotecas de aprendizaje automático, para cerrar la comprobación de CA-14 | No se registró: esas bibliotecas no se instalan en H2.0 | Instrucción de H2.0 de no instalar bibliotecas pesadas aún no usadas. CA-14 queda pendiente hasta el hito que las introduzca |
| Auditoría final, sección G (contrato provisional) | Instalar pandas, NumPy, pyarrow, openpyxl, pydantic y PyYAML | Solo PyYAML | La misma instrucción (D-04) |
| Especificación 5.1 | Archivo de bloqueo con pip-tools (sustituible) | `uv pip compile --universal` (D-05) | Bloqueo válido en Windows |
| Especificación 6 | `docs/decisiones/`, `tests/integration/`, `tests/fixtures/`, `cli.py`, `notebooks/` | No se crean todavía | Estructura mínima; se añaden en el hito que las use |
| Instrucción de H2.0 | Carpeta `configs/` | `config/` | La especificación prescribe `config/` |

## Supuestos temporales

- El nombre `suficiencia` y la lista de dependencias se mantienen hasta que el equipo decida REC-05.
- SQLite no forma parte del proyecto hasta que se resuelva DP-16.
- La instalación en Windows se comprobó una vez, con Python 3.13.0 en la PC de un miembro del equipo. Otras versiones de Python en Windows no se han comprobado.
- Se supone acceso a PyPI para la primera instalación. Con un proxy institucional, puede hacer falta configurar `pip` según las indicaciones del área de TI.

## Pendientes

| Pendiente | Responsable | Cuándo |
| --- | --- | --- |
| Decidir REC-05 (nombre y dependencias) | Equipo | Antes de aceptar H2.0 |
| Repetir `scripts/verificar.py` en Windows tras D-19 (la primera ejecución, del 28 de octubre de 2026, terminó en OK) | Equipo | Antes de aceptar H2.0 |
| Inicializar git y hacer el primer commit; con el repositorio creado, la prueba PA-04 de archivos versionados deja de omitirse | Equipo | Al aceptar H2.0 |
| Definir la licencia del repositorio | Equipo | Antes de compartirlo fuera del equipo |
| Meta de cobertura (RNF-11) e incorporación de pytest-cov | Equipo | Al aprobar la Fase 1 |
| Matriz de compatibilidad de bibliotecas de aprendizaje automático (CA-14) | Equipo | En el hito que las introduzca |
| DP-16 (SQLite o archivos) | Equipo | Antes de H2.7 |
