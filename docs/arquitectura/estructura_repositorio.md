# Estructura del repositorio y límites de los módulos

La estructura sigue la sección 6 de la especificación (igual en la v0.5 y la v0.6), reducida a lo que H2.0 a H2.3 y H2.7 necesitan. Las carpetas de hitos posteriores no se crean vacías: se añaden cuando un hito autorizado las use.

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
│   ├── proyecto.yaml           # rutas y parámetros de reproducibilidad sin valores pendientes
│   ├── escenarios.yaml         # bloques, conjuntos y fechas índice (pendientes, DP-01d); H2.2
│   └── ejemplos/               # catálogo, variables, diccionario, objetivo, poblaciones y partición FICTICIOS; H2.2 a H2.5
├── data/
│   └── README.md               # única pieza versionada de data/
├── docs/
│   ├── especificacion/         # copias de referencia de la v0.6 (vigente), la v0.5 y la v0.4
│   ├── diagramas/              # fuentes Mermaid de los cuatro diagramas
│   ├── arquitectura/           # decisiones_h2_0.md, decisiones_h2_1.md, este documento
│   ├── desarrollo/             # entorno_reproducible.md, pruebas_h2_0.md, pruebas_h2_1.md
│   └── gestion/                # acta, registro_h2_0.md, registro_h2_1.md
├── scripts/
│   ├── verificar.py            # ejecuta todas las comprobaciones
│   └── generar_sintetico.py    # genera archivos SINTÉTICOS dentro de data/; H2.3
├── src/suficiencia/
│   ├── __init__.py             # versión y descripción de las capas
│   ├── cli.py                  # línea de comandos `suficiencia` (H2.1); solo usa application
│   ├── domain/
│   │   ├── errores.py          # errores con causa y acción sugerida (RNF-15)
│   │   ├── huella.py           # huella SHA-256 (RNF-16)
│   │   ├── proyecto.py         # configuración del proyecto como objeto del dominio
│   │   ├── puertos.py          # FuenteConfiguracion, AlmacenArtefactos, FuenteCatalogoVentanas, FuenteVariables
│   │   ├── datos/              # M1: diccionario.py y auditoria.py (H2.3); objetivo.py (H2.4)
│   │   ├── trazabilidad/       # M6: registros.py (registros y cadena de huellas) y filtro.py; H2.7
│   │   └── escenarios/         # M2: modelo.py y construccion.py (H2.2); poblaciones.py y particion.py con el sello (H2.5)
│   ├── application/
│   │   ├── contratos.py        # contratos pydantic de entrada y salida (RNF-14)
│   │   ├── errores.py          # errores reexportados para la CLI y la interfaz
│   │   ├── _base.py            # base de los servicios de casos de uso
│   │   ├── demostracion_objetivo.py # historiales FICTICIOS para `objetivo demostracion`; H2.4
│   │   ├── servicio_*.py       # siete servicios de casos de uso y el del proyecto
│   │   └── composicion.py      # construye los servicios con sus adaptadores
│   ├── experimentation/        # vacía todavía
│   ├── persistence/
│   │   ├── configuracion.py    # lector de config/proyecto.yaml; implementa FuenteConfiguracion
│   │   ├── escenarios_yaml.py  # lector de config/escenarios.yaml y de variables; H2.2
│   │   ├── diccionario_yaml.py # lector del diccionario de datos; H2.3
│   │   ├── lectores.py         # CSV y Excel como texto; escritura del dataset procesado; H2.3
│   │   ├── seudonimizacion.py  # HMAC-SHA256 provisional (DP-14); H2.3
│   │   ├── objetivo_yaml.py    # lector de la definición del objetivo (DP-01, DP-18); H2.4
│   │   ├── poblaciones_yaml.py # lector de ventanas, diseños y partición (DP-01d, DP-04, DP-05, DP-17); H2.5
│   │   ├── particion_archivos.py # índices de la partición en workspace/particiones/; H2.5
│   │   ├── repositorio_sqlite.py # registro de solo agregar (DP-16: SQLite); H2.7
│   │   ├── entorno.py          # captura del entorno (RNF-17); H2.7
│   │   └── exportacion.py      # CSV y Excel con filtro de identificadores; H2.7
│   └── ui/                     # vacía todavía
└── tests/
    ├── conftest.py             # bloqueo de red durante las pruebas
    ├── fixtures/               # generador de historiales SINTÉTICOS (solo pruebas); H2.3
    ├── integration/            # registro SQLite, entorno, corridas y exportación (H2.7); objetivo (H2.4); poblaciones, partición y sello (H2.5)
    ├── unit/                   # dominio, servicios, persistencia, configuración, red
    └── architecture/           # contratos de capas, línea de comandos, privacidad, alcance
