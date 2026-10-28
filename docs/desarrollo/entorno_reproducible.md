# Entorno reproducible

Pasos exactos para crear, verificar y mantener el entorno de desarrollo del hito H2.0. Solo se necesitan Python y `pip`. No se usan servicios cloud, credenciales, bases de datos ni conexiones con la universidad.

## 1. Versión de Python

- **Mínima:** 3.11 (`requires-python = ">=3.11"`). El proyecto usa `tomllib`, de la biblioteca estándar desde 3.11.
- **Recomendada:** 3.12.
- **Comprobadas:** 3.11.17, 3.12.3 y 3.13.16 en Linux, y 3.13.0 en Windows. La instalación en macOS no se ha comprobado todavía (ver `docs/gestion/registro_h2_0.md`).

Para comprobar qué versiones tiene instaladas:

- Windows: `py --list`
- Linux o macOS: `python3 --version`

Si falta, instale Python 3.12 desde python.org. En Windows, marque la opción del lanzador `py` durante la instalación.

## 2. Crear el entorno e instalar

El repositorio no depende de activar el entorno: todos los comandos llaman directamente al Python de `.venv`. Así se evitan las restricciones de ejecución de scripts de PowerShell.

### Windows (PowerShell o símbolo del sistema)

```powershell
cd ruta\a\suficiencia-desercion
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .
```

Con otra versión instalada, cambie `-3.12` por `-3.11` o `-3.13`.

### Linux o macOS

```bash
cd ruta/a/suficiencia-desercion
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
```

### Qué hace cada paso

1. `venv` crea un entorno aislado en `.venv/`, que está excluido de git.
2. `--require-hashes -r requirements.lock` instala **exactamente** las versiones fijadas y verifica el hash SHA-256 de cada archivo descargado. Incluye la herramienta de construcción (`hatchling` y `editables`).
3. `--no-deps --no-build-isolation -e .` instala el paquete `suficiencia` en modo editable, usando la herramienta de construcción ya fijada. No descarga nada sin versión fija.

La primera instalación necesita acceso a PyPI. Después, las comprobaciones funcionan sin red.

### Activación opcional

Si prefiere activar el entorno:

- PowerShell: `.venv\Scripts\Activate.ps1`. Si la política de ejecución lo impide, use antes `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`; el cambio solo afecta a esa ventana.
- Símbolo del sistema: `.venv\Scripts\activate.bat`
- Linux o macOS: `source .venv/bin/activate`

## 3. Verificar el entorno

```powershell
.venv\Scripts\python scripts\verificar.py        # Windows
```

```bash
.venv/bin/python scripts/verificar.py            # Linux o macOS
```

Resultado esperado: el resumen final muestra `OK` en las cinco comprobaciones (ruff check, ruff format, mypy, import-linter y pytest), y el comando termina con código 0. Las comprobaciones también pueden ejecutarse por separado:

| Comprobación | Windows | Linux o macOS |
| --- | --- | --- |
| Estilo | `.venv\Scripts\python -m ruff check .` | `.venv/bin/python -m ruff check .` |
| Formato | `.venv\Scripts\python -m ruff format --check .` | `.venv/bin/python -m ruff format --check .` |
| Tipos | `.venv\Scripts\python -m mypy` | `.venv/bin/python -m mypy` |
| Contratos de capas | `.venv\Scripts\lint-imports` | `.venv/bin/lint-imports` |
| Pruebas | `.venv\Scripts\python -m pytest` | `.venv/bin/python -m pytest` |

**No use** `python -m importlinter.cli`: termina con código 0 sin comprobar nada. Use `lint-imports` o `scripts/verificar.py`.

## 4. Regenerar el archivo de bloqueo (solo mantenedores)

Solo es necesario al cambiar dependencias en `pyproject.toml`. Requiere la herramienta `uv`, que no es necesaria para instalar.

```bash
uv pip compile pyproject.toml --extra dev --universal --generate-hashes --python-version 3.11 --annotation-style line -o requirements.lock
```

- `--universal` resuelve para Windows, Linux y macOS a la vez. Por ejemplo, incluye `colorama`, que pytest solo usa en Windows.
- `--python-version 3.11` garantiza que el bloqueo sirva para la versión mínima.
- Después de regenerar: reinstale el entorno, ejecute `scripts/verificar.py` y registre el cambio en `docs/arquitectura/`.

## 5. Problemas frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `THESE PACKAGES DO NOT MATCH THE HASHES` | Descarga alterada, caché corrupta o proxy que modifica archivos | Repetir con `--no-cache-dir`. Si persiste, no forzar la instalación: avisar al equipo |
| `Readme file does not exist` o `No module named 'editables'` al instalar con `-e .` | Falta el README o no se instaló antes `requirements.lock` | Ejecutar los pasos en orden, desde la raíz del repositorio |
| `py` no se reconoce (Windows) | Python instalado sin el lanzador | Usar la ruta completa de `python.exe` o reinstalar con el lanzador |
| Una prueba de privacidad aparece como omitida (`SKIPPED`) | git no instalado, o la carpeta aún no es un repositorio | Instalar git, o ejecutar `git init` y volver a probar |
| `ModuleNotFoundError: suficiencia` | No se ejecutó la instalación editable | Repetir el paso 3 de la sección 2 |

## 6. Qué no hace este entorno (H2.0)

- No instala pandas, scikit-learn, XGBoost, LightGBM, SHAP, LIME, Streamlit ni Plotly. Se añadirán en el hito que los use (decisión D-04).
- No crea ni usa bases de datos. SQLite depende de DP-16, todavía pendiente.
- No usa variables de entorno ni secretos. Por eso no existe `.env.example`.
