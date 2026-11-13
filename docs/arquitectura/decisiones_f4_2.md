# Decisiones técnicas del hito F4.2: estabilidad descriptiva y referente R-max

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx. Las tres funciones del hito son descriptivas (N3), dependen de decisiones abiertas y están **apagadas por omisión**, como aprobó el equipo en el plan de la Fase 4. Todo se prueba con datos sintéticos y configuraciones ficticias; ningún resultado es evidencia sobre estudiantes reales ni sobre el método. La numeración continúa la de `decisiones_f4_3.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-209 | **Estabilidad de la selección (CMP-5; RF-M4-22).** Para cada escenario se usa la corrida de la que salió su modelo seleccionado. En cada fold de desarrollo se calculan las métricas sobre las probabilidades de validación de ese fold, con intervalos bootstrap dentro del fold (DP-08e), y se aplica el criterio del protocolo de la evaluación. Por escenario se cuentan los folds evaluables, los folds en que cumple y los folds en que la regla lo elige. Las condiciones que comparan escenarios entre sí (DP-08d) quedan sin comparadores, como en la evaluación final | Reentrenar la selección completa en cada fold | Describir con lo ya registrado no cambia la selección ni abre la prueba; reentrenar repetiría todo el desarrollo | Aplicada |
| D-210 | Métricas de prueba por cohorte de cada configuración evaluada, con las predicciones que guardó la evaluación final. No se abre la prueba. Se registra como cálculo exploratorio de tipo `estabilidad` | Calcularlas en la evaluación final | La evaluación final no debe cambiar; CMP-5 es descriptiva y sin inferencia entre cohortes (DP-20g) | Aplicada |
| D-211 | CMP-5 se enciende con `comparacion.estabilidad: true` (DP-20g). Sin ese campo queda apagada. El servicio y `suficiencia evaluacion estabilidad` se niegan si está apagada, y la demostración solo agrega su paso si está encendida | Un campo obligatorio, sin valor por omisión | El plan aprobado la incorpora como dato opcional, apagado por omisión | Aplicada |
| D-212 | **Estabilidad de las explicaciones (RF-M5-06), entre folds.** Se explican los modelos de cada fold de la corrida con las mismas filas de fondo y explicadas que el modelo congelado, y con el mismo explicador. Se comparan con el congelado de dos formas: la proporción de la importancia de cada bloque y la correlación de Spearman entre las importancias por variable. Se enciende con `interpretabilidad.estabilidad: folds` (por omisión, `ninguna`) y exige el nivel `bloque` | Entre semillas | RF-M5-06 admite semillas o folds. Los modelos de los folds ya existen y tienen su huella; entre semillas habría que reentrenar | Aplicada |
| D-213 | **Referente R-max (RF-M4-16; DP-19d).** Se enciende con `referencia.r_max: true` (por omisión, apagado). Es el escenario y la familia con mejor métrica de R0 en validación entre los escenarios pedidos y las cinco familias. Los empates se resuelven por el orden del catálogo (ventana más temprana, menos bloques) y después por `seleccion.orden_familias`. Se congela como control, se evalúa en el mismo acceso a la prueba y aparece en la comparación descriptiva CMP-2 | Elegir entre los 32 escenarios aunque no se hayan pedido | Solo hay corridas de los escenarios pedidos. R-max es descriptivo y optimista por construcción | Aplicada |
| D-214 | `experimentos_ficticio.yaml` declara las tres funciones apagadas. `experimentos_estabilidad_ficticio.yaml` es el mismo ejemplo con las tres encendidas | Encenderlas en el ejemplo principal | Las demostraciones y pruebas anteriores no cambian; el ejemplo nuevo las ejercita | Aplicada |

## Desviaciones respecto del plan

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 4, F4.2 | Estabilidad de la selección por fold y de las explicaciones entre semillas y folds; R-max | Todo, con las explicaciones solo entre folds (D-212) | Entre semillas habría que reentrenar los modelos |

## No implementado en F4.2

- Estabilidad de las explicaciones entre semillas.
- Gráficos de estabilidad en el visor.
- Cualquier inferencia entre cohortes: CMP-5 solo cuenta y describe.

## Limitaciones conocidas

- Los intervalos por fold y por cohorte salen de pocas filas y son anchos; son descriptivos.
- Un escenario con una sola variable no tiene correlación de rangos definida: se informa como «—».
