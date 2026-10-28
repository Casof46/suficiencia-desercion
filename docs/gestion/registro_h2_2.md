# Registro del hito H2.2 — ventanas, conjuntos, escenarios y verificador de fuga

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 28 de octubre de 2026 |
| Solicitado por | Jorge, en nombre del equipo |
| Base | Especificación Fase 1 v0.5 (M2; RF-M2-01 a RF-M2-04; PU-01, 02, 03, 18 y 19); plan de la Fase 2 (paquete de cierre, sección E) |
| Autorización | H2.1 a H2.3 autorizados el 28 de octubre de 2026 (acta, apartado 5.1), pendiente de confirmación de Javier |
| Estado del hito | **Ejecutado y verificado en Linux; pendiente de verificación en Windows y de aceptación por el equipo** |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/escenarios/modelo.py` | Bloques A, F, S y B; ventanas T0 a T3 con fecha índice obligatoria (DP-01d); catálogo; generación de los 8 conjuntos; variables con bloque y ventana mínima (DP-03); escenario con factibilidad |
| `src/suficiencia/domain/escenarios/construccion.py` | Constructor de los 32 escenarios y verificador de fuga independiente (`FugaTemporal`) |
| `src/suficiencia/domain/puertos.py` | Puertos nuevos `FuenteCatalogoVentanas` y `FuenteVariables` |
| `src/suficiencia/persistence/escenarios_yaml.py` | Lectura y validación de `config/escenarios.yaml` y de archivos de variables |
| `src/suficiencia/application/servicio_escenarios.py` | `generar_escenarios`: construye, verifica y devuelve la matriz |
| `src/suficiencia/cli.py` | Comando `suficiencia escenarios [--configuracion] [--variables] [--detalle]` |
| `config/escenarios.yaml` | Bloques, conjuntos y fechas índice pendientes (`null`, DP-01d) |
| `config/ejemplos/` | Catálogo y variables **ficticios**, declarados como tales |
| Pruebas y documentación | `pruebas_h2_2.md`, `decisiones_h2_2.md`, este registro |

**No se construyó:** poblaciones, partición, objetivo, diccionario real, fechas índice reales ni asignación real de variables. No se usaron datos.

## 2. Dependencias añadidas

| Paquete | Tipo | Motivo |
| --- | --- | --- |
| hypothesis | Desarrollo | Prueba basada en propiedades PU-02 (sección 5.1; D-39) |
| sortedcontainers | Indirecta | Requerida por hypothesis |

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11.17, 3.12.3 y 3.13.16, instalación limpia desde el bloqueo | Cinco `OK`; 6 contratos cumplidos; 205 pasan y 1 se omite (sin git) |
| Linux, Python 3.12.3, con `git init` y `git add -A` | 206 pasan; `.hypothesis/` no queda para versionar |
| Windows | **Pendiente**: debe ejecutarlo el equipo |

## 4. Matriz de criterios de aceptación de H2.2

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Exactamente 8 conjuntos y 32 escenarios | Cumplido | PU-01; prueba de la matriz |
| 2 | Ninguna variable posterior a su ventana aparece en ningún caso generado | Cumplido | PU-02 (propiedad), PU-03 (canario) y control negativo |
| 3 | Una configuración inválida se rechaza con mensaje en español | Cumplido | 14 casos de configuración inválida |
| 4 | Factibilidad por bloque | Cumplido | PU-19 |
| 5 | Sin fechas índice reales ni asignación real de variables | Cumplido | `config/escenarios.yaml` con `null`; ejemplos rotulados como ficticios |
| 6 | Funciona en el sistema de trabajo | **Pendiente en Windows** | — |

## 5. Limitaciones

Ver `docs/arquitectura/decisiones_h2_2.md`, "Limitaciones conocidas".
