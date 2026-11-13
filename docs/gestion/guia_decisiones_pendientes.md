# Guía de las decisiones metodológicas pendientes

| Campo | Valor |
| --- | --- |
| Fecha | 13 de noviembre de 2026 |
| Para | El equipo y la asesoría |
| Base | Especificación Fase 1 v0.6, sección 12; informes de cierre de las Fases 3 y 4; registros de los hitos |
| Qué es | Un apoyo para decidir. Para cada decisión abierta dice qué pide la especificación, dónde entra en el motor, qué valor tiene hoy el ejemplo ficticio y qué mostraron los ensayos con datos sintéticos |
| Qué no es | **No decide nada ni recomienda opciones.** Los valores de los ejemplos son inventados para probar el programa. Lo observado con datos sintéticos describe al generador, no a estudiantes reales |

## 1. Estado actual

- **20 decisiones.** Según `suficiencia decisiones` en la PC del proyecto, hay 1 registrada (DP-16, SQLite) y 19 abiertas. El equipo además decidió el subcódigo DP-08h (se permite un piloto; pendiente de la conformidad de la asesoría), que no cierra DP-08.
- **Bloquean el uso de datos reales:** DP-01, DP-02, DP-14, DP-15 y DP-18.
- **Deben cerrarse antes de aprobar el protocolo confirmatorio:** DP-06, DP-07, DP-08, DP-09, DP-10, DP-12, DP-17, DP-19 y DP-20.
- **Cómo se registra una decisión:** `suficiencia registro decision --codigo DP-xx ...`, con fecha, responsable, opción elegida y justificación, y su ficha en `docs/decisiones/` (RF-M6-05). Ninguna admite valores fijados después de ver resultados de desarrollo.
- **Cómo la usa el motor:** cada decisión es un dato obligatorio de la configuración del proyecto. Un valor `null` detiene el programa y nombra la decisión pendiente. El visor muestra el estado de cada una y desactiva sus funciones con datos del proyecto mientras sigan abiertas (F4.4).

## 2. Orden sugerido por las dependencias

Este orden sale de la columna "resolver antes de" y de las dependencias de la especificación; no es una prioridad del equipo.

1. **Para tener datos:** DP-02 y DP-14 (autorización y protección), DP-15 (formato).
2. **Para construir el objetivo:** DP-01 (con sus 13 subcódigos) y DP-18.
3. **Para variables y escenarios:** DP-03 y DP-01d (fechas índice).
4. **Para poblaciones y partición:** DP-04, DP-05 (junto con DP-08h) y DP-17.
5. **Para el protocolo:** DP-06, DP-07, DP-09, DP-10, DP-12 y, después, DP-08, DP-19 y DP-20, que dependen de las anteriores. DP-11 y DP-13 pueden resolverse en paralelo.

## 3. Cada decisión

### DP-01: definición operativa de deserción

- **Especificación:** 13 subcódigos, DP-01a a DP-01m (sección 12.1). La institución aporta reglas, códigos y datos; el equipo y la asesoría aprueban. Se resuelve antes de CU-03.
- **En el motor:** `config/objetivo/definicion.yaml`, con un campo por subcódigo y el catálogo de estados de matrícula. La fecha índice de cada ventana (DP-01d) va en `config/escenarios.yaml`.
- **Ejemplos ficticios:** `config/ejemplos/objetivo_ficticio.yaml` y `config/ejemplos/oe3/objetivo_oe3_ficticio.yaml`; el segundo imita las reglas del generador del OE3.
- **Lo que mostró el ensayo con el dataset sintético del OE3 (F4.3):**
  - En desarrollo coinciden 2655 de 2681 etiquetas del motor y del generador.
  - En 25 estudiantes difiere la confirmación del evento cuando hay reservas al final del horizonte o en el ciclo H+1. El generador salta las reservas y confirma con el ciclo siguiente; el motor mira solo hasta el ciclo H+1 y deja la etiqueta sin decidir. Es una pregunta para DP-01g y DP-01m.
  - En 1 estudiante difiere el fallecimiento en el ciclo H+1: el generador excluye el episodio; el motor ya había decidido Y = 0 al terminar el horizonte (DP-01l).
  - Con la población inicial "matriculados en el primer periodo", el motor deja fuera a 94 estudiantes con retiro total en el ciclo 1, que el generador sí etiqueta (DP-01c y DP-01h).