```

## 2. Equivalencia con la sección 6 de la especificación

| Especificación v0.5 | Repositorio (H2.1) | Motivo |
| --- | --- | --- |
| `config/` con `proyecto.yaml`, `escenarios.yaml`, `modelos.yaml`, `diccionario/`, `objetivo/`, `protocolo/` | `proyecto.yaml`, `escenarios.yaml` y `ejemplos/` | `diccionario/` depende de DP-03 y `objetivo/` de DP-01 y DP-18 (el ejemplo ficticio está en `ejemplos/`); el resto, de hitos posteriores. Se mantiene el nombre `config/` de la especificación, no `configs/` |
| `data/raw`, `interim`, `processed` | `data/README.md` | Las subcarpetas se crean al usarse; nunca se versionan |
| `workspace/`, `reports/` | No existen | Se generan en ejecución y están excluidas por `.gitignore` |
| `docs/especificacion/` | Copias de referencia de la v0.6, la v0.5 y la v0.4 | Igual |
| `docs/diagramas/` | Cuatro archivos `.mmd` | Igual |
| `docs/decisiones/` | Ficha de DP-16, la primera decisión resuelta (RF-M6-05) | Las decisiones técnicas de cada hito están en `docs/arquitectura/`, y no son decisiones metodológicas |
| — | `docs/gestion/`, `docs/arquitectura/`, `docs/desarrollo/` | Carpetas solicitadas en la instrucción de H2.0 |
| `src/suficiencia/{domain,application,experimentation,persistence,ui}` | Igual, con `__init__.py` documentado | El contenido empieza en H2.1 |
| `domain/{datos,escenarios,evaluacion,trazabilidad}/` | `escenarios/` (H2.2, con poblaciones y partición desde H2.5), `datos/` (H2.3, con el objetivo desde H2.4) y `trazabilidad/` (H2.7); sin evaluación | `evaluacion/` en H2.6 |
| Siete `application/servicio_*.py` | Los siete, más `servicio_proyecto.py`, `_base.py`, `errores.py` y `composicion.py` | Ver decisiones D-22 y D-23 de H2.1 |
| `src/suficiencia/cli.py` | Igual | Comandos `estado`, `config validar` y `ejecutar` (H2.1) |
| `tests/{unit,integration,acceptance,architecture,fixtures}` | Todas salvo `acceptance/` | Se crea con su primera prueba |
| `scripts/` | `scripts/verificar.py` | Windows no incluye `make` |
| `notebooks/` | No existe | Sin uso en H2.0 |

## 3. Límites entre capas

| Capa | Puede importar | No puede importar | Contrato que lo comprueba |
| --- | --- | --- | --- |
| `ui` | `application` | `domain`, `experimentation`, `persistence` | `capas`, `ui-solo-aplicacion` |
| `application` | `domain`, `experimentation`, `persistence` | `ui`, Streamlit, Plotly | `capas`, `motor-sin-streamlit` |
| `experimentation` | `domain` | `ui`, `application`, `persistence`, Streamlit, Plotly | `capas`, `motor-sin-streamlit` |
| `persistence` | `domain` | `ui`, `application`, `experimentation`, Streamlit, Plotly | `capas`, `motor-sin-streamlit` |
| `domain` | Ninguna capa del paquete | Todas las demás capas y Streamlit, Plotly, scikit-learn, XGBoost, LightGBM, SHAP, LIME, sqlite3, PyYAML, pydantic, pyarrow, openpyxl y joblib | `capas`, `dominio-sin-dependencias-externas` |
| `cli` (raíz del paquete) | `application` | `domain`, `experimentation`, `persistence`, `ui`, Streamlit, Plotly | `cli-solo-aplicacion`, `motor-sin-streamlit` |
| Todas las capas | — | `cli` | `capas-no-usan-cli` |

### Qué controlan los contratos

Todo lo que sigue se comprobó con el control negativo de `tests/architecture/test_contratos_capas.py`:

- Las sentencias `import x` y `from x import y` de los archivos `.py` dentro de `src/suficiencia`, incluidos los imports dentro de funciones.
- En el contrato `capas`, las cadenas indirectas: una capa inferior no puede llegar a una superior ni siquiera a través de un módulo intermedio.
- En `ui-solo-aplicacion` y `cli-solo-aplicacion`, solo los imports **directos** (`allow_indirect_imports = True`). Las cadenas `ui → application → domain` y `cli → application → domain` son el uso previsto y no cuentan como violación. Sin esta opción, el contrato se rompería en cuanto la aplicación usara el dominio. Una prueba de regresión lo protege.
- Imports de los módulos externos de la lista, aunque no estén instalados.

### Qué no controlan

- Imports dinámicos (`importlib.import_module`, `__import__`), código en `exec` o `eval`, y nombres de módulo construidos como texto.
- Dependencias a través de bibliotecas de terceros: si una biblioteca permitida importa Streamlit, el contrato no lo ve.
- El uso de archivos, red o bases de datos sin un import (por ejemplo, abrir un `.sqlite` con otra biblioteca). Para SQLite existe además una prueba específica mientras DP-16 esté pendiente.
- El código fuera de `src/suficiencia` (pruebas, scripts).
- El **control negativo** (`tests/architecture/test_contratos_capas.py`) crea un paquete temporal que viola cada tipo de contrato (17 violaciones) y comprueba que falla. Desde H2.1 los contratos ya no se cumplen de forma trivial: la aplicación usa el dominio y la persistencia, y la CLI usa la aplicación.
- Que todo módulo de la raíz del paquete esté en algún contrato lo comprueba una prueba aparte.

### Composición de dependencias

El dominio define puertos (`domain/puertos.py`) que implementan `persistence` y, más adelante, `experimentation`. Los servicios de `application` reciben las implementaciones ya construidas. El único lugar que elige qué adaptador implementa cada puerto es `application/composicion.py`; la CLI y la futura interfaz obtienen allí los servicios. Así las pruebas sustituyen un adaptador por otro sin archivos (por ejemplo, `tests/unit/test_servicios_aplicacion.py` usa una `FuenteConfiguracion` en memoria).
