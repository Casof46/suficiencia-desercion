# Registro del hito H2.D — visor de demostración local

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 29 de octubre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, porque el profesor pidió ver la aplicación funcionando |
| Base | Contexto maestro (Streamlit como interfaz local; principios 1, 3, 10 y 13); arquitectura de capas de la especificación v0.6 (RF-UI-02) |
| Autorización | Pedido del equipo del 29 de octubre de 2026, fuera del orden del plan de la Fase 2. Comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026 |
| Riesgo aceptado | Ninguno metodológico: el visor no decide nada. Si la asesoría cambia REC-01 o REC-03, el visor muestra lo que muestren H2.4 y H2.5 ajustados |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `9ae248a`); aceptado por el equipo** el 11 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/ui/visor.py` | Seis páginas: inicio, datos y auditoría, escenarios, objetivo de deserción, poblaciones y partición, registro |
| `src/suficiencia/ui/presentacion.py` | Conversión de contratos a tablas y a la línea de tiempo de cada historial; sin Streamlit |
| `src/suficiencia/application/contratos.py` y `servicio_escenarios.py` | Campo `origen` en `SolicitudLeerPrueba` (D-97) |
| `tests/conftest.py`, `tests/unit/test_sin_red.py` | Bloqueo de red que permite solo la interfaz local (D-99) |
| `.streamlit/config.toml` | Solo localhost, sin "Deploy", tema del visor (D-98) |
| `pyproject.toml`, `requirements.lock` | Grupo opcional `ui` con Streamlit (D-91, D-92) |
| Pruebas y documentación | `test_visor.py`, prueba de localhost, `pruebas_h2_d.md`, `decisiones_h2_d.md`, este registro |

## 2. Dependencias añadidas

Streamlit 1.66.0 y sus dependencias (entre ellas pyarrow, altair, starlette y uvicorn), todas fijadas con hash en `requirements.lock`.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11, instalación desde el bloqueo | Cinco `OK`; 6 contratos cumplidos; 484 pasan. Revisión visual con capturas del visor en Chromium |
| Windows 11, Python 3.13.0, primer intento (4 de noviembre de 2026) | 11 fallan y 473 pasan: el bloqueo de red de las pruebas impedía a asyncio usar la interfaz local (127.0.0.1) |
| Linux, Python 3.11, tras la corrección D-99 | Las pruebas nuevas de `test_sin_red.py` pasan, también con el par de sockets de respaldo que usa Windows |
| Windows 11, Python 3.13.0, tras la corrección D-99 (4 de noviembre de 2026) | Cinco `OK`; 6 contratos cumplidos; **486 pasan** |

## 4. Matriz de criterios de aceptación de H2.D

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | El visor muestra lo que el motor ya hace, sin calcular nada propio | Cumplido | D-93; contrato `ui-solo-aplicacion` |
| 2 | No acepta datos reales ni archivos desde el navegador | Cumplido | D-94; marca sintética exigida por el motor |
| 3 | La prueba sigue sellada desde la web y el intento queda registrado con su origen | Cumplido | `test_visor.py`; D-97 |
| 4 | Nada sale del equipo | Cumplido | D-98; prueba de localhost |
| 5 | Funciona en el sistema de trabajo | Cumplido | Windows 11: 486 pasan tras D-99 |
