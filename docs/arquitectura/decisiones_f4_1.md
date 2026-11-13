# Decisiones técnicas del hito F4.1 — reportes desde el registro y comparación de escenarios

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx. Todo se prueba con datos sintéticos y configuraciones ficticias; ningún resultado es evidencia sobre estudiantes reales ni sobre el método. Continúan la numeración de `decisiones_f3_7.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-195 | La evaluación comparativa guarda en el registro su resultado completo (`resumen`), además de lo que ya guardaba | Reconstruir la comparación con lo que guardaba F3.5 | Faltaban la seleccionada, R0, sus escenarios y la población comparada: sin ellos no se puede escribir el reporte de RF-M6-07 desde el registro | Aplicada |
| D-196 | `ServicioEvaluacionFinal.resultados_registrados`: lee la evaluación final, su **última** comparación exitosa y su **última** explicación exitosa, sin abrir la prueba ni recalcular. Los accesos a la prueba son los permitidos hasta la fecha de la evaluación. Una comparación registrada antes de F4.1 detiene el programa y pide repetirla (no abre la prueba) | Elegir la comparación por identificador | Lo habitual es querer el estado más reciente; repetir una comparación no cuesta un acceso | Aplicada |
| D-197 | `suficiencia evaluacion reporte --evaluacion ID --reporte CARPETA` exporta el reporte de una evaluación del proyecto, con el mismo formato y el mismo rótulo que el de la demostración (D-188, D-189). Sin comparación registrada, el reporte lo dice y no tiene sus tablas | Un formato aparte | Un solo formato de reporte | Aplicada |
| D-198 | Reporte de los escenarios en validación (RF-M4-10, RF-M4-14): una tabla con cada escenario, familia y métrica, con su intervalo, y en el texto una matriz ventana × conjunto por familia con la **primera métrica declarada** en DP-08a. Las celdas sin corrida se marcan con «·». `suficiencia experimentos metricas --reporte CARPETA` lo exporta | Una matriz con la mejor familia de cada escenario | Elegir "la mejor" sería una regla de selección (DP-10); el reporte solo reordena lo registrado | Aplicada |
| D-199 | Cada corrida en las métricas lleva su ventana y su conjunto, y el resultado de las métricas, su origen de datos (sintético si alguna corrida no declara otro, D-187). El registro de las corridas de entrenamiento no cambia | Agregar el origen al registro de cada corrida | Cambiarlo cambiaría la clave de reanudación (D-144): todas las corridas ya hechas se repetirían | Aplicada |
| D-200 | Página "Escenarios en validación" del visor: calcula las métricas de las corridas ya registradas en el proyecto al pulsar un botón (guarda un cálculo exploratorio, como `experimentos metricas`), y muestra la matriz ventana × conjunto de la métrica y la familia elegidas y las familias de un escenario con sus intervalos, con el rótulo de datos sintéticos, y las descargas del reporte | Entrenar desde el visor | Entrenar todos los escenarios tarda; la página usa lo que ya está registrado | Aplicada |

## Desviaciones respecto del plan

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 4, F4.1 | Reportes del proyecto desde el registro; escenarios por ventana y conjunto; los cinco modelos de cada escenario | Todo | — |

## No implementado en F4.1

- Reporte de una evaluación del proyecto con datos reales: no hay protocolo aprobado ni datos autorizados; se prueba con registros de prueba.
- Elegir una comparación o una explicación anterior por su identificador (D-196).

## Limitaciones conocidas

- Las comparaciones registradas antes de F4.1 no se pueden reportar desde el registro; hay que repetirlas.
- La página de validación se revisó con capturas en Linux.
