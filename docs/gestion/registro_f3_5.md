# Registro del hito F3.5 — comparación con la referencia R0

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F3.4 |
| Base | Plan de la Fase 3 (sección 2, F3.5); especificación Fase 1 v0.6 (RF-M4-15 a 21; CU-12; CMP-1 a CMP-4; C1 a C8; PU-22 a PU-27; PI-15; DP-19, DP-20) |
| Autorización | El equipo aceptó F3.4 y pidió empezar F3.5 el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |
| Riesgo aceptado | Si la asesoría cambia el diseño comparativo, la comparación se ajusta; todo valor está parametrizado |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `a6e1d90`); aceptado por el equipo** el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/evaluacion/comparacion.py` | R0 y controles, no inferioridad, anticipación, reducción, cobertura y estados C1 a C8 (D-166, D-170 a D-172) |
| `src/suficiencia/domain/evaluacion/metricas.py` | Réplicas de la diferencia pareada |
| `src/suficiencia/domain/experimentos.py`, `config/ejemplos/experimentos_ficticio.yaml` | Secciones obligatorias `referencia` (DP-19) y `comparacion` (DP-20) |
| `src/suficiencia/application/servicio_experimentos.py` | R0 y controles en la selección (D-167) |
| `src/suficiencia/application/servicio_evaluacion_final.py` | Predicciones de prueba guardadas (D-168) y servicio `comparar` (D-169) |
| `src/suficiencia/persistence/corridas_archivos.py` | Guardado y lectura con huella de las predicciones de prueba |
| `src/suficiencia/application/demostracion_final.py` | La demostración incluye R0, controles y comparación (D-173) |
| `src/suficiencia/cli.py` | Comando `suficiencia evaluacion comparar` |
| Pruebas y documentación | `pruebas_f3_5.md`, `decisiones_f3_5.md`, este registro |

**No se construyó:** R-max, estabilidad (CMP-5), cobertura temprana dentro de la comparación ni uso de datos reales.

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 812 pasan y 1 se omite (sin git) |
| Windows 11, Python 3.13.0 (12 de noviembre de 2026) | Cinco `OK`; 6 contratos cumplidos; 812 pasan y 1 se omite (el sistema no permite crear enlaces simbólicos); la demostración termina con el mismo estado que en Linux (`C3_no_inferioridad_no_demostrada`, sin significado por ser datos sintéticos y protocolo ficticio) y un solo acceso permitido a la prueba. Evidencia: `workspace\tareas\verificar_f35.log` |

La demostración con un escenario entrena tres (el pedido, el de R0 y el de R-ven), congela cuatro configuraciones (selección, R0, R0-fam y R-ven), las evalúa en un solo acceso y compara sin nuevo acceso. Tarda unos 30 segundos en Linux. Su estado depende del generador sintético y de los valores inventados: no es una conclusión sobre el método.

## 4. Matriz de criterios de aceptación de F3.5

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | R0 y controles (DP-19) | Cumplido en Linux y Windows | PU-22, PU-23 |
| 2 | Diferencias pareadas y no inferioridad (DP-20) | Cumplido en Linux y Windows | PU-24, PU-25 |
| 3 | Anticipación y reducción de información | Cumplido en Linux y Windows | PU-26 |
| 4 | Estados C1 a C8 | Cumplido en Linux y Windows | PU-27 |
| 5 | Sin nuevo acceso a la prueba | Cumplido en Linux y Windows | PI-15 |
| 6 | Verificación en Windows antes del commit | Cumplido | `verificar_f35.log` |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. DP-19 y DP-20 entran como datos obligatorios.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | 13 de noviembre de 2026 | Confirma la aceptación |
| Jorge | 12 de noviembre de 2026 | Acepta F3.5 y pide empezar F3.6 |
