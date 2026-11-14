# Registro del hito F3.4 — selección y evaluación final

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F3.3 |
| Base | Plan de la Fase 3 (sección 2, F3.4); especificación Fase 1 v0.6 (M4: RF-M4-05 a 09, RF-M4-12; CU-07, CU-08; PI-09, PI-10, PI-15; selección del modelo representativo) |
| Autorización | El equipo aceptó F3.3 y pidió empezar F3.4 el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |
| Riesgo aceptado | Si la asesoría cambia REC-01 a REC-03 o el diseño comparativo, la selección y la evaluación se ajustan; todo valor está parametrizado |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `df5d69c`); aceptado por el equipo** el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/evaluacion/seleccion.py` | Reglas de selección (DP-10) y de umbral (DP-06) como datos (D-155, D-156) |
| `src/suficiencia/domain/experimentos.py`, `config/ejemplos/experimentos_ficticio.yaml` | Secciones obligatorias `seleccion` y `umbral` |
| `src/suficiencia/experimentation/modelos.py` | Ajuste final con todo el desarrollo y predicción con un modelo ajustado (D-157) |
| `src/suficiencia/persistence/corridas_archivos.py` | Guardado y lectura con huella del modelo final |
| `src/suficiencia/application/servicio_experimentos.py` | Servicio `seleccionar` (D-158) |
| `src/suficiencia/application/servicio_evaluacion_final.py` | Evaluación final con apertura única, métricas, regla confirmatoria y control de repetición (D-159 a D-161) |
| `src/suficiencia/application/demostracion_final.py`, `config/ejemplos/protocolo_evaluacion_final_ficticio.yaml` | Demostración en un proyecto temporal con protocolo ficticio (D-162 a D-164) |
| `src/suficiencia/application/composicion.py` | Clave de sesión (D-163) y nuevos puertos |
| `src/suficiencia/cli.py` | `experimentos seleccionar`, `evaluacion final` y `evaluacion demostracion` |
| Pruebas y documentación | `pruebas_f3_4.md`, `decisiones_f3_4.md`, este registro |

**No se construyó:** R0 y controles (F3.5), procedimientos de multiplicidad ni uso de datos reales. En el registro del proyecto no se congeló ni se evaluó nada: no hay protocolo aprobado.

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 768 pasan y 1 se omite (sin git) |
| Windows 11, primera verificación (12 de noviembre de 2026) | Cinco `OK` salvo pruebas: 766 pasan y 2 fallan (la demostración y la prueba de cp1252, que la incluye). Causa: la carpeta temporal de Windows llega con el nombre corto y las rutas del registro se guardaban mal. Corregido (D-165) con una prueba que lo reproduce en Linux |
| Windows 11, Python 3.13.0, después de la corrección | Cinco `OK`; 6 contratos cumplidos; **768 pasan y 1 se omite** (la del enlace simbólico, que Windows no permite crear sin permisos especiales) en 7 min 41 s. La demostración termina correctamente con los nueve pasos esperados y un solo acceso a la prueba |

La demostración con el historial ampliado de 1200 estudiantes y un escenario tarda unos 20 segundos en Linux. Su resultado depende de los supuestos del generador sintético y del límite inventado del protocolo ficticio: no es una conclusión sobre el método.

## 4. Matriz de criterios de aceptación de F3.4

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Modelo por escenario (DP-10) y umbral (DP-06) solo con validación | Cumplido en Linux y Windows | RF-M4-07, RF-M4-08, PI-10 |
| 2 | Congelamiento con huella | Cumplido en Linux y Windows | PI-09 |
| 3 | Evaluación final con apertura única (demostración) | Cumplido en Linux y Windows | PI-15, RF-M4-09 |
| 4 | Regla de suficiencia sobre resultados reales del motor | Cumplido en Linux y Windows, solo con condiciones de umbral | D-161 |
| 5 | Verificación en Windows antes del commit | Cumplido, después de corregir D-165 | Sección 3 |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. DP-06 y DP-10 entran como datos obligatorios; DP-08 solo aparece en el protocolo ficticio de la demostración.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | 13 de noviembre de 2026 | Confirma la aceptación |
| Jorge | 12 de noviembre de 2026 | Acepta F3.4 y pide empezar F3.5 |
