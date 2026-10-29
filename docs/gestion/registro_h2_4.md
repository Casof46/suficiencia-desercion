# Registro del hito H2.4 — objetivo y estados de etiqueta

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 29 de octubre de 2026 |
| Solicitado por | Jorge, en nombre del equipo |
| Base | Especificación Fase 1 v0.6 (M1; RF-M1-06, 10 y 11; CU-03; PU-09 y PU-12, con el cambio CP-08); plan de la Fase 2 (paquete de cierre, sección E) |
| Autorización | El equipo pidió avanzar a H2.4 el 29 de octubre de 2026 sin esperar la conformidad de la asesoría con REC-03, que el equipo ya había aceptado con el cambio CP-08. Comunicado por Jorge; pendiente de confirmación de Javier |
| Riesgo aceptado | Si la asesoría pide cambios en REC-03 o en DP-18, este hito se ajusta |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `a572a4b`); aceptado por el equipo** el 29 de octubre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/datos/objetivo.py` | Definición del objetivo con los elementos de DP-01 y DP-18 obligatorios; categorías del catálogo de estados; constructor del estado de etiqueta por unidad y de la tabla completa; `para_modelado`; resumen de no etiquetables por cohorte y motivo (CP-08) |
| `src/suficiencia/persistence/objetivo_yaml.py` | Lectura de la definición en YAML: secciones obligatorias, `null` como decisión pendiente |
| `src/suficiencia/application/servicio_datos.py` | `validar_objetivo`, `construir_objetivo` (importación, auditoría y etiquetado) y `demostracion_objetivo`; CU-03 con avance |
| `src/suficiencia/application/demostracion_objetivo.py` | Diez historiales ficticios escritos a mano |
| `src/suficiencia/cli.py` | Comandos `objetivo validar`, `objetivo construir` y `objetivo demostracion` |
| `config/ejemplos/objetivo_ficticio.yaml` | Definición FICTICIA rotulada como tal |
| Pruebas y documentación | `pruebas_h2_4.md`, `decisiones_h2_4.md`, este registro |

**No se construyó:** ninguna definición de deserción, las poblaciones por ventana, la partición ni el análisis de sensibilidad. No se usaron datos reales.

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.12.3 (entorno de desarrollo) | Cinco `OK`; 6 contratos cumplidos; 432 pasan y 1 se omite (sin git) |
| Linux, Python 3.11, instalación limpia desde el bloqueo, con `git init` y `git add -A` | Cinco `OK`; 433 pasan |
| Windows 11, Python 3.13.0, PC de Jorge (29 de octubre de 2026) | Cinco `OK`; 6 contratos cumplidos; **433 pasan, 0 omitidas**. Prueba manual: `objetivo validar` sin definición se detuvo por DP-01; con el ejemplo mostró los 19 parámetros con su código DP y el catálogo; `objetivo demostracion` dio los diez estados esperados (por ejemplo, `MMAAAAAA` positivo con evento en el periodo 3 y `MAAMMMMM` negativo); `objetivo construir` etiquetó 300 unidades del Excel sintético, omitió la distribución de estados y guardó el resultado en `data/interim/`. Versionado en git y en GitHub (commit `a572a4b`) |

## 4. Matriz de criterios de aceptación de H2.4

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Sin todos los parámetros, el objetivo no se construye | Cumplido | Pruebas de definición incompleta; control negativo |
| 2 | Los casos sintéticos diseñados a mano producen el estado esperado | Cumplido | PU-09 |
| 3 | Los no etiquetables no entran al modelado y se cuentan por cohorte y motivo | Cumplido | PU-12; control negativo |
| 4 | Ninguna definición de deserción ni valores reales | Cumplido | Solo el ejemplo ficticio; DP-01 detiene el programa |
| 5 | Funciona en el sistema de trabajo | Cumplido | Linux con 3.11 y 3.12; Windows 11 con 3.13.0, pruebas y prueba manual |

## 5. Limitaciones

Ver `docs/arquitectura/decisiones_h2_4.md`, "No implementado en H2.4" y "Limitaciones conocidas".
