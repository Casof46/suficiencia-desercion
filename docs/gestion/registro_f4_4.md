# Registro del hito F4.4: decisiones abiertas e historial de experimentos en el visor

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 13 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F4.2 |
| Base | Plan de la Fase 4 (sección 3, F4.4); especificación Fase 1 v0.6 (RF-UI-04, RF-M6-02) |
| Autorización | El equipo pidió empezar F4.4 el 13 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026). La asesoría no se ha pronunciado sobre el plan de la Fase 4 |
| Riesgo aceptado | Ninguno nuevo: no depende de decisiones abiertas |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `d117698`); aceptado por el equipo** el 13 de noviembre de 2026, con la revisión en Windows por medio de las pruebas de las páginas (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/trazabilidad/historial.py` | Decisiones de cada función del visor y comparación de registros (D-215, D-218) |
| `src/suficiencia/application/servicio_reportes.py`, `contratos.py` | `disponibilidad_funciones`, `historial_experimentos` y `comparar_experimentos` |
| `src/suficiencia/ui/visor.py`, `presentacion.py` | Botón desactivado en seis páginas; páginas "Decisiones" e "Historial de experimentos" (D-216 a D-218) |
| `workspace/tareas/verificar_f44.cmd` | Verificación en Windows |
| Pruebas y documentación | `test_historial.py`, `test_visor.py`, `pruebas_f4_4.md`, `decisiones_f4_4.md`, este registro |

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 971 pasan y 1 se omite (sin git). Revisión visual con Chromium de las páginas "Decisiones", "Historial de experimentos" y "Objetivo de deserción" (con el botón desactivado y las decisiones abiertas) |
| Windows 11, Python 3.13.0 (13 de noviembre de 2026) | Cinco `OK`; 6 contratos cumplidos; 971 pasan y 1 se omite (el sistema no permite crear enlaces simbólicos). Pruebas de las páginas de F4.4 por separado: 13 pasan. Estado de las decisiones en el registro del proyecto: 1 registrada (DP-16) y 19 abiertas, que es lo que muestra la página "Decisiones" en esa PC. Duró unos 27 minutos. Evidencia: `workspace\tareas\verificar_f44.log` |

## 4. Matriz de criterios de aceptación de F4.4

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Estado de las decisiones en el visor | Cumplido en Linux y Windows | `test_visor.py` |
| 2 | Funciones desactivadas cuando dependen de una decisión abierta | Cumplido en Linux y Windows | `test_visor.py`, `test_historial.py` |
| 3 | Historial de experimentos | Cumplido en Linux y Windows | `test_visor.py` |
| 4 | Revisión en Windows | Cumplido con las pruebas de las páginas (D-219) | `verificar_f44.log` |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. El visor no registra decisiones.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | 13 de noviembre de 2026 | Confirma la aceptación |
| Jorge | 13 de noviembre de 2026 | Acepta F4.4 y pide preparar el cierre de la Fase 4 (F4.5) |
