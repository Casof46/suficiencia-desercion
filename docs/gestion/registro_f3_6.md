# Registro del hito F3.6 — interpretabilidad

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F3.5 |
| Base | Plan de la Fase 3 (sección 2, F3.6); especificación Fase 1 v0.6 (M5; RF-M5-01 a 05; CU-09; PU-21; PI-13; DP-11) |
| Autorización | El equipo aceptó F3.5 y pidió empezar F3.6 el 12 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier). La misma respuesta aceptó agregar SHAP y LIME, que se instalan en el equipo y no envían datos a ningún servicio |
| Riesgo aceptado | Si la asesoría o el equipo cambian el alcance de la interpretabilidad, se ajusta; todo valor está parametrizado (DP-11) |
| Estado del hito | **Ejecutado y verificado en Linux.** Pendiente: verificación en Windows, commit del equipo y aceptación |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/evaluacion/interpretabilidad.py` | DP-11 como datos, explicador según la familia, muestras con semilla y agregación por variable y por bloque (D-175, D-177, D-178) |
| `src/suficiencia/experimentation/explicadores.py` | SHAP (lineal, de árboles o kernel) y LIME sobre el estimador congelado (D-176, D-179, D-180) |
| `src/suficiencia/application/servicio_interpretabilidad.py` | Servicio `explicar` (CU-09), con las comprobaciones de PI-13 (D-181 a D-183) |
| `src/suficiencia/persistence/corridas_archivos.py` | Guardado de las tablas de cada explicación con su huella |
| `src/suficiencia/domain/experimentos.py`, `config/ejemplos/experimentos_ficticio.yaml` | Sección obligatoria `interpretabilidad` (DP-11) |
| `src/suficiencia/application/demostracion_final.py` | La demostración explica las configuraciones congeladas (D-184) |
| `src/suficiencia/cli.py` | Comando `suficiencia evaluacion explicar` |
| `pyproject.toml`, `requirements.lock`, `src/suficiencia/persistence/entorno.py` | SHAP y LIME fijados con hashes; sus versiones se registran con cada corrida (D-174, D-185) |
| Pruebas y documentación | `pruebas_f3_6.md`, `decisiones_f3_6.md`, este registro |

**No se construyó:** estabilidad de las explicaciones (RF-M5-06), explicaciones con la prueba, gráficos (F3.7) ni uso de datos reales.

## 2. Dependencias añadidas

| Biblioteca | Versión | Motivo |
| --- | --- | --- |
| shap | 0.51.0 (`<0.52`) | Explicaciones SHAP (RF-M5-01, 03) |
| lime | 0.2.0.1 | Explicaciones locales LIME (RF-M5-02) |

Llegan como dependencias suyas, entre otras, numba, llvmlite, matplotlib y scikit-image. Todas están fijadas en `requirements.lock` con hashes y publicadas antes del 28 de octubre de 2026 (D-92). LIME se construye en el equipo durante la instalación (D-174).

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 875 pasan y 1 se omite (sin git) |
| Windows 11 | Pendiente |

La demostración explica las cuatro configuraciones que congela (selección, R0 y dos controles) solo con filas de desarrollo y sin agregar accesos a la prueba. Tarda unos 30 segundos en Linux. Las importancias dependen del generador sintético: no son una conclusión sobre el método ni sobre estudiantes reales.

## 4. Matriz de criterios de aceptación de F3.6

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | SHAP con el explicador según el modelo | Cumplido en Linux | PU-21; `test_explicadores.py` |
| 2 | LIME local | Cumplido en Linux | `test_explicadores.py`; PI-13 |
| 3 | Importancia por bloque (DP-11) | Cumplido en Linux | PU-21 |
| 4 | Solo configuraciones congeladas, con partición, muestra y semilla registradas | Cumplido en Linux | PI-13 |
| 5 | Sin nuevo acceso a la prueba | Cumplido en Linux | PI-15 |
| 6 | Verificación en Windows antes del commit | Pendiente | — |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. DP-11 entra como dato obligatorio.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | Pendiente | |
| Jorge | Pendiente | |
