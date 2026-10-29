# Decisiones técnicas del hito H2.5

Son decisiones **técnicas y reversibles** tomadas para construir H2.5: poblaciones D1, D2 y D3, partición cronológica y sello de la prueba. Ninguna resuelve DP-01d, DP-04, DP-05 ni DP-17. Las únicas configuraciones que existen son ejemplos ficticios. Continúan la numeración de `decisiones_h2_4.md`.

H2.5 depende de REC-01. El equipo la aceptó el 29 de octubre de 2026, con la condición de que DP-05 incluya un plan de contingencia, y pidió construir el hito sin esperar la conformidad de la asesoría. Si la asesoría pide cambios en REC-01, este hito se ajusta.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-78 | La configuración de poblaciones y partición (`config/poblaciones.yaml`) declara el periodo índice de cada ventana, el diseño principal, los complementarios y las cohortes de cada partición. Todos los campos son obligatorios, y un `null` detiene el programa nombrando DP-01d, DP-04, DP-17 o DP-05. Si el archivo no existe, se detiene por DP-04 | Un archivo por decisión | Un solo archivo para todo lo que CU-04 necesita decidir | Aplicada |
| D-79 | La fecha índice de cada ventana se expresa como el periodo ordinal al final del cual se consolida su información (0 = la admisión). Convive con el texto de `config/escenarios.yaml`, que describe la fecha índice | Reemplazar el texto de H2.2 | El historial sintético es ordinal (D-69). Cuando DP-01d y DP-15 se resuelvan, habrá que convertir la fecha índice real a periodos. **Desviación menor**: DP-01d queda en dos archivos, con formatos distintos | Aplicada |
| D-80 | Los tres diseños se construyen siempre, sin elegir ninguno. D1: en riesgo y etiquetable en cada ventana. D2: los miembros de D1 en T3, con la misma etiqueta en todas las ventanas. D3: toda la cohorte etiquetable, con una marca de "detectable a tiempo" | Construir solo el diseño principal | RF-M2-12 pide los tamaños de los tres sin esperar DP-17. La elección es DP-04 y DP-17 | Aplicada |
| D-81 | "Evento antes de la fecha índice" usa el periodo del evento según DP-01f. Con horizonte desde el ingreso, la etiqueta de cada unidad es la misma en todas las ventanas. Con horizonte relativo, cada ventana se etiqueta desde su periodo índice y el evento previo se busca con un horizonte que termina en ese periodo | Una sola regla | Las dos opciones de DP-01e están en la especificación | Aplicada |
| D-82 | D3 solo se construye con horizonte desde el ingreso | Inventar una variante | D3 cuenta la cohorte desde la admisión; con horizonte relativo no está definida | Aplicada |
| D-83 | Partición por cohortes: cada cohorte de los datos va a desarrollo, prueba, piloto o excluidas, y una cohorte sin asignar o declarada sin unidades detiene el programa. Toda cohorte de prueba debe ser posterior a toda cohorte de desarrollo y de piloto. Los códigos de cohorte se ordenan como texto | Asignar en silencio | REC-01 y PI-07. Evita perder cohortes por un error de escritura | Aplicada |
| D-84 | El plan de contingencia de DP-05 es un texto obligatorio de la configuración | Opcional | Condición con la que el equipo aceptó REC-01 | Aplicada |
| D-85 | Piloto (DP-08h): sus cohortes se declaran en `cohortes_piloto`, quedan fuera de desarrollo y prueba y no se describen | Mezclarlas con desarrollo | Decisión del equipo sobre DP-08h; las cohortes concretas son DP-05 | Aplicada |
| D-86 | Sello: las filas de prueba solo se obtienen con `SelloPrueba.leer`, que entrega la prueba solo a la operación `evaluacion_final` y registra cada intento, permitido o no, en el registro de accesos de H2.7. La partición expone el desarrollo y, de la prueba, solo su tamaño | Confiar en que nadie lea la prueba | RF-M2-07, RF-M6-06 y PI-02 | Aplicada |
| D-87 | Los índices se guardan en `workspace/particiones/particion-<fecha y hora>/`: un CSV por partición, solo con el seudónimo y la cohorte, y un manifiesto con cohortes, tamaños, plan de contingencia y huellas. Nunca se sobrescriben. Al leer la prueba se comprueba su huella | Guardar etiquetas o datos completos | RF-M2-06; los índices bastan para reconstruir y no repiten datos | Aplicada |
| D-88 | `poblaciones construir` describe solo el desarrollo (tamaño, eventos y prevalencia por diseño y ventana, exclusiones por motivo y no etiquetables por cohorte con la marca de CP-08). De la prueba informa solo el tamaño | Describir todo con datos sintéticos | RF-M2-09, PI-02 y CU-11 parte B | Aplicada |
| D-89 | CU-11 parte A: para todas las cohortes, solo el número de unidades, el último periodo observable y si alcanza el periodo necesario para etiquetar (horizonte más confirmación). No cuenta eventos ni estados | Omitir la parte A | La parte A sirve para elegir las cohortes de prueba con seguimiento completo (DP-05) sin mirar resultados | Aplicada |
| D-90 | `poblaciones leer-prueba` existe para comprobar el sello: como ninguna operación de la línea de comandos es la evaluación final, siempre se rechaza y queda registrado | No ofrecerlo | Permite verificar PI-02 a mano | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 2 | H2.5 después de la conformidad de la asesoría con REC-01 | Construido con la aceptación del equipo, sin esa conformidad | Decisión del equipo del 29 de octubre de 2026 |
| Especificación, DP-01d | Una fecha índice por ventana | Texto en `escenarios.yaml` y periodo ordinal en `poblaciones.yaml` | D-79 |
| Plan de la Fase 2 | PI-07 completa | Solo la parte de la partición; la de los folds de validación llega con M3 | No hay validación interna todavía |

## No implementado en H2.5

- La elección del diseño principal y de las cohortes reales.
- La evaluación final, la única operación que podrá leer la prueba (CU-08).
- Los folds de validación cronológica (RF-M3-03) y la segunda parte de PI-07.
- El análisis de sensibilidad de CP-08: solo se marcan las cohortes que lo exigen.

## Limitaciones conocidas

- El sello protege la prueba dentro del programa. Quien abra `prueba.csv` con otro programa no queda registrado. La huella delata una modificación, no una lectura.
- La partición se guarda con los seudónimos de la clave usada. Con `--clave-efimera`, los seudónimos cambian en cada ejecución, así que cada partición vale solo para el dataset seudonimizado en esa ejecución.
- Los códigos de cohorte deben ordenarse cronológicamente como texto (por ejemplo, `2014-1`).