### DP-02: fuente, alcance y autorización de uso de los datos

- **Especificación:** convenio o carta institucional, aprobación ética o datos anonimizados por la institución. Deciden la institución y la asesoría, antes de CU-01.
- **En el motor:** el importador rechaza todo archivo sin la marca de origen sintético. No hay forma de cargar datos reales mientras esto siga abierto.
- **Estado:** el proyecto no cuenta hoy con autorización institucional. Los datos institucionales no se envían a servicios externos ni a asistentes de IA.

### DP-03: bloque y ventana mínima de cada variable

- **Especificación:** revisión variable por variable, o un criterio por fecha de registro en el sistema fuente. Deciden el equipo y la asesoría, antes de CU-02.
- **En el motor:** el diccionario de datos (bloque y `ventana_minima` de cada variable) y la lectura de cada variable en el corte (`matrices.agregacion` en `config/experimentos.yaml`: `primer_registro` o `ultimo_ciclo`).
- **Lo que mostró el ensayo con el OE3:** una variable disponible desde T0 que cambia en cada ciclo, como los créditos matriculados, solo puede leerse con `primer_registro`. Por eso queda como la del ciclo 1 en todas las ventanas. Si la base real tiene variables así, habrá que decidir cómo tratarlas.

### DP-04: diseño principal de población (D1, D2 o D3)

- **Especificación:** ver la sección 4 (M2). Puede decidirse conceptualmente, sin ver tamaños. Antes de CU-04.
- **En el motor:** `diseno_principal` en `config/poblaciones.yaml`. El motor construye los tres diseños sin elegir ninguno.
- **Lo que mostró el ensayo con el OE3:** D1 incluye a estudiantes que el generador saca de su población anidada R(t), por una interrupción, una reserva o un retiro total previos. En desarrollo fueron 1, 57, 222 y 348 en T0 a T3.

### DP-05: partición cronológica y plan de contingencia

- **Especificación:** cohortes de desarrollo y de prueba, cohortes atípicas, plan de contingencia y, si DP-08h lo habilita, cohortes de piloto. Depende de DP-01 y DP-18. Antes de CU-04.
- **En el motor:** `particion` en `config/poblaciones.yaml` (`cohortes_desarrollo`, `cohortes_prueba`, `cohortes_piloto`, `cohortes_excluidas` y `plan_contingencia`).
- **Ejemplos ficticios:** 8 cohortes de desarrollo, 2 de prueba y 2 excluidas, como la base de trabajo del informe del OE3.

### DP-06: desbalance y regla del umbral

- **Especificación:** pesos de clase o remuestreo dentro del fold; umbral fijo, que optimiza una métrica, que garantiza un mínimo de Recall o el cuantil 1 − q de la capacidad de alerta (propuesta del manuscrito; requiere DP-08i). Decide el equipo, antes de CU-05.
- **En el motor:** `desbalance` (`ninguno` o `pesos_clase`) y `umbral.regla` (`fijo`, `cuantil_q` o `recall_minimo`) en `config/experimentos.yaml`.

### DP-07: validación interna, búsqueda de hiperparámetros y presupuesto

