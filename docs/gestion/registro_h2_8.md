# Registro del hito H2.8 — CLI mínima y cierre de la Fase 2

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 11 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, después de aceptar H2.D y H2.6 |
| Base | Plan de la Fase 2 (paquete de cierre, sección E, H2.8); especificación Fase 1 v0.6 (CU-03, CU-04, CU-05; PI-11; RF-M6-05) |
| Autorización | El equipo aceptó H2.D y H2.6 el 11 de noviembre de 2026 y pidió seguir. Comunicado por Jorge; pendiente de confirmación de Javier |
| Riesgo aceptado | Los de H2.4 a H2.6: si la asesoría pide cambios en REC-01 a REC-03, esos hitos y sus pruebas de aceptación se ajustan |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; pendientes la evidencia de Windows (pytest completo e instalación limpia) y la aceptación por el equipo** |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `config/decisiones_metodologicas.yaml` | Catálogo de DP-01 a DP-20: nombre, quién decide y antes de qué; sin decisiones ni valores |
| `src/suficiencia/domain/trazabilidad/decisiones.py` | Cruce del catálogo con el registro de decisiones |
| `src/suficiencia/application/servicio_reportes.py`, `contratos.py`, `composicion.py` | `estado_decisiones` |
| `src/suficiencia/cli.py` | Comando `suficiencia decisiones` |
| `tests/acceptance/` | Pruebas de aceptación de CU-03, CU-04 y CU-05 y PI-11 determinista |
| `docs/gestion/informe_cierre_fase_2.md` | Informe de cierre de la Fase 2 con limitaciones |
| Pruebas y documentación | `pruebas_h2_8.md`, `decisiones_h2_8.md`, este registro |

**No se construyó:** entrenamiento de modelos, más interfaz Streamlit ni uso de datos reales.

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 599 pasan y 1 se omite (sin git) |
| Linux, Python 3.12, clon nuevo e instalación siguiendo el README | Cinco `OK`; **600 pasan** (`evidencia_fase_2/instalacion_limpia_linux.txt`) |
| Windows 11, Python 3.13.0 (11 de noviembre de 2026) | Cinco `OK`; 6 contratos cumplidos; **600 pasan** |
| Windows 11, clon nuevo desde GitHub e instalación siguiendo el README | **Pendiente** |

## 4. Matriz de criterios de aceptación de H2.8

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Salida completa de pytest adjunta | **Pendiente** | `evidencia_fase_2/pytest_windows.txt` |
| 2 | Instalación verificada desde el README en un entorno limpio | Linux: cumplido (600 pasan). Windows: **pendiente** | `evidencia_fase_2/` |
| 3 | Lista de limitaciones conocidas | Cumplido | Informe de cierre, sección 6 |
| 4 | Criterios de aceptación de CU-03 a CU-05 sobre datos sintéticos | Cumplido en Linux y Windows | `tests/acceptance/` |
| 5 | PI-11 en las partes deterministas | Cumplido en Linux y Windows | `tests/acceptance/` |
