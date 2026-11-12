# Registro del hito H2.6 — protocolo, desviaciones y congelamiento

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 4 de noviembre de 2026; ajuste el 11 de noviembre de 2026 (D-118 a D-120) |
| Solicitado por | Jorge, en nombre del equipo |
| Base | Especificación Fase 1 v0.6 (M4; RF-M4-04, 05, 06, 09, 12 y 13; CU-05, CU-07 y CU-08; PU-04, PU-05, PU-06 y PI-09); plan de la Fase 2 (paquete de cierre, sección E) |
| Autorización | Jorge pidió construir H2.6 el 4 de noviembre de 2026, después de cerrar H2.D. El equipo aceptó REC-02 el 29 de octubre de 2026; falta la conformidad de la asesoría. Comunicado por Jorge; pendiente de confirmación de Javier |
| Riesgo aceptado | Si la asesoría pide cambios en REC-02 (protocolo en cuatro etapas), este hito se ajusta |
| Estado del hito | **Ejecutado y verificado en Linux y Windows, con el ajuste del 11 de noviembre; versionado en git y en GitHub (commits `05fbed9` y `b4f3c1e`); aceptado por el equipo** el 11 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier). REC-02 sigue pendiente de la conformidad de la asesoría (ver "Riesgo aceptado") |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/evaluacion/suficiencia.py` | Motor de la regla: criterio como datos, condiciones de umbral y de no inferioridad, interfaz de multiplicidad sin ningún procedimiento, desempate y los tres resultados (escenario suficiente, ninguno cumple, empate sin resolver) |
| `src/suficiencia/domain/evaluacion/protocolo.py` | Contenido del protocolo con su huella; versiones (borrador, aprobado, reemplazado) reconstruidas del registro; aprobación con huella revisada; desviaciones; modos exploratorio y confirmatorio |
| `src/suficiencia/domain/evaluacion/congelamiento.py` | Configuración congelada con huella (RF-M4-12) y comprobaciones previas a la evaluación final |
| `src/suficiencia/persistence/repositorio_sqlite.py`, `protocolo_yaml.py` | Tablas `protocolos`, `desviaciones` y `congelamientos` (esquema 2); lectura de YAML |
| `src/suficiencia/application/servicio_protocolo.py`, `servicio_experimentos.py`, `servicio_evaluacion_final.py`, `registro_corridas.py`, `demostracion_protocolo.py` | CU-05 (borrador, aprobación, consulta y demostración), congelamiento (CU-07), comprobaciones de CU-08 y rechazo de corridas confirmatorias sin protocolo |
| `src/suficiencia/cli.py` | Comandos `protocolo borrador`, `aprobar`, `ver` y `demostracion`; `registro ver` con los tipos nuevos |
| `config/ejemplos/protocolo_ficticio.yaml` | Protocolo FICTICIO rotulado como tal; el programa no lo aprueba en el registro del proyecto |
| `.vscode/` | Configuración de VS Code: intérprete, pruebas, tareas y depuración (D-120) |
| Pruebas y documentación | `pruebas_h2_6.md`, `decisiones_h2_6.md`, este registro |

**No se construyó:** ningún criterio real, ni la evaluación final que abre la prueba, ni R0. No se usaron datos reales.

## 1.1. Ajuste del 11 de noviembre de 2026

Al revisar el informe de avance del OE3 se vio que el motor no podía expresar dos partes de la regla que propone el manuscrito: la no inferioridad frente a un número de comparadores que cambia según la ventana, y un desempate por orden de conjuntos. Se ajustó el motor (D-118 y D-119) sin adoptar esa regla ni ningún valor: DP-08 sigue abierta. Se añadió además la configuración de VS Code (D-120).

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11, instalación limpia desde el bloqueo, sin git | Cinco `OK`; 6 contratos cumplidos; 568 pasan y 1 se omite (sin git) |
| Windows 11, Python 3.13.0 (4 de noviembre de 2026), sobre el commit `9ae248a` | Cinco `OK`; 6 contratos cumplidos; **569 pasan**. `protocolo demostracion` termina bien y, después, `protocolo ver` confirma que el registro del proyecto no tiene ninguna versión del protocolo |
| Linux, Python 3.11, con el ajuste del 11 de noviembre (sin git) | Cinco `OK`; 583 pasan y 1 se omite (sin git) |
| Windows 11, Python 3.13.0, con el ajuste del 11 de noviembre, sobre el commit `05fbed9` | Cinco `OK`; 6 contratos cumplidos; **584 pasan**; la demostración termina bien |

## 4. Matriz de criterios de aceptación de H2.6

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Ningún criterio, umbral ni procedimiento de multiplicidad por defecto en el código ni en `config/` | Cumplido | `test_sin_criterio_por_defecto.py`; control negativo |
| 2 | Un protocolo aprobado no puede editarse | Cumplido | PU-06; control negativo |
| 3 | La evaluación rechaza una huella distinta | Cumplido | PI-09; control negativo |
| 4 | Sin criterios reales, métrica primaria ni procedimiento de multiplicidad elegido | Cumplido | Solo el ejemplo ficticio; DP-08f detiene la regla |
| 5 | Funciona en el sistema de trabajo | Cumplido | Windows 11: 569 pasan antes del ajuste y 584 después |

## 5. Limitaciones

Ver `docs/arquitectura/decisiones_h2_6.md`, "No implementado en H2.6" y "Limitaciones conocidas".