- **Especificación:** origen deslizante o expansivo por cohorte; búsqueda en malla, aleatoria o bayesiana; número de intentos. La evidencia que pide incluye el tiempo medido con datos sintéticos. Decide el equipo, antes de CU-05.
- **En el motor:** `validacion`, `busqueda` y `modelos` (espacio de cada familia) en `config/experimentos.yaml`. El motor ofrece malla y búsqueda aleatoria; la bayesiana no está implementada.
- **Tiempo medido con datos sintéticos (F4.3):** con el dataset del OE3 (4050 estudiantes, 40 variables), 6 folds y la malla del ejemplo ficticio (2 combinaciones por familia), entrenar las cinco familias del escenario T1|A+F tardó unos 24 segundos en Linux. El método completo con 28 escenarios tardó 8 minutos en Linux y unos 22 minutos en la PC de Windows. Un espacio de búsqueda mayor multiplica esos tiempos.

### DP-08: criterios de suficiencia

- **Especificación:** nueve subcódigos, DP-08a a DP-08i (sección 12.2). Depende de DP-04, DP-09 y DP-17. Antes de CU-05; DP-08h, antes de CU-04. El manuscrito congelado del 23 de octubre de 2026 tiene una propuesta sin valores para los parámetros; la especificación no la adopta mientras no se apruebe.
- **En el motor:** el criterio va en el protocolo (métricas, condiciones, multiplicidad y desempate), que se aprueba y se congela en el registro. Las métricas y los intervalos van en `metricas` e `intervalos` de `config/experimentos.yaml`, y q (DP-08i) en `metricas.q`.
- **Estado:** DP-08h decidido por el equipo (se permite un piloto). No existe ningún criterio ni procedimiento de multiplicidad del proyecto. El protocolo de ejemplo es ficticio y el programa se niega a aprobarlo.

### DP-09: Brier Score y calibración

- **Especificación:** no usar, solo reportar o incluir en el criterio; Platt o isotónica; Brier escalado (propuesta del manuscrito). Antes de CU-05.
- **En el motor:** `calibracion` (`ninguna`, `platt` o `isotonica`) en `config/experimentos.yaml`; Brier y Brier escalado están entre las métricas disponibles.

### DP-10: selección del modelo representativo

- **Especificación:** mejor en validación o el más simple dentro de un margen; reentrenar o no sobre todo desarrollo. Antes de CU-05.
- **En el motor:** `seleccion` en `config/experimentos.yaml` (métrica, margen, orden de familias y reentrenamiento).
- **Lo que mostró el ensayo con el OE3:** con el margen del ejemplo ficticio (0,01), la familia seleccionada cambió entre Linux y Windows en 3 de 28 escenarios. Pequeñas diferencias numéricas entre sistemas bastaron para cambiar cuál quedaba primera. La regla de suficiencia y el estado de la comparación coincidieron en los dos sistemas.

### DP-11: alcance de la interpretabilidad

- **Especificación:** solo el escenario suficiente o todas las configuraciones congeladas; global, por bloque, local. Decide el equipo, antes de CU-09.
- **En el motor:** `interpretabilidad` en `config/experimentos.yaml`. Desde F4.2 incluye una opción apagada para comparar las explicaciones entre los modelos de los folds (`estabilidad: folds`).
- **Costo observado:** KernelExplainer (SVM) es el más lento; el ejemplo usa muestras acotadas.

### DP-12: tratamiento de faltantes

- **Especificación:** imputación simple, indicador de faltante, exclusión; no aplica si el escenario no es factible. Decide el equipo, antes de CU-05.
- **En el motor:** perfiles de `preprocesamiento` en `config/experimentos.yaml`, ajustados solo con el ajuste de cada fold. Un bloque sin variables en una ventana deja el escenario no factible: no se imputa.
- **Lo que mostró el ensayo con el OE3:** las variables de los estudiantes de D1 que el generador saca de R(t) llegan vacías y se imputan (ver DP-04).

### DP-13: análisis de equidad por subgrupos

- **Especificación:** no incluir, reportar métricas por subgrupo o incluir en el criterio. Requiere atributos de subgrupo autorizados.
- **En el motor:** las métricas por subgrupo (RF-M4-11) no están construidas; dependen de esta decisión y de atributos autorizados.

### DP-14: seudonimización o anonimización y custodia

