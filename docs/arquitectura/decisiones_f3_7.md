# Decisiones técnicas del hito F3.7 — resultados en el visor y reporte

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx. Todo se ejercita con datos sintéticos y con el protocolo ficticio de la demostración; ningún resultado del reporte ni del visor es evidencia sobre estudiantes reales ni sobre la eficacia del método (RNF-19). Continúan la numeración de `decisiones_f3_6.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-186 | Se agrega Plotly (7.1.0) al grupo opcional `ui`, junto a Streamlit, fijado en `requirements.lock` con hashes y `--exclude-newer 2026-10-28` (D-92). Solo la interfaz lo importa (contrato `motor-sin-streamlit`) y solo con `plotly.graph_objects` | Los gráficos propios de Streamlit | El equipo lo aprobó al aceptar F3.6; la especificación lo pide (RF-UI-03). `graph_objects` no necesita dependencias adicionales | Aplicada |
| D-187 | Rótulo de datos sintéticos (RNF-19) como regla del dominio (`domain/trazabilidad/rotulo.py`): el campo `origen_datos` queda en los registros de la evaluación final, la comparación y la explicación; cada tabla exportada lleva una columna `origen_datos` con `SINTÉTICO` en cada fila; el texto del reporte empieza con la leyenda. Un registro que no declara su origen se trata como sintético | Rotular solo el texto | PI-16 pide el rótulo en registros, gráficos y exportaciones. Mientras el importador solo admita datos sintéticos (DP-02, DP-14), tratar como sintético lo no declarado nunca deja un resultado sin rótulo | Aplicada |
| D-188 | El reporte de resultados se arma con lo que ya devolvieron los servicios, sin calcular nada nuevo: evaluación final; R0 y controles; diferencias pareadas con intervalos; anticipación; reducción de información; estado; interpretabilidad por bloque, y limitaciones (RF-M6-07). Las limitaciones repiten las de la especificación (M4) y las de las decisiones abiertas. No contiene seudónimos: los registros locales se numeran (RF-M6-04) | Un reporte que vuelva a leer el registro | Así el mismo reporte sirve para la demostración, cuyo proyecto temporal se borra, y para el visor | Aplicada |
| D-189 | Exportación: `reporte.md`, un CSV por tabla y `resultados.xlsx` (una hoja por tabla), en una carpeta nueva dentro de `reports/` (que git no versiona), sin sobrescribir y con el filtro de identificadores. Antes de escribir se comprueba el rótulo; si falta en cualquier parte, no se escribe nada. El visor obtiene los mismos archivos en memoria para las descargas | Escribir y comprobar después | "La exportación sin rótulo se rechaza" (PI-16) | Aplicada |
| D-190 | La exportación de experimentos del registro (`suficiencia registro exportar experimentos`) agrega la columna de rótulo a cada fila | Dejarla como estaba | Los experimentos son resultados obtenidos con datos sintéticos (RNF-19) | Aplicada |
| D-191 | `suficiencia evaluacion demostracion ... --reporte CARPETA` exporta el reporte de la demostración | Un comando `evaluacion reporte` sobre el registro | El reporte de una evaluación del proyecto necesita un protocolo aprobado, que no existe; se agregará cuando haga falta | Aplicada |
| D-192 | Página "Resultados (Fase 3)" del visor: ejecuta la demostración de F3.4 a F3.6 al pulsar un botón, con rutas fijas (`data/sintetico/ampliado.csv` y los ejemplos ficticios) y el escenario T1\|A+F; muestra la regla, el estado de la comparación y los pasos; cuatro gráficos Plotly (AUC-ROC y Brier escalado con intervalo, diferencias con R0 y su margen, importancia por bloque); las explicaciones locales numeradas, y las descargas del reporte | Ejecutar la demostración al abrir la página | La demostración entrena modelos y tarda alrededor de un minuto | Aplicada |
| D-193 | Cada gráfico de resultados sintéticos lleva "DATOS SINTÉTICOS" en el título y la leyenda completa al pie. La importancia por bloque se muestra como proporción de la importancia de cada configuración | Mostrar importancias absolutas | Las escalas cambian entre familias (log-odds, probabilidad o margen; D-176): las importancias absolutas no se comparan entre configuraciones | Aplicada |
| D-194 | Los gráficos están en `ui/graficos.py`, sin Streamlit, como `presentacion.py` (D-93) | Construirlos dentro de cada página | Se prueban sin levantar el visor | Aplicada |

## Desviaciones respecto de la documentación anterior

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 3, F3.7 | Páginas de resultados con rótulo sintético; exportación | Una página de resultados y el reporte exportable | — |
| Especificación, estructura (sección 8) | Carpeta `ui/componentes/` con gráficos Plotly | Un módulo `ui/graficos.py` | Un solo archivo basta por ahora |
| H2.D (D-91) | Plotly postergado | Incorporado | D-186 |

## No implementado en F3.7

- Reporte de una evaluación del proyecto leído del registro (D-191).
- Interfaz definitiva (RF-UI-01, RF-UI-04): configuración desde el navegador y desactivación de funciones según decisiones pendientes.
- Historial comparativo de experimentos en la interfaz (RF-M6-02).
- Gráficos dentro del reporte exportado: el reporte lleva tablas y texto; los gráficos están en el visor.

## Limitaciones conocidas

- La revisión visual de la página se hizo con capturas en Linux (Chromium); en Windows falta verla en el navegador.
- La página usa siempre los mismos archivos de ejemplo; si `data/sintetico/ampliado.csv` no existe, lo dice y muestra el comando para generarlo.
