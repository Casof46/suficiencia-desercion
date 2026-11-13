# Decisiones técnicas del hito F4.4: decisiones abiertas e historial de experimentos en el visor

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx. El visor sigue siendo una demostración local con datos sintéticos y configuraciones ficticias. La numeración continúa la de `decisiones_f4_2.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-215 | Cada función del visor declara las decisiones de las que depende su versión **con datos y configuración del proyecto** (`domain/trazabilidad/historial.py`). Son datos, no reglas: salen de la columna "resolver antes de" de la sección 12 y de los módulos que usa cada página. Mientras alguna esté abierta en el registro de decisiones, esa versión queda desactivada | Desactivar las páginas completas | Con decisiones abiertas, el visor dejaría de mostrar todo: las 20 siguen abiertas. Con los ejemplos ficticios, cada función sigue disponible y rotulada (RF-UI-04) | Aplicada |
| D-216 | Cada página muestra un botón desactivado, "Ejecutar con los datos y la configuración del proyecto", con las decisiones abiertas que lo bloquean. Cuando todas sus decisiones están registradas, el visor lo dice y remite a la línea de comandos | Implementar en el visor la ejecución con los datos del proyecto | No hay datos autorizados (DP-02) ni configuración del proyecto: ese camino no se podría probar. La línea de comandos ya ejecuta cada caso de uso con los archivos del proyecto | Aplicada |
| D-217 | Página "Decisiones": estado de DP-01 a DP-20 según el registro (los subcódigos se listan, pero no cierran la decisión, como en H2.8) y tabla de funciones con su estado con datos del proyecto y con el ejemplo ficticio. El visor no registra decisiones | Registrar decisiones desde el visor | Registrar una decisión es un acto del equipo con justificación; queda en `suficiencia registro decision` | Aplicada |
| D-218 | Página "Historial de experimentos" (RF-M6-02): todos los experimentos del registro, filtrables por estado y tipo, con el rótulo de origen, y la comparación de dos experimentos campo por campo (estado, modo, protocolo, huella de los datos, configuración, semillas y error). Por omisión muestra solo los campos distintos | Comparar métricas recalculadas | El historial muestra lo que guardó el registro; las métricas de validación ya tienen su página (F4.1) | Aplicada |
| D-219 | La revisión visual del visor se hizo en Linux con Chromium. En Windows se comprueba con las pruebas de la página en `verificar_f44.cmd` | Capturas en Windows | El acceso a la PC es solo de clic en el Explorador; el navegador no se puede manejar desde aquí | Aplicada |

## Desviaciones respecto del plan

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 4, F4.4 | Estado de las decisiones, funciones desactivadas, historial de experimentos y revisión visual en Windows | Todo; la revisión visual se hizo en Linux y en Windows se ejecutan las pruebas de las páginas (D-219). El equipo puede abrir el visor en Windows y revisarlo | Ver D-219 |

## No implementado en F4.4

- Ejecutar funciones con los datos del proyecto desde el visor (D-216).
- Registrar decisiones desde el visor (D-217).

## Limitaciones conocidas

- La lista de dependencias de cada función se mantiene a mano: si una página empieza a usar otro módulo, hay que actualizarla.
