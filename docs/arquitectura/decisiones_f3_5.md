# Decisiones técnicas del hito F3.5 — comparación con la referencia R0

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx: la regla de R0 (DP-19) y el protocolo comparativo (DP-20) entran como datos obligatorios, con un ejemplo rotulado "EJEMPLO FICTICIO", y la comparación con protocolo solo se ejercita en la demostración con un protocolo ficticio. Continúan la numeración de `decisiones_f3_4.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-166 | Regla de R0 (DP-19) como datos: ventana de referencia `t_ref` (DP-19a), conjunto `mas_completo` (DP-19b) y métrica de elección de la familia (DP-19c), con empates por el orden de familias de la regla de selección. R0 no tiene margen, compuerta, umbrales mínimos ni no inferioridad (RF-M4-15) | Reutilizar la regla de selección del método | La especificación separa a propósito la regla de R0 de la del método; si fueran la misma, la comparación no aislaría nada | Aplicada |
| D-167 | Los referentes se construyen en `experimentos seleccionar`, con el mismo procedimiento que la selección (mismo reentrenamiento y misma regla de umbral): R0; un R0-fam por cada familia que el método eligió; un R-ven por cada ventana cuyo escenario seleccionado no sea el más completo, salvo que coincida con R0 | Construirlos después de la evaluación final | El escenario suficiente se conoce recién en la prueba, pero R0 y los controles deben congelarse antes de abrirla (RF-M4-17). Por eso se construyen los de todos los escenarios candidatos | Aplicada |
| D-168 | La evaluación final guarda las predicciones de prueba de cada configuración (seudónimo, cohorte, etiqueta y probabilidad) en `workspace/evaluacion_final/` con su huella en el registro | Volver a predecir en la comparación | CU-12 "usa las predicciones de CU-08 y no vuelve a abrir la prueba" (PI-15) | Aplicada |
| D-169 | `suficiencia evaluacion comparar` (CU-12): exige el protocolo vigente de la evaluación; compara la configuración del escenario suficiente con R0 sobre los estudiantes de prueba de R0 (en riesgo en `t_ref`, CMP-1); comprueba la validez (mismo horizonte por coincidencia de etiquetas, población de R0 contenida en la de la seleccionada, mismas cohortes, R0 evaluable); aplica la no inferioridad a cada métrica de DP-20 con el bootstrap pareado estratificado; calcula anticipación y reducción de información; describe las diferencias con R0-fam y R-ven (CMP-2); clasifica en C1 a C8 y registra el resultado. Verifica que no se haya registrado ningún acceso a la prueba | Una prueba estadística distinta del bootstrap | La especificación recomienda el bootstrap pareado (DP-20d); DeLong solo como sensibilidad, si se comprueban sus supuestos | Aplicada |
| D-170 | No inferioridad: con nivel 1 − α, demostrada si el cuantil α de las réplicas de Δ supera −δ; pérdida mayor que el margen si el cuantil 1 − α/2 queda por debajo de −δ; si no, no concluyente | Usar el valor puntual de Δ | Es la regla de la especificación; una diferencia no significativa nunca cuenta como no inferior (PU-25) | Aplicada |
| D-171 | Estados C1 a C8 en este orden: C7 si falla alguna condición de validez; C5 si la regla no seleccionó ninguno; C6 si la regla no dio un escenario o no hay no inferioridad evaluable; C8 si la seleccionada usa el escenario de R0; C4 si alguna métrica pierde más que el margen; C3 si alguna no es concluyente; C2 si todas son no inferiores y hay anticipación; C1 en el resto. Ningún estado declara superioridad | Otro orden | La validez va primero: sin ella ninguna diferencia se interpreta (RF-M4-21) | Aplicada |
| D-172 | La cobertura temprana (CMP-3) está implementada y probada como función, pero no se calcula en la comparación | Calcularla con D1 | Necesita q (DP-08i) y el diseño D3 (DP-17), que siguen abiertos (DP-20f) | Aplicada |
| D-173 | La demostración entrena también los escenarios que necesitan R0 y los controles, congela selección, R0 y controles, los evalúa en el único acceso y compara | Solo la selección | Muestra el recorrido completo de CU-08 y CU-12 | Aplicada |

## Desviaciones respecto de la documentación anterior

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 3, F3.5 | R0 y controles; diferencias, no inferioridad, anticipación y estados | Todo, salvo R-max (opcional, N3), la cobertura temprana en la comparación (D-172) y la estabilidad CMP-5 (N3) | Dependen de decisiones abiertas o son complementarios |
| `experimentos seleccionar` (F3.4) | Solo la selección | También R0 y los controles; exige que estén entrenados sus escenarios | D-167 |

## No implementado en F3.5

- R-max (opcional y descriptivo) y la estabilidad de la selección (CMP-5, RF-M4-22, N3).
- La cobertura temprana dentro de la comparación (D-172).
- DeLong pareado como análisis de sensibilidad.
- Comparación y evaluación en el registro del proyecto: necesitan un protocolo real aprobado con DP-19 y DP-20.
