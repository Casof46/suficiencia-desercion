# Registro del hito H2.5 — poblaciones, partición cronológica y sello de la prueba

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 29 de octubre de 2026 |
| Solicitado por | Jorge, en nombre del equipo |
| Base | Especificación Fase 1 v0.6 (M2; RF-M2-05 a 09 y 12; CU-04 y CU-11; PU-10, 11, 13 y 17; PI-02 y PI-07); plan de la Fase 2 (paquete de cierre, sección E) |
| Autorización | El equipo pidió seguir con H2.5 el 29 de octubre de 2026, sin esperar la conformidad de la asesoría con REC-01. El equipo ya había aceptado REC-01 con un plan de contingencia obligatorio en DP-05, y DP-08h con el piloto permitido. Comunicado por Jorge; pendiente de confirmación de Javier |
| Riesgo aceptado | Si la asesoría pide cambios en REC-01 o en DP-08h, este hito se ajusta |
| Estado del hito | **Ejecutado y verificado en Linux; pendiente de verificación en Windows y de aceptación por el equipo** |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/escenarios/poblaciones.py` | Periodos índice; poblaciones D1, D2 y D3 por ventana; exclusiones por motivo; descriptivos por cohortes; seguimiento por cohorte (CU-11 parte A); configuración de poblaciones |
| `src/suficiencia/domain/escenarios/particion.py` | Definición de la partición con plan de contingencia y piloto; división por cohortes; sello de la prueba con registro de accesos |
| `src/suficiencia/domain/datos/objetivo.py` | Preparación de unidades compartida con las poblaciones; periodo necesario para etiquetar |
| `src/suficiencia/persistence/poblaciones_yaml.py` | Lectura de la configuración: campos obligatorios, `null` como decisión pendiente |
| `src/suficiencia/persistence/particion_archivos.py` | Índices y manifiesto de cada partición en `workspace/particiones/`, con huellas |
| `src/suficiencia/application/servicio_escenarios.py` | `construir_poblaciones` y `leer_prueba`; CU-04 y CU-11 con avance |
| `src/suficiencia/cli.py` | Comandos `poblaciones construir` y `poblaciones leer-prueba` |
| `config/ejemplos/poblaciones_ficticio.yaml` | Configuración FICTICIA rotulada como tal |
| Pruebas y documentación | `pruebas_h2_5.md`, `decisiones_h2_5.md`, este registro |

**No se construyó:** la elección del diseño principal ni de las cohortes reales, la evaluación final ni los folds de validación. No se usaron datos reales.

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.12.3 (entorno de desarrollo) | Cinco `OK`; 6 contratos cumplidos; 469 pasan y 1 se omite (sin git) |
| Linux, Python 3.11, instalación limpia desde el bloqueo, con `git init` y `git add -A` | Cinco `OK`; 470 pasan |
| Windows | **Pendiente**: debe ejecutarlo el equipo |

## 4. Matriz de criterios de aceptación de H2.5

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Los tres diseños producen las poblaciones esperadas | Cumplido | PU-10, PU-11, cobertura D3 |
| 2 | Ningún componente distinto de la evaluación final obtiene filas de prueba | Cumplido | PI-02; control negativo |
| 3 | Ningún conteo que dependa del resultado se calcula sobre la prueba | Cumplido | PU-13; control negativo |
| 4 | Toda cohorte de prueba es posterior a las de desarrollo | Cumplido | PI-07 (parte de la partición); control negativo |
| 5 | Sin diseño principal ni cohortes reales | Cumplido | Solo el ejemplo ficticio; DP-04 detiene el programa |
| 6 | Funciona en el sistema de trabajo | **Pendiente en Windows** | — |

## 5. Limitaciones

Ver `docs/arquitectura/decisiones_h2_5.md`, "No implementado en H2.5" y "Limitaciones conocidas".
