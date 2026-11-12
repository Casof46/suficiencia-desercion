# suficiencia-desercion

Aplicación web experimental local para ejecutar, evaluar y documentar un **método temporal que determina la suficiencia de información en la detección temprana del riesgo de deserción académica**. La contribución científica es el método; este repositorio es el instrumento de software que lo ejecutará.

## Estado del proyecto

| Elemento | Estado |
| --- | --- |
| Especificación | Fase 1, versión 0.6, que incorpora el cambio CP-08 (reporte de no etiquetables por cohorte y análisis de sensibilidad), los responsables de los 29 riesgos y las decisiones del equipo del 29 de octubre de 2026. **No aprobada formalmente**: el equipo eligió la aprobación formal, que espera la conformidad de la asesoría y la firma del acta (`docs/gestion/acta_cierre_fase_1_propuesta.md`). H2.0 se construyó sobre la v0.4, y H2.1 a H2.3 y H2.7 sobre la v0.5 |
| Hitos | H2.0 (repositorio y entorno) aceptado por el equipo el 28 de octubre de 2026. **H2.1** (arquitectura y contratos) y **H2.2** (escenarios y anti-fuga) verificados en Linux y Windows y aceptados el 28 de octubre de 2026. **H2.3** (datos sintéticos, diccionario, importación, auditoría y seudonimización) verificado y aceptado el 29 de octubre de 2026. **H2.7** (trazabilidad y registro, DP-16: SQLite) verificado y aceptado el 29 de octubre de 2026. **H2.4** (objetivo y estados de etiqueta) construido por autorización del equipo sin esperar la conformidad de la asesoría con REC-03; verificado en Linux y Windows y aceptado el 29 de octubre de 2026. **H2.5** (poblaciones, partición y sello) construido con el mismo criterio; verificado en Linux y Windows y aceptado el 29 de octubre de 2026. **H2.D** (visor de demostración local, fuera del plan, a pedido del profesor) verificado en Linux y Windows el 4 de noviembre de 2026 y aceptado el 11 de noviembre de 2026. **H2.6** (protocolo, desviaciones y congelamiento) construido el 4 de noviembre de 2026 por pedido del equipo sin esperar la conformidad de la asesoría con REC-02; verificado en Linux y Windows, con su ajuste del 11 de noviembre, y aceptado ese día. **H2.8** (cierre de la Fase 2) aceptado el 11 de noviembre de 2026; la asesoría dio su conformidad con el informe de cierre. **Fase 3** (entrenamiento con datos sintéticos) en curso: `docs/gestion/plan_fase_3.md`. **F3.1** (matrices, folds y preprocesamiento) verificado en Linux y Windows y aceptado el 11 de noviembre de 2026. **F3.2** (los cinco modelos) verificado en Linux y Windows y aceptado el 12 de noviembre de 2026. **F3.3** (métricas e intervalos) verificado en Linux y Windows el 12 de noviembre de 2026; pendiente de aceptación |
| Funcionalidad | Matriz de 32 escenarios con verificador de fuga temporal (H2.2). Generación de datos **sintéticos**, validación del diccionario, importación de CSV y Excel con seudonimización y auditoría de calidad (H2.3). Registro de trazabilidad de solo agregar en SQLite, con captura del entorno, registro de decisiones, verificación de integridad y exportación sin identificadores (H2.7). Objetivo y estados de etiqueta (positivo, negativo o no etiquetable con motivo) con reglas parametrizadas por DP-01, todas obligatorias y sin valores por omisión; solo con definiciones ficticias (H2.4). Poblaciones D1, D2 y D3 por ventana, partición cronológica por cohortes con piloto, sello de la prueba con registro de accesos y descriptivos solo de desarrollo (H2.5). Visor web local de solo lectura con Streamlit (H2.D). Protocolo confirmatorio versionado (borrador, aprobado, reemplazado) que no se edita una vez aprobado, desviaciones obligatorias, configuraciones congeladas con huella y motor de la regla de suficiencia que recibe el criterio como datos; **no existe ningún criterio ni procedimiento de multiplicidad del proyecto** y el ejemplo ficticio no se puede aprobar (H2.6). Estado de las decisiones DP-01 a DP-20 y pruebas de aceptación de CU-03 a CU-05 (H2.8); informe de cierre en `docs/gestion/informe_cierre_fase_2.md`. Historial sintético ampliado de 12 cohortes, matrices por escenario con corte en el periodo índice, folds cronológicos por cohortes y preprocesamiento ajustado dentro de cada fold, con DP-03, DP-07 y DP-12 como datos obligatorios; (F3.1). Entrenamiento exploratorio de LR, Random Forest, XGBoost, LightGBM y SVM en esos folds, con búsqueda de hiperparámetros, desbalance y calibración como datos (DP-06, DP-07, DP-09), semilla fija y cada corrida registrada, también las fallidas; (F3.2). AUC-ROC, Brier, Brier escalado y Recall@q con la prevalencia e intervalos bootstrap estratificados sobre las probabilidades de validación, y diferencias pareadas, con DP-08a, DP-08e y DP-08i como datos; todavía sin selección (F3.3). Los datos reales no se pueden importar (DP-02, DP-14). Sin configuración real, todo se prueba con los ejemplos ficticios de `config/ejemplos/` |
| Decisiones metodológicas | DP-16 (SQLite) y DP-08h (se permite un piloto) decididas por el equipo (`docs/decisiones/`); las demás, abiertas. REC-04 y REC-05 aceptadas; REC-01 a REC-03 aceptadas por el equipo el 29 de octubre de 2026, pendientes de la conformidad de la asesoría |
| Nombre del paquete | `suficiencia` (REC-05 aceptada) |

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

