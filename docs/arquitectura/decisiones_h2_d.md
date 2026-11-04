# Decisiones técnicas del hito H2.D — visor de demostración local

Son decisiones **técnicas y reversibles** tomadas para mostrar el motor en el navegador. H2.D **no está en el plan de la Fase 2**: lo pidió el equipo el 29 de octubre de 2026, entre H2.5 y H2.6, porque el profesor pidió ver la aplicación funcionando. No resuelve ninguna decisión metodológica, no adelanta la interfaz definitiva y no usa datos reales. Continúan la numeración de `decisiones_h2_5.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-91 | Streamlit entra como dependencia opcional (`pip install` del grupo `ui`, fijado en `requirements.lock`). Sale de la lista de bibliotecas postergadas junto con pyarrow, que Streamlit instala como dependencia propia. Plotly sigue postergado | Instalar Streamlit fuera del bloqueo | El entorno debe seguir siendo reproducible con hashes (RNF-10) |
| D-92 | Los paquetes nuevos del bloqueo se fijaron en versiones publicadas al menos dos semanas antes (Streamlit 1.66.0, entre otros). Las versiones ya fijadas no cambiaron | Tomar la última versión | Reduce el riesgo de una versión recién publicada con errores o código malicioso |
| D-93 | El visor es de **solo lectura** sobre los servicios de aplicación: `src/suficiencia/ui/visor.py` (páginas) y `presentacion.py` (tablas y HTML, sin Streamlit). No calcula nada metodológico | Llamar al dominio desde la interfaz | RF-UI-02 y contrato `ui-solo-aplicacion` |
| D-94 | Rutas fijas a los ejemplos ficticios (`config/ejemplos/`) y al historial sintético (`data/sintetico/historial.xlsx`). No hay carga de archivos desde el navegador | Permitir subir archivos | Evita que alguien cargue datos reales en la demostración; el motor además exige la marca sintética (DP-02) |
| D-95 | Un aviso fijo en todas las páginas dice que los datos son sintéticos y las configuraciones ficticias, y que DP-01, DP-04 y DP-05 siguen abiertas | Avisar solo en el inicio | Quien vea una captura de pantalla suelta no debe confundirla con un resultado |
| D-96 | Construir poblaciones solo ocurre al pulsar un botón, porque guarda una partición nueva en `workspace/` | Construirlas al abrir la página | La operación tiene efectos (archivos y registro) |
| D-97 | `SolicitudLeerPrueba` tiene un campo `origen` (`linea_de_comandos` por omisión, o `visor`). Desde el visor el intento queda registrado como `consulta_desde_el_visor` | Registrar todo como línea de comandos | El registro de accesos debe decir la verdad sobre quién intentó leer la prueba |
| D-98 | `.streamlit/config.toml`: escucha solo en `localhost`, sin abrir el navegador ni pedir correo (`headless`), sin botón "Deploy" y sin estadísticas de uso | Valores por omisión de Streamlit | Principio 10 del contexto maestro y RNF-06: nada sale del equipo |
| D-99 | En las pruebas, el bloqueo de red permite conectar solo a la interfaz local del equipo (127.x.x.x y ::1). Resolver nombres y `create_connection` siguen bloqueados | Desactivar el bloqueo en las pruebas del visor | En Windows, asyncio crea un par de sockets conectados por 127.0.0.1 (`socket.socketpair`); con el bloqueo completo fallaban las 11 pruebas del visor. La interfaz local no sale del equipo, así que RNF-04 se mantiene |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 2 | La interfaz Streamlit en un hito posterior | Un visor de demostración entre H2.5 y H2.6 | Pedido del profesor; decisión del equipo del 29 de octubre de 2026 |
| `test_alcance_h2_0.py` | Streamlit y pyarrow postergados | Incorporados | D-91 |
| `tests/conftest.py` (H2.0) | Ninguna conexión de red durante las pruebas | Se permite la interfaz local del equipo | D-99 |

## No implementado en H2.D

- La interfaz definitiva (RF-UI): carga de archivos, configuración desde el navegador, ejecución de experimentos.
- Publicación en internet. El visor solo funciona en el equipo donde se ejecuta.
- Gráficos con Plotly (sigue postergado).

## Limitaciones conocidas

- El visor usa siempre los mismos archivos de ejemplo; si `data/sintetico/historial.xlsx` no existe, la página lo dice y muestra el comando para generarlo.
- Cada clic en "Construir poblaciones y partición" crea otra carpeta en `workspace/particiones/`.
- Las pruebas del visor usan el ejecutor de Streamlit (`AppTest`), sin navegador. La revisión visual se hizo con capturas en Linux (Chromium); en Windows falta verla.
- Streamlit muestra en las pruebas un aviso de pandas 3.1 sobre `reset_index(inplace=True)`, interno de Streamlit. No afecta al resultado.
