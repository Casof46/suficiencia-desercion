# Plan de la Fase 3 — entrenamiento y evaluación con datos sintéticos

| Campo | Valor |
| --- | --- |
| Fecha | 11 de noviembre de 2026 |
| Aprobación | El equipo aprobó empezar la Fase 3 con esta secuencia el 11 de noviembre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier). La asesoría dio su conformidad con el informe de cierre de la Fase 2, que propone esta secuencia; **no** se ha pronunciado todavía sobre este plan |
| Base | Especificación Fase 1 v0.6 (M3, M4, M5); informe de cierre de la Fase 2, sección 7; informe de avance del OE3 |

## 1. Reglas de la fase

1. **Solo datos sintéticos.** El importador sigue rechazando todo archivo sin la marca de origen sintético (DP-02, DP-14). Ningún resultado de esta fase es evidencia sobre estudiantes reales ni sobre la eficacia del método.
2. **Solo modo exploratorio en el registro del proyecto.** No hay protocolo aprobado, y el ejemplo ficticio no se puede aprobar. Todo lo confirmatorio (congelar, evaluación final, regla en modo confirmatorio) se ejercita solo en registros temporales de demostración, como en H2.6.
3. **Cada decisión abierta entra como dato obligatorio**, con un ejemplo rotulado "EJEMPLO FICTICIO" en `config/ejemplos/`. Sin el archivo del proyecto, el programa se detiene con la decisión pendiente. Las decisiones afectadas son DP-03, DP-06, DP-07, DP-09, DP-10, DP-11, DP-12, DP-19 y DP-20.
4. **La prueba sigue sellada.** El desarrollo nunca la lee. La única lectura es la evaluación final, en modo demostración.
5. **Bibliotecas nuevas solo en el hito que las usa**, fijadas en `requirements.lock` con hashes y con versiones publicadas al menos dos semanas antes (D-92).
6. **Mismo ciclo que la Fase 2:** Linux y luego Windows; registro, decisiones y pruebas de cada hito; commit lo hace el equipo.

## 2. Hitos

| Hito | Objetivo | Componentes | Pruebas de la especificación | Bibliotecas |
| --- | --- | --- | --- | --- |
| F3.1 | Datos listos para entrenar sin fuga | Generador sintético ampliado (12 cohortes); matrices por ventana y escenario solo con desarrollo; folds rolling-origin por cohortes (DP-07 como datos); preprocesamiento ajustado dentro de cada fold (DP-12 como datos) | PI-01, PI-07 (folds), PI-08 (cohortes por fold), PU-12 | scikit-learn |
| F3.2 | Los cinco modelos | Fábrica de LR, RF, XGBoost, LightGBM y SVM; búsqueda de hiperparámetros con espacio y presupuesto como datos (DP-07); desbalance dentro del fold (DP-06); calibración (DP-09); semillas; corridas registradas | PI-06, PI-08 (búsqueda), PI-11, PI-12, RF-M3-05 a 09 | XGBoost, LightGBM |
| F3.3 | Métricas e intervalos | AUC-ROC, Brier, Recall@q y las secundarias; prevalencia junto a cada métrica; bootstrap pareado; diferencias | PU-07, PU-20, PU-24 | — |
| F3.4 | Selección y evaluación final | Modelo por escenario (DP-10) y umbral (DP-06) solo con validación; congelamiento con huella; evaluación final con apertura única (demostración); regla de suficiencia sobre resultados reales del motor | PI-09, PI-10, PI-15 | — |
| F3.5 | Comparación con la referencia | R0 y controles (DP-19); diferencias pareadas, no inferioridad, anticipación y estados C1 a C8 (DP-20) | PU-22 a PU-27 | — |
| F3.6 | Interpretabilidad | SHAP y LIME sobre configuraciones congeladas; importancia por bloque (DP-11) | PU-21, PI-13 | SHAP, LIME |
| F3.7 | Resultados en el visor y reporte | Páginas de resultados con rótulo sintético; exportación | PI-16 | Plotly, si se aprueba |

Cada hito tiene su registro (`registro_f3_x.md`), sus decisiones técnicas (`decisiones_f3_x.md`) y sus pruebas (`pruebas_f3_x.md`).

## 3. No implementar en la Fase 3

- Datos reales, conexión con sistemas de la universidad o servicios externos.
- Valores reales para cualquier decisión abierta.
- Conclusiones sobre el método: las salidas reflejan los supuestos del generador sintético.

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| La asesoría cambia REC-01 a REC-03 o el diseño comparativo | Los hitos que dependen de ellos se ajustan; todo valor está parametrizado |
| Tiempo de entrenamiento alto en la PC del equipo (28 escenarios × 5 familias × folds) | Presupuesto de búsqueda como dato; ejecución por lotes y reanudable (RF-M3-08) |
| Una biblioteca nueva no instala en Windows | Verificación en Windows en cada hito, antes del commit |
