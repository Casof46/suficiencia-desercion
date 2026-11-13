# Decisiones técnicas del hito F4.3: ensayo general con el dataset sintético del OE3

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx. El dataset es 100 % sintético y todas las configuraciones son ficticias. Ningún resultado del ensayo es evidencia sobre estudiantes reales ni sobre el método: las salidas reflejan los supuestos del generador. La numeración continúa la de `decisiones_f4_1.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-201 | El generador del dataset del OE3 se versiona **sin cambios** en `scripts/oe3/generar_dataset_sintetico.py` y queda excluido de ruff y de mypy. Se recuperó de la conversación del 23 de octubre de 2026 en que se escribió: la versión final más sus cinco modificaciones posteriores, aplicadas en orden. Con la semilla 20261023, las 10 huellas coinciden con las del README del dataset. Coinciden en dos entornos: Python 3.13, numpy 2.5.3 y pandas 3.0.5; y el del proyecto, Python 3.11, numpy 2.4.6 y pandas 3.1.0. Su huella SHA-256, con fin de línea LF como se guarda en git, es `f70d353cec9e66ffe40e028f24824866890d1e5d98f51187d27b3eb413c3fa34` | Adaptarlo al estilo del proyecto | Cambiaría el código cuyas salidas se comprueban con las huellas publicadas | Aplicada |
| D-202 | `scripts/preparar_ensayo_oe3.py` comprueba primero las 10 huellas: si alguna no coincide, se detiene sin escribir nada. Después arma un solo archivo en el formato del motor, una fila por estudiante y ciclo. El estado de matrícula sale del archivo longitudinal y las 40 variables, del archivo ancho. Es una conversión del ejemplo, fuera del motor. No implementa la integración de RF-M1-09 ni decide DP-15 | Usar solo el archivo ancho, como preveía el plan | El archivo ancho no trae el estado de matrícula de cada ciclo, y el motor construye la etiqueta con él (M1). Ver la desviación más abajo | Aplicada |
| D-203 | **Corrección del motor.** El paso que adapta los tipos antes del preprocesamiento devuelve las columnas en el orden en que llegan | Mantener primero las numéricas y después las categóricas | Las variables de un escenario van en orden alfabético. Una categórica entre dos numéricas (por ejemplo `area_programa`) cambiaba el orden, y scikit-learn rechazaba el ajuste en las cinco familias. El historial de prueba anterior no lo mostraba porque sus categóricas quedaban al final. Las columnas se eligen por nombre, así que las corridas anteriores no cambian | Aplicada |
| D-204 | Configuraciones ficticias en `config/ejemplos/oe3/`. **Diccionario:** nombres, tipos, rangos, bloques y la "primera ventana admisible" α de cada variable, tomados del diccionario del generador. **Objetivo:** imita las reglas con que el generador construye su etiqueta. **Poblaciones:** la partición del generador (cohortes 1 a 8 de desarrollo, 9 y 10 de prueba, 11 y 12 excluidas). **Escenarios:** las fechas índice que supone el generador. **Experimentos:** los de `experimentos_ficticio.yaml`, más la lectura de las 40 variables. El protocolo es el ficticio de F3.4 | Valores propios del equipo | DP-01, DP-03, DP-04 y DP-05 siguen abiertas. Copiar los supuestos del generador permite comparar el motor con él sin inventar nada nuevo | Aplicada |
| D-205 | Población inicial `admitidos` en el objetivo del ensayo | `matriculados_primer_periodo` | En el generador, todos los estudiantes están matriculados en el ciclo 1. A 94 de ellos les registra un retiro total en ese ciclo, que el motor no cuenta como matrícula: con `matriculados_primer_periodo` quedarían fuera, y el generador sí los etiqueta | Aplicada |
| D-206 | El script compara la etiqueta del motor con la del generador **solo en las cohortes de desarrollo**. Las diferencias se documentan; no se corrigen ni en el motor ni en el generador | Comparar todas las cohortes; ajustar el motor hasta que coincida | La prueba sigue sellada. Cada diferencia es una regla distinta de la definición de deserción, y esa definición es DP-01, que sigue abierta | Aplicada |
| D-207 | El método completo se ensaya con `evaluacion demostracion` sobre los 28 escenarios factibles, en un proyecto temporal. Los 4 escenarios de T0 con el bloque B no son factibles, porque B no tiene variables en T0 | Entrenar en el registro del proyecto | El registro del proyecto solo admite el modo exploratorio. La selección, la evaluación final, la comparación con R0 y las explicaciones solo existen en la demostración | Aplicada |
| D-208 | El historial del ensayo se escribe con fin de línea LF en cualquier sistema | Dejar el fin de línea del sistema | En la primera verificación en Windows, el historial salió con fin de línea CRLF. Su huella fue `0e2fddee…` y en Linux `f06e7098…`: mismo contenido, distinta huella. Con LF, la huella no depende del sistema | Aplicada |

## Desviaciones respecto del plan

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 4, F4.3 | Usar solo el archivo ancho (`wide`), ya integrado, salvo que el equipo decidiera otra cosa | Combinar el ancho y el longitudinal del mismo generador en un solo archivo, con un script fuera del motor (D-202) | El ancho no tiene el estado de matrícula por ciclo que el motor necesita para el objetivo. Aceptada por el equipo el 13 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier) |
| Plan de la Fase 4, regla 1 ("solo datos sintéticos") | — | Se cumple: cada fila lleva `origen_datos = SINTETICO` y el importador la acepta solo por eso | — |

## Diferencias entre el motor y el generador (datos para DP-01, no decisiones)

| Tema | Generador | Motor con el objetivo ficticio del ensayo | Efecto en desarrollo |
| --- | --- | --- | --- |
| Confirmación de un ciclo sin matrícula seguido de reservas al final del horizonte o en el ciclo H+1 (por ejemplo `MMMNRN` o `MRNRRM`) | Salta las reservas y confirma con el ciclo siguiente | Mira solo hasta el ciclo H+1; si ahí sigue una pausa, la etiqueta queda sin decidir (seguimiento incompleto) | 25 estudiantes que el generador etiqueta (9 positivos y 16 negativos) quedan sin etiqueta en el motor |
| Baja por fallecimiento en el ciclo H+1 | Excluye el episodio | La etiqueta ya quedó decidida al terminar el horizonte (Y = 0) | 1 estudiante |
| Población de cada ventana | R(t) anidada: activos en todos los ciclos hasta t | D1: sin evento antes de la fecha índice y con etiqueta (DP-04) | D1 incluye a estudiantes que el generador saca de R(t), por una interrupción, una reserva o un retiro total previos. Para ellos, el generador deja vacías a propósito las variables desde T1, que se imputan dentro de cada fold. En desarrollo son 1, 57, 222 y 348 en T0 a T3 |
| Créditos y cursos matriculados | En Tj, los del ciclo j | Las variables desde T0 solo se leen con `primer_registro`: siempre los del ciclo 1 | Coinciden en T0 y T1; difieren en T2 y T3 |

Coinciden 2655 de 2681 etiquetas de desarrollo. En los positivos que coinciden, el ciclo de inicio del evento es el mismo en todos los casos.

## No implementado en F4.3

- La integración de las fuentes crudas fechadas (RF-M1-09; DP-15).
- Una población R(t) anidada en el motor: sería un diseño nuevo de población (DP-04).
- Variables disponibles desde T0 que cambian por ciclo.

## Limitaciones conocidas

- Las métricas del ensayo salen de un generador con relaciones inventadas. Muestran que el motor recorre el método de punta a punta con datos de la estructura del OE3; no dicen nada sobre qué ventana o qué bloques bastan en una universidad real.
- El dataset no se versiona: se regenera con el script y la semilla, y se comprueban sus huellas.