El último comando ejecuta ruff, mypy, import-linter y pytest, y termina con `OK` en las cinco comprobaciones. Si ya tenía el entorno de un hito anterior, repita los dos comandos `pip install` para actualizarlo. Explicación paso a paso y solución de problemas en `docs/desarrollo/entorno_reproducible.md`.

## Línea de comandos

Desde la carpeta del repositorio (en Linux o macOS, `.venv/bin/suficiencia`):

```powershell
.venv\Scripts\suficiencia estado            # servicios, casos de uso y en qué hito se construye cada uno
.venv\Scripts\suficiencia config validar    # valida config/proyecto.yaml
.venv\Scripts\suficiencia escenarios        # se detiene: faltan las fechas índice (DP-01d)
.venv\Scripts\suficiencia escenarios --configuracion config\ejemplos\escenarios_ficticio.yaml --variables config\ejemplos\variables_ficticias.yaml
.venv\Scripts\python scripts\generar_sintetico.py --semilla 1 --salida data\sintetico\historial.xlsx
.venv\Scripts\suficiencia datos diccionario config\ejemplos\diccionario_sintetico.yaml
.venv\Scripts\suficiencia datos importar data\sintetico\historial.xlsx --diccionario config\ejemplos\diccionario_sintetico.yaml --clave-efimera
.venv\Scripts\suficiencia objetivo validar config\ejemplos\objetivo_ficticio.yaml
.venv\Scripts\suficiencia objetivo construir data\sintetico\historial.xlsx --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --clave-efimera
.venv\Scripts\suficiencia objetivo demostracion   # casos ficticios escritos a mano y su estado de etiqueta
.venv\Scripts\suficiencia poblaciones construir data\sintetico\historial.xlsx --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --configuracion config\ejemplos\poblaciones_ficticio.yaml --clave-efimera
.venv\Scripts\python scripts\generar_sintetico.py --semilla 7 --estudiantes 1200 --ampliado --salida data\sintetico\ampliado.csv
.venv\Scripts\suficiencia experimentos preparar data\sintetico\ampliado.csv --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --poblaciones config\ejemplos\poblaciones_ampliado_ficticio.yaml --escenarios config\ejemplos\escenarios_ficticio.yaml --experimentos config\ejemplos\experimentos_ficticio.yaml --clave-efimera
.venv\Scripts\suficiencia experimentos entrenar data\sintetico\ampliado.csv --diccionario config\ejemplos\diccionario_sintetico.yaml --definicion config\ejemplos\objetivo_ficticio.yaml --poblaciones config\ejemplos\poblaciones_ampliado_ficticio.yaml --escenarios config\ejemplos\escenarios_ficticio.yaml --experimentos config\ejemplos\experimentos_ficticio.yaml --clave-efimera --escenario "T1|A+F" --familia lr
.venv\Scripts\suficiencia experimentos metricas --experimentos config\ejemplos\experimentos_ficticio.yaml
.venv\Scripts\suficiencia entorno           # entorno que se registra con cada corrida
.venv\Scripts\suficiencia registro ver decisiones
.venv\Scripts\suficiencia registro verificar  # comprueba que ningún registro fue modificado
.venv\Scripts\suficiencia protocolo demostracion  # ciclo del protocolo con un ejemplo FICTICIO, en un registro temporal
.venv\Scripts\suficiencia protocolo ver   # versiones del protocolo; hoy no hay ninguna
.venv\Scripts\suficiencia decisiones   # estado de DP-01 a DP-20: registradas o abiertas
.venv\Scripts\suficiencia ejecutar CU-05    # responde que el caso de uso aún no está implementado
```

