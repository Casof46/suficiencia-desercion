# Registro del hito F3.1 — datos listos para entrenar sin fuga

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 11 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, después de cerrar la Fase 2 |
| Base | Plan de la Fase 3 (sección 2, F3.1); especificación Fase 1 v0.6 (M3: RF-M3-02, RF-M3-03; PI-01, PI-07, PI-08, PU-12) |
| Autorización | El equipo aprobó empezar la Fase 3 por F3.1 el 11 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier). La asesoría dio su conformidad con el informe de cierre de la Fase 2; no se ha pronunciado sobre el plan de la Fase 3 |
| Riesgo aceptado | Si la asesoría cambia REC-01 a REC-03 o el diseño comparativo, las matrices y los folds se ajustan; todo valor está parametrizado |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `0917025`); aceptado por el equipo** el 11 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `tests/fixtures/generador_sintetico.py`, `scripts/generar_sintetico.py` | Historial ampliado de 12 cohortes (`--ampliado`) y corrección del reingreso (D-128) |
| `config/ejemplos/poblaciones_ampliado_ficticio.yaml` | EJEMPLO FICTICIO: periodos índice, D1 como diseño principal, 8 cohortes de desarrollo, 2 de prueba y 2 excluidas |
| `config/ejemplos/experimentos_ficticio.yaml` | EJEMPLO FICTICIO: validación (DP-07), lectura de cada variable (DP-03) y dos perfiles de preprocesamiento (DP-12) |
| `src/suficiencia/domain/escenarios/matrices.py` | Matrices por escenario con corte en el periodo índice (D-129) |
| `src/suficiencia/domain/experimentos.py` | Configuración de experimentos y folds cronológicos (D-130, D-132) |
| `src/suficiencia/experimentation/pipelines.py` | Preprocesamiento con scikit-learn ajustado dentro de cada fold (D-132) |
| `src/suficiencia/persistence/experimentos_yaml.py` | Lectura de la configuración de experimentos |
| `src/suficiencia/application/preparacion_desarrollo.py`, `servicio_experimentos.py`, `contratos.py`, `composicion.py` | Preparación del desarrollo (D-133, D-134, D-135) |
| `src/suficiencia/cli.py` | Comando `suficiencia experimentos preparar` |
| Pruebas y documentación | `pruebas_f3_1.md`, `decisiones_f3_1.md`, este registro |

**No se construyó:** modelos, métricas, selección ni uso de datos reales.

## 2. Dependencias añadidas

scikit-learn 1.9.1 y sus dependencias joblib 1.6.0, scipy (1.17.1 con Python 3.11; 1.18.1 con 3.12 o más), threadpoolctl 3.7.0 y cloudpickle 3.1.2, en `requirements.lock` con hashes (D-127). **Hay que reinstalar el entorno desde el bloqueo.**

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 644 pasan y 1 se omite (sin git) |
| Windows 11, Python 3.13.0 (11 de noviembre de 2026), después de reinstalar desde `requirements.lock` | Cinco `OK`; 6 contratos cumplidos; **645 pasan** (8 min). `experimentos preparar` con el historial ampliado (semilla 7) termina correctamente con los mismos 6 folds, 28 escenarios preparados y 4 no factibles que en Linux |

Con el historial ampliado de ejemplo (1200 estudiantes, semilla 7) y las configuraciones ficticias, `experimentos preparar` da 6 folds, 28 escenarios preparados y 4 no factibles. Son números del generador sintético; no dicen nada sobre estudiantes reales ni sobre el método.

Las 4 advertencias que muestra pytest vienen de Streamlit (una función de pandas que dejará de existir) en las pruebas del visor; ya aparecían en la Fase 2 y no son fallas.

## 4. Matriz de criterios de aceptación de F3.1

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Generador sintético ampliado (12 cohortes) | Cumplido en Linux y Windows | `test_datos_sinteticos.py` |
| 2 | Matrices por ventana y escenario solo con desarrollo | Cumplido en Linux y Windows | `test_matrices.py`, `test_preparacion_desarrollo.py` |
| 3 | Folds rolling-origin por cohortes, DP-07 como datos | Cumplido en Linux y Windows | `test_experimentos.py` |
| 4 | Preprocesamiento dentro de cada fold, DP-12 como datos | Cumplido en Linux y Windows | `test_preparacion_desarrollo.py` |
| 5 | PI-01, PI-07 (folds), PI-08 (cohortes por fold), PU-12 | Cumplido en Linux y Windows | `pruebas_f3_1.md` |
| 6 | Verificación en Windows antes del commit | Cumplido | Sección 3 |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. DP-03, DP-07 y DP-12 entran como datos obligatorios; sin `config/experimentos.yaml` el programa se detiene con DP-07.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | Pendiente de confirmación | |
| Jorge | 11 de noviembre de 2026 | Acepta F3.1 y pide empezar F3.2 |
