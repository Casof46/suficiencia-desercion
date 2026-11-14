# Registro del hito F3.7 — resultados en el visor y reporte

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F3.6 |
| Base | Plan de la Fase 3 (sección 2, F3.7); especificación Fase 1 v0.6 (RF-M6-03, RF-M6-04, RF-M6-07; RF-UI-02, RF-UI-03; RNF-19; PI-16) |
| Autorización | El equipo aceptó F3.6, pidió empezar F3.7 y aprobó agregar Plotly el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |
| Riesgo aceptado | La página de resultados y el reporte usan la demostración con protocolo ficticio; cuando exista un protocolo aprobado se agregará el reporte leído del registro |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `6769282`); aceptado por el equipo** el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/trazabilidad/rotulo.py` | Regla del rótulo de datos sintéticos (D-187) |
| `src/suficiencia/application/reporte_resultados.py` | Reporte de evaluación final, comparación e interpretabilidad (D-188) |
| `src/suficiencia/application/servicio_reportes.py`, `src/suficiencia/persistence/exportacion.py` | Exportación rotulada del reporte y rótulo en la exportación de experimentos (D-189, D-190) |
| `src/suficiencia/application/servicio_evaluacion_final.py`, `servicio_interpretabilidad.py`, `contratos.py` | Origen de los datos en los registros y en los resultados |
| `src/suficiencia/cli.py` | Opción `--reporte` de `suficiencia evaluacion demostracion` (D-191) |
| `src/suficiencia/ui/graficos.py`, `visor.py`, `presentacion.py` | Página "Resultados (Fase 3)" con gráficos Plotly rotulados y descargas (D-192 a D-194) |
| `pyproject.toml`, `requirements.lock` | Plotly en el grupo `ui` (D-186) |
| Pruebas y documentación | `pruebas_f3_7.md`, `decisiones_f3_7.md`, este registro |

**No se construyó:** reporte leído del registro para evaluaciones del proyecto, interfaz definitiva (RF-UI-01, RF-UI-04) ni historial comparativo en la interfaz (RF-M6-02).

## 2. Dependencias añadidas

| Biblioteca | Versión | Motivo |
| --- | --- | --- |
| plotly | 7.1.0 | Gráficos del visor (RF-UI-03) |

Fijada en `requirements.lock` con hashes y publicada antes del 28 de octubre de 2026 (D-92). Sus dependencias ya estaban fijadas.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 902 pasan y 1 se omite (sin git) |
| Windows 11, Python 3.13.0 (12 de noviembre de 2026) | Plotly 7.1.0 instalado desde `requirements.lock`; cinco `OK`; 6 contratos cumplidos; 902 pasan y 1 se omite (el sistema no permite crear enlaces simbólicos); la demostración exportó su reporte rotulado a `reports\demostracion_f37` (texto, cinco CSV y Excel), que empieza con la leyenda de datos sintéticos. Evidencia: `workspace\tareas\verificar_f37.log` |

La página de resultados se revisó en Linux con Chromium: aviso, cuatro gráficos con el rótulo en el título y la leyenda al pie, tabla de explicaciones locales numeradas y dos descargas. Las cifras dependen del generador sintético y de valores inventados.

## 4. Matriz de criterios de aceptación de F3.7

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Páginas de resultados con rótulo sintético | Cumplido en Linux y Windows | `test_visor.py`; PI-16 |
| 2 | Exportación rotulada; sin rótulo se rechaza | Cumplido en Linux y Windows | PI-16 |
| 3 | Rótulo en los registros | Cumplido en Linux y Windows | PI-16 |
| 4 | Gráficos con Plotly | Cumplido en Linux y Windows | RF-UI-03 |
| 5 | Verificación en Windows antes del commit | Cumplido | `verificar_f37.log` |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | 13 de noviembre de 2026 | Confirma la aceptación |
| Jorge | 12 de noviembre de 2026 | Acepta F3.7 y pide preparar el informe de cierre de la Fase 3 |