## Visor de demostración (H2.D)

Un visor web de solo lectura que muestra en el navegador lo que el motor ya hace, siempre con datos sintéticos y configuraciones ficticias. Solo funciona en este equipo (`localhost`). Desde la carpeta del repositorio:

```powershell
.venv\Scripts\python scripts\generar_sintetico.py --semilla 1 --salida data\sintetico\historial.xlsx   # si aún no existe
.venv\Scripts\python -m streamlit run src\suficiencia\ui\visor.py
```

Abra `http://localhost:8501` en el navegador. Para detenerlo, `Ctrl+C` en la terminal. Decisiones en `docs/arquitectura/decisiones_h2_d.md`.

## Trabajar desde VS Code

Abra la carpeta del repositorio en VS Code (Archivo > Abrir carpeta). La primera vez, acepte instalar las extensiones recomendadas (Python y Ruff). VS Code usa solo el entorno del proyecto (`.venv`).

- **Tareas**: menú Terminal > Ejecutar tarea. Están numeradas: 1. Verificar todo, 2. Solo las pruebas, 3. Generar datos sintéticos, 4. Abrir el visor, 5. Demostración del protocolo, 6. Demostración del objetivo, 7. Estado del motor y 8. Verificar el registro. El visor se detiene con `Ctrl+C` en su terminal.
- **Pruebas**: el ícono del matraz, en la barra izquierda, lista todas las pruebas y permite correr una sola.
- **Depuración**: el ícono del triángulo con un insecto ofrece "Depurar el visor" y "Depurar la demostración del protocolo".

## Control de versiones

El equipo creó el primer commit el 28 de octubre de 2026. Para crear un repositorio nuevo desde una copia sin historial:

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
├── src/suficiencia/        # paquete: cinco capas y la línea de comandos (cli.py)
├── tests/                  # unit/ y architecture/
├── scripts/verificar.py    # todas las comprobaciones con un solo comando
└── docs/                   # especificación, diagramas, arquitectura, desarrollo y gestión
```

Detalle de cada carpeta y de los límites entre capas: `docs/arquitectura/estructura_repositorio.md`.

## Documentación

| Documento | Contenido |
| --- | --- |
| `docs/especificacion/especificacion_fase_1_v0.6.md` | Copia de referencia de la especificación vigente |
| `docs/especificacion/especificacion_fase_1_v0.5.md` | Copia de la v0.5, base de H2.1 a H2.3 y H2.7 |
| `docs/especificacion/especificacion_fase_1_v0.4.md` | Copia de la v0.4, base de H2.0 |
| `docs/diagramas/*.mmd` | Fuentes Mermaid de los cuatro diagramas |
| `docs/gestion/acta_cierre_fase_1_propuesta.md` | Propuesta de acta de cierre de la Fase 1 (sin firmar) |
| `docs/gestion/registro_h2_*.md` | Registro de cada hito: archivos, criterios y resultados reales |
| `docs/arquitectura/decisiones_h2_*.md` | Decisiones técnicas, alternativas, desviaciones y pendientes |
| `docs/arquitectura/estructura_repositorio.md` | Estructura y límites de los módulos |
| `docs/desarrollo/entorno_reproducible.md` | Creación y verificación del entorno |
| `docs/desarrollo/pruebas_h2_*.md` | Pruebas, comandos, criterios de aceptación y resultados de cada hito |
