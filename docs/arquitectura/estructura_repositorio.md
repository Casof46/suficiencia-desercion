# Estructura del repositorio y límites de los módulos

La estructura sigue la sección 6 de la especificación v0.4, reducida a lo que H2.0 necesita. Las carpetas de hitos posteriores no se crean vacías: se añaden cuando un hito autorizado las use.

## 1. Árbol actual

```text
suficiencia-desercion/
├── pyproject.toml              # metadatos, dependencias y configuración de ruff, mypy y pytest
├── requirements.lock           # bloqueo universal con hashes
├── README.md
├── .gitignore                  # exclusiones de datos, secretos, modelos, entornos y cachés
├── .importlinter               # contratos de dependencias entre capas
├── .streamlit/config.toml      # telemetría desactivada (RNF-06, PA-03)
├── config/
│   └── proyecto.yaml           # rutas y parámetros de reproducibilidad sin valores pendientes
├── data/
│   └── README.md               # única pieza versionada de data/
├── docs/
│   ├── especificacion/especificacion_fase_1_v0.4.md   # copia de referencia
│   ├── diagramas/              # fuentes Mermaid de los cuatro diagramas
│   ├── arquitectura/           # decisiones_h2_0.md, este documento
│   ├── desarrollo/             # entorno_reproducible.md, pruebas_h2_0.md
│   └── gestion/                # acta_cierre_fase_1_propuesta.md, registro_h2_0.md
├── scripts/
│   └── verificar.py            # ejecuta todas las comprobaciones
├── src/suficiencia/
│   ├── __init__.py             # versión y descripción de las capas
│   ├── domain/                 # vacía en H2.0
│   ├── application/            # vacía en H2.0
│   ├── experimentation/        # vacía en H2.0
│   ├── persistence/
│   │   └── configuracion.py    # lector de config/proyecto.yaml
│   └── ui/                     # vacía en H2.0
└── tests/
    ├── conftest.py             # bloqueo de red durante las pruebas
    ├── unit/                   # paquete, configuración, red
    └── architecture/           # contratos de capas, privacidad, alcance de H2.0
```

## 2. Equivalencia con la sección 6 de la especificación

| Especificación v0.4 | Repositorio H2.0 | Motivo |
| --- | --- | --- |
| `config/` con `proyecto.yaml`, `escenarios.yaml`, `modelos.yaml`, `diccionario/`, `objetivo/`, `protocolo/` | Solo `config/proyecto.yaml` | El resto pertenece a H2.2 y siguientes. Se mantiene el nombre `config/` de la especificación, no `configs/` |
| `data/raw`, `interim`, `processed` | `data/README.md` | Las subcarpetas se crean al usarse; nunca se versionan |
| `workspace/`, `reports/` | No existen | Se generan en ejecución y están excluidas por `.gitignore` |
| `docs/especificacion/` | Copia de referencia de la v0.4 | Igual |
| `docs/diagramas/` | Cuatro archivos `.mmd` | Igual |
| `docs/decisiones/` | No existe todavía | Se creará al resolverse la primera decisión DP (RF-M6-05). Las decisiones técnicas de H2.0 están en `docs/arquitectura/decisiones_h2_0.md`, que no son decisiones metodológicas |
| — | `docs/gestion/`, `docs/arquitectura/`, `docs/desarrollo/` | Carpetas solicitadas en la instrucción de H2.0 |
| `src/suficiencia/{domain,application,experimentation,persistence,ui}` | Igual, con `__init__.py` documentado | Cumple la estructura; el contenido empieza en H2.1 |
| `src/suficiencia/cli.py` | No existe | Corresponde a H2.1 |
| `tests/{unit,integration,acceptance,architecture,fixtures}` | Solo `unit/` y `architecture/` | Las demás se crean con su primera prueba |
| `scripts/` | `scripts/verificar.py` | Windows no incluye `make` |
| `notebooks/` | No existe | Sin uso en H2.0 |

## 3. Límites entre capas

| Capa | Puede importar | No puede importar | Contrato que lo comprueba |
| --- | --- | --- | --- |
| `ui` | `application` | `domain`, `experimentation`, `persistence` | `capas`, `ui-solo-aplicacion` |
| `application` | `domain`, `experimentation`, `persistence` | `ui`, Streamlit, Plotly | `capas`, `motor-sin-streamlit` |
| `experimentation` | `domain` | `ui`, `application`, `persistence`, Streamlit, Plotly | `capas`, `motor-sin-streamlit` |
| `persistence` | `domain` | `ui`, `application`, `experimentation`, Streamlit, Plotly | `capas`, `motor-sin-streamlit` |
| `domain` | Ninguna capa del paquete | Todas las demás capas y Streamlit, Plotly, scikit-learn, XGBoost, LightGBM, SHAP, LIME, sqlite3, PyYAML, pyarrow, openpyxl y joblib | `capas`, `dominio-sin-dependencias-externas` |

### Qué controlan los contratos

Todo lo que sigue se comprobó con el control negativo de `tests/architecture/test_contratos_capas.py`:

- Las sentencias `import x` y `from x import y` de los archivos `.py` dentro de `src/suficiencia`, incluidos los imports dentro de funciones.
- En el contrato `capas`, las cadenas indirectas: una capa inferior no puede llegar a una superior ni siquiera a través de un módulo intermedio.
- En `ui-solo-aplicacion`, solo los imports **directos** (`allow_indirect_imports = True`). La cadena `ui → application → domain` es el uso previsto y no cuenta como violación. Sin esta opción, el contrato se rompería en cuanto la aplicación usara el dominio. Una prueba de regresión lo protege.
- Imports de los módulos externos de la lista, aunque no estén instalados.

### Qué no controlan

- Imports dinámicos (`importlib.import_module`, `__import__`), código en `exec` o `eval`, y nombres de módulo construidos como texto.
- Dependencias a través de bibliotecas de terceros: si una biblioteca permitida importa Streamlit, el contrato no lo ve.
- El uso de archivos, red o bases de datos sin un import (por ejemplo, abrir un `.sqlite` con otra biblioteca). Para SQLite existe además una prueba específica mientras DP-16 esté pendiente.
- El código fuera de `src/suficiencia` (pruebas, scripts).
- Hoy los contratos se cumplen de forma trivial porque las capas están vacías. Por eso existe un **control negativo**: un paquete temporal que viola los mismos tipos de contrato y debe fallar (`tests/architecture/test_contratos_capas.py`).

### Composición de dependencias

La especificación define puertos en el dominio que implementan `experimentation` y `persistence`, y servicios en `application` que los usan. En H2.0 no existe ningún puerto ni servicio; se crean en H2.1.
