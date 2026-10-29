# Decisiones técnicas del hito H2.4

Son decisiones **técnicas y reversibles** tomadas para construir H2.4 (objetivo y estados de etiqueta). Ninguna resuelve DP-01 ni DP-18: el programa no contiene ninguna definición de deserción, y la única definición que existe es un ejemplo ficticio. Continúan la numeración de `decisiones_h2_7.md`.

H2.4 depende de REC-03. El equipo la aceptó el 29 de octubre de 2026 con el cambio CP-08 y pidió construir el hito sin esperar la conformidad de la asesoría. Si la asesoría pide cambios en REC-03, este hito se ajusta.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-65 | Cada elemento del desglose de DP-01 es una sección obligatoria de la definición del objetivo (`evento`, `unidad`, `poblacion`, `horizonte`, `fechado_evento`, `pausas`, `retiro_en_periodo`, `traslados`, `reingreso`, `periodos_extraordinarios`, `desenlaces_excluidos`, `seguimiento`), igual que el catálogo de estados y el tratamiento de los no etiquetables (DP-18). Si falta, la definición se rechaza; si vale `null`, el programa se detiene nombrando el subcódigo pendiente | Valores por omisión | Criterio de H2.4: sin todos los parámetros, el objetivo no se construye. Ningún valor se supone | Aplicada |
| D-66 | DP-01d (fecha índice) no se repite en la definición del objetivo: ya es obligatoria en `config/escenarios.yaml` desde H2.2. La definición tiene 12 de los 13 elementos | Duplicarla | Una sola fuente para cada decisión. **Desviación menor** respecto del plan, que pedía los 13 parámetros en el constructor | Aplicada |
| D-67 | Catálogo de estados: cada código de estado de matrícula se asocia a una de ocho categorías (matrícula, ausencia, pausa, retiro en el periodo, traslado interno, traslado externo, desenlace excluido, evento formal). Un código sin categoría detiene el programa | Reglas sobre los códigos directamente | Los códigos los aporta la institución (DP-01); las reglas se escriben sobre categorías y no dependen de los nombres de los códigos | Aplicada |
| D-68 | Cada categoría configurable admite solo las opciones que lista la sección 12.1 (por ejemplo, la pausa puede ser neutral, ausencia o no observable). Una pausa neutral exige `limite_periodos` (un número o `sin_limite`): pasado ese límite, cuenta como ausencia | Admitir cualquier combinación | Las opciones de DP-01g, h, i y l son las de la especificación; el límite expresa la opción "evento tras N periodos" | Aplicada |
| D-69 | Los periodos son ordinales desde el ingreso (1 = primer periodo de la cohorte), como el campo `ciclo` del diccionario sintético. El último periodo observable de cada cohorte es el máximo periodo con registros de esa cohorte | Fechas de calendario; una fecha de corte declarada | Es el formato del historial sintético. El formato real depende de DP-15 y puede requerir otra conversión | Aplicada |
| D-70 | El horizonte desde el ingreso etiqueta a cada estudiante una vez. El horizonte relativo a la fecha índice exige indicar el periodo de inicio de cada ventana: el constructor lo acepta, pero solo se usará al construir las poblaciones por ventana (H2.5) | Implementar las ventanas ahora | H2.5 no está autorizado | Aplicada |
| D-71 | Seguimiento incompleto: no se etiqueta como negativo a quien no tiene observado todo el horizonte. Con `fin_horizonte_y_confirmacion`, tampoco a quien tiene una ausencia al final del horizonte que todavía no se puede confirmar. Con reingreso que anula, un evento seguido de un horizonte sin observar completo queda como seguimiento incompleto, porque un reingreso futuro podría anularlo | Etiquetar como negativo lo no observado | Es el problema que REC-03 busca evitar | Aplicada |
| D-72 | Después de un traslado externo, un desenlace excluido o un traslado interno que no continúa, la unidad no tiene más periodos que observar: la falta de registros posteriores no se interpreta | Seguir leyendo periodos | Evita declarar "no observable" lo que es el fin natural del historial | Aplicada |
| D-73 | `construir` nunca muestra la distribución de los estados de etiqueta, ni siquiera con datos sintéticos: informa el número de unidades, las excluidas de la población y la huella del resultado. La función que cuenta no etiquetables por cohorte y motivo (CP-08) existe en el dominio, pero el servicio no la usa hasta que exista la partición de desarrollo (H2.5) | Mostrar los conteos con datos sintéticos | RF-M1-03 y RF-M2-09: antes del sellado no se muestra la distribución de los estados | Aplicada |
| D-74 | `objetivo demostracion` etiqueta diez historiales ficticios escritos a mano con la definición de ejemplo, para ver qué produce cada situación sin mostrar datos | Mostrar casos del dataset sintético | Permite comprobar las reglas a mano sin contradecir D-73 | Aplicada |
| D-75 | `construir` repite la importación de H2.3 (marca sintética, seudonimización y auditoría apta) en lugar de leer el CSV procesado | Leer `data/interim/` | Garantiza que solo se etiqueten datos sintéticos, seudonimizados y auditados (PU-17) | Aplicada |
| D-76 | Solo se implementa el tratamiento `excluir_y_contar` de DP-18 (REC-03). El nivel que exige el análisis de sensibilidad es obligatorio en la definición; el tipo de análisis queda pendiente en DP-18 | Implementar el análisis | Su tipo no está decidido | Aplicada |
| D-77 | El ejemplo ficticio va en `config/ejemplos/objetivo_ficticio.yaml`; la definición del proyecto irá en `config/objetivo/definicion.yaml` | `config/objetivo/` con ejemplos, como decía el plan | Sigue la convención de H2.2 y H2.3: los ejemplos están juntos y rotulados. **Desviación menor** | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 2 | 13 parámetros de DP-01 en el constructor | 12; DP-01d sigue en `config/escenarios.yaml` | D-66 |
| Plan de la Fase 2 | Ejemplos en `config/objetivo/` | Ejemplo en `config/ejemplos/` | D-77 |
| Plan de la Fase 2 | H2.4 después de la conformidad de la asesoría con REC-03 | Construido con la aceptación del equipo, sin esa conformidad | Decisión del equipo del 29 de octubre de 2026 |

## No implementado en H2.4

- Ninguna definición de deserción ni valores reales de horizonte, N o fechas.
- Las poblaciones D1, D2 y D3 por ventana, la partición y el reporte de no etiquetables en desarrollo (H2.5).
- El análisis de sensibilidad de CP-08: solo se marca qué cohortes lo exigen.
- Los tratamientos de DP-18 distintos de excluir y contar.

## Limitaciones conocidas

- Los historiales fijos del generador sintético terminan antes que su cohorte. Con `periodo_sin_registro: no_observable`, esos estudiantes quedan como no etiquetables por resultado no observable. Es correcto según la regla, pero no representa ninguna situación real.
- La unidad estudiante y carrera necesita una columna de carrera que el diccionario sintético no tiene. Está probada con tablas escritas a mano.
- El fechado del evento en el primer periodo sin matrícula cuenta desde la primera ausencia efectiva: una pausa dentro del límite no es ausencia.