- **Especificación:** datos anonimizados por la institución, seudonimización local sin guardar la correspondencia, o correspondencia custodiada por la institución. Antes de CU-01.
- **En el motor:** seudonimización con una clave que no se guarda (`--clave-efimera`). La seudonimización no equivale a anonimización: los datos seudonimizados siguen siendo datos personales.

### DP-15: formato de entrada de los datos

- **Especificación:** tabla ancha, tablas por bloque o tablas por periodo. Decide el equipo, según lo que entregue la institución.
- **En el motor:** hoy, una tabla con una fila por estudiante y ciclo, que incluye el historial de matrícula. La integración de varias tablas (RF-M1-09) no está construida.
- **Lo que mostró el ensayo con el OE3:** el archivo ancho del generador no trae el estado de matrícula de cada ciclo, que el motor necesita para el objetivo. Hubo que combinarlo con el archivo longitudinal, con un script fuera del motor. Si la institución entrega varias tablas, el historial de matrícula por periodo tiene que estar entre ellas.

### DP-16: SQLite para el registro de experimentos (registrada)

- Decidida por el equipo el 29 de octubre de 2026 (comunicada por Jorge; pendiente de confirmación de Javier); ficha en `docs/decisiones/DP-16.md`.

### DP-17: análisis complementario de población (D2, D3)

- **Especificación:** D2, D3, ambos o ninguno. La evidencia son el tamaño y los eventos de D2 y D3 en desarrollo, que el motor calcula sin requerir esta decisión. Antes de CU-05.
- **En el motor:** `analisis_complementarios` en `config/poblaciones.yaml`. La población común y la cobertura temprana dentro de la comparación (RF-M2-10, RF-M2-11; DP-20f) no se construyeron porque dependen de esta decisión.

### DP-18: casos no etiquetables

- **Especificación:** excluir y contar por motivo, con reporte por cohorte y motivo (propuesta por defecto, que el equipo aceptó con CP-08 en REC-03, pendiente de la conformidad de la asesoría); análisis de sensibilidad; métodos de supervivencia (fuera del alcance). Antes de CU-03.
- **En el motor:** `no_etiquetables` en la definición del objetivo (tratamiento y nivel que exige un análisis de sensibilidad). Los no etiquetables nunca entran en entrenamiento ni evaluación, y se cuentan por cohorte y motivo, solo en desarrollo.

### DP-19: referencia R0 y controles

- **Especificación:** subcódigos DP-19a a DP-19e (sección 12.3), con recomendaciones técnicas no aprobadas. Antes de CU-05.
- **En el motor:** `referencia` en `config/experimentos.yaml` (ventana, conjunto y métrica). R0-fam y R-ven se construyen siempre. Desde F4.2, R-max (DP-19d) es una opción apagada (`r_max`).

### DP-20: protocolo de la evaluación comparativa

- **Especificación:** subcódigos DP-20a a DP-20g (sección 12.3), con recomendaciones técnicas no aprobadas. Depende de DP-08a, DP-08c, DP-08e, DP-08f, DP-08i y DP-17. Antes de CU-05.
- **En el motor:** `comparacion` en `config/experimentos.yaml` (métricas, márgenes y nivel). Desde F4.2, la estabilidad de la selección (CMP-5; DP-20g) es una opción apagada (`estabilidad`). La comparación nunca declara superioridad.

## 4. Pendientes de la asesoría que no son decisiones DP

- Aprobación formal de la Fase 1.
- Conformidad con REC-01 a REC-03 (aceptadas por el equipo).
- Comparador B del OE3.
- Conformidad con DP-08h.

## 5. Advertencias

- Los valores de `config/ejemplos/` son inventados. No deben copiarse a la configuración del proyecto como si fueran decisiones.
- Lo observado con datos sintéticos describe al generador del OE3 y a los supuestos de los ejemplos. No dice qué ventana o qué bloques bastan en una universidad real, ni que el método esté validado.
- Ninguna decisión debe cerrarse para facilitar la programación.
