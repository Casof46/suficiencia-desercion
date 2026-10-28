# suficiencia-desercion

Aplicación web experimental local para ejecutar, evaluar y documentar un **método temporal que determina la suficiencia de información en la detección temprana del riesgo de deserción académica**. La contribución científica es el método; este repositorio es el instrumento de software que lo ejecutará.

## Estado del proyecto

| Elemento | Estado |
| --- | --- |
| Especificación | Fase 1, versión 0.5, que añade la evaluación comparativa frente a una referencia convencional. **No aprobada formalmente**; propuesta de acta en `docs/gestion/acta_cierre_fase_1_propuesta.md`. H2.0 se construyó sobre la v0.4, y `config/proyecto.yaml` aún la declara: la v0.5 no cambia nada de lo que H2.0 implementa |
| Hito actual | **H2.0 — repositorio y entorno reproducible**, ejecutado con un contrato provisional y pendiente de aceptación por el equipo |
| Funcionalidad | Ninguna funcionalidad metodológica todavía. Solo la estructura de capas, el lector de configuración y las comprobaciones de calidad |
| Decisiones metodológicas | DP-01 a DP-20 abiertas; REC-01 a REC-05 sin aceptar |
| Nombre del paquete | `suficiencia`, **provisional** hasta que se decida REC-05 |

> **Datos institucionales.** No coloque datos reales en este repositorio, no los suba a repositorios públicos ni privados y no los envíe a servicios externos o asistentes de IA sin autorización expresa. Las condiciones previas están en la sección H.1 del documento "Fase 1 — Auditoría final y acta de cierre". La seudonimización no equivale a anonimización.

## Requisitos

- Python **3.11 o superior** (recomendado 3.12). Comprobado en Linux con 3.11, 3.12 y 3.13, y en Windows con 3.13. Con otra versión instalada (`py --list` la muestra), cambie `-3.12` por esa versión en los comandos.
- `pip`, incluido con Python. No se requieren servicios cloud, credenciales, bases de datos ni conexión con la universidad.
- `git`, opcional: algunas pruebas de privacidad se omiten si no está instalado.

## Instalación rápida

Windows (PowerShell), desde la carpeta del repositorio:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .
.venv\Scripts\python scripts\verificar.py
```

Linux o macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python scripts/verificar.py
```

El último comando ejecuta ruff, mypy, import-linter y pytest, y termina con `OK` en las cinco comprobaciones. Explicación paso a paso y solución de problemas en `docs/desarrollo/entorno_reproducible.md`.

## Control de versiones

El repositorio se entrega **sin historial git**: el primer commit corresponde al equipo. Para crearlo:

```bash
git init
git add .
git status          # revise que no aparezcan datos, .venv, secretos ni archivos Excel o CSV
git commit -m "H2.0: repositorio y entorno reproducible"
```

Con el repositorio creado, la prueba de privacidad PA-04 también revisa los archivos versionados; antes de eso, esa prueba se omite.

## Estructura

```text
suficiencia-desercion/
├── pyproject.toml          # metadatos, dependencias y configuración de herramientas
├── requirements.lock       # versiones exactas con hashes (Windows, Linux y macOS)
├── .importlinter           # contratos de dependencias entre capas
├── .gitignore              # exclusión de datos, secretos, modelos y entornos
├── .streamlit/config.toml  # telemetría desactivada (Streamlit aún no se instala)
├── config/proyecto.yaml    # configuración no sensible del proyecto
├── data/README.md          # carpeta de datos NO versionada
├── src/suficiencia/        # paquete: domain, application, experimentation, persistence, ui
├── tests/                  # unit/ y architecture/
├── scripts/verificar.py    # todas las comprobaciones con un solo comando
└── docs/                   # especificación, diagramas, arquitectura, desarrollo y gestión
```

Detalle de cada carpeta y de los límites entre capas: `docs/arquitectura/estructura_repositorio.md`.

## Documentación

| Documento | Contenido |
| --- | --- |
| `docs/especificacion/especificacion_fase_1_v0.5.md` | Copia de referencia de la especificación vigente |
| `docs/especificacion/especificacion_fase_1_v0.4.md` | Copia de la v0.4, base de H2.0 |
| `docs/diagramas/*.mmd` | Fuentes Mermaid de los cuatro diagramas |
| `docs/gestion/acta_cierre_fase_1_propuesta.md` | Propuesta de acta de cierre de la Fase 1 (sin firmar) |
| `docs/gestion/registro_h2_0.md` | Registro del hito: archivos, pruebas y resultados reales |
| `docs/arquitectura/decisiones_h2_0.md` | Decisiones técnicas, alternativas, supuestos y pendientes |
| `docs/arquitectura/estructura_repositorio.md` | Estructura y límites de los módulos |
| `docs/desarrollo/entorno_reproducible.md` | Creación y verificación del entorno |
| `docs/desarrollo/pruebas_h2_0.md` | Pruebas, comandos y criterios de aceptación de H2.0 |
