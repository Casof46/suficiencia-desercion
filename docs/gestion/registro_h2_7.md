# Registro del hito H2.7 — trazabilidad y registro

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 29 de octubre de 2026 |
| Solicitado por | Jorge, en nombre del equipo |
| Base | Especificación Fase 1 v0.5 (M6; RF-M6-01, 03, 05 y 06; RNF-05, 16 y 17; PI-03, 04, 05 y 12); plan de la Fase 2 (paquete de cierre, sección E) |
| Autorización | H2.7 autorizado y DP-16 decidida (SQLite) el 29 de octubre de 2026 (acta), pendiente de confirmación de Javier |
| Estado del hito | **Ejecutado y verificado en Linux; pendiente de verificación en Windows y de aceptación por el equipo** |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/trazabilidad/registros.py` | Registros de experimento, decisión y acceso; entorno; cadena de huellas y su verificación |
| `src/suficiencia/domain/trazabilidad/filtro.py` | Filtro de identificadores para exportaciones |
| `src/suficiencia/domain/puertos.py` | Puertos nuevos `RepositorioRegistros` y `CapturadorEntorno` |
| `src/suficiencia/persistence/repositorio_sqlite.py` | Registro SQLite de solo agregar, con disparadores y huellas encadenadas (DP-16) |
| `src/suficiencia/persistence/entorno.py` | Captura del entorno (RNF-17) |
| `src/suficiencia/persistence/exportacion.py` | Exportación a CSV y Excel con filtro |
| `src/suficiencia/application/registro_corridas.py` | Registrador de corridas exitosas y fallidas |
| `src/suficiencia/application/servicio_reportes.py` | Entorno, registro de decisiones, consulta, verificación, exportación y demostración (parte de CU-10) |
| `src/suficiencia/cli.py` | Comandos `entorno` y `registro` (`decision`, `ver`, `verificar`, `exportar`, `demostracion`) |
| `docs/decisiones/` | Ficha versionada de DP-16 |
| Pruebas y documentación | `pruebas_h2_7.md`, `decisiones_h2_7.md`, este registro |

**No se construyó:** reportes de experimento ni el reporte comparativo, ni el sello de la prueba que escribirá los accesos (H2.5). No se usaron datos.

## 2. Dependencias añadidas

Ninguna. sqlite3 viene incluido en Python.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.12.3 (entorno de desarrollo) y 3.11.17 (instalación limpia desde el bloqueo) | Cinco `OK`; 6 contratos cumplidos; 325 pasan y 1 se omite (sin git) |
| Linux, Python 3.11.17, con `git init` y `git add -A` | 326 pasan |
| Windows | **Pendiente**: debe ejecutarlo el equipo |

## 4. Matriz de criterios de aceptación de H2.7

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Los registros solo admiten agregar | Cumplido | Disparadores, cadena de huellas y controles negativos |
| 2 | Ninguna exportación contiene identificadores | Cumplido | PI-04 |
| 3 | La suite completa pasa sin red | Cumplido | PI-05 |
| 4 | PI-03 y PI-12 con corridas simuladas | Cumplido | Prueba de integración |
| 5 | Sin reportes de resultados científicos | Cumplido | No existen |
| 6 | Funciona en el sistema de trabajo | **Pendiente en Windows** | — |

## 5. Limitaciones

Ver `docs/arquitectura/decisiones_h2_7.md`, "No implementado en H2.7" y "Limitaciones conocidas".
