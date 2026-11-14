# Informe de cierre de la Fase 3 — entrenamiento y evaluación con datos sintéticos

| Campo | Valor |
| --- | --- |
| Proyecto | Método temporal para determinar la suficiencia de información en la detección temprana del riesgo de deserción académica |
| Fecha | 12 de noviembre de 2026 |
| Base | Especificación Fase 1 v0.6; plan de la Fase 3 (`docs/gestion/plan_fase_3.md`); informe de cierre de la Fase 2 |
| Repositorio | `Casof46/suficiencia-desercion`, rama `main` |
| Estado | **Fase 3 cerrada: los siete hitos aceptados por el equipo** (el último, el 12 de noviembre de 2026; comunicado por Jorge, confirmado por Javier el 13 de noviembre de 2026). **La asesoría dio su conformidad con este informe** el 12 de noviembre de 2026 (comunicado por Jorge). Esa conformidad no incluye la aprobación formal de la Fase 1, la conformidad con REC-01 a REC-03 ni el comparador B del OE3, que siguen pendientes |

## 1. Resumen

La Fase 3 completó el recorrido del método **con datos sintéticos y configuraciones ficticias**. Hoy el motor:

- arma las matrices de cada escenario sin fuga y los folds cronológicos por cohortes, y ajusta el preprocesamiento dentro de cada fold;
- entrena las cinco familias (regresión logística, Random Forest, XGBoost, LightGBM y SVM), con búsqueda de hiperparámetros, desbalance y calibración como datos;
- calcula AUC-ROC, Brier, Brier escalado y Recall@q con la prevalencia, intervalos bootstrap estratificados y diferencias pareadas;
- selecciona modelo y umbral por escenario solo con desarrollo;
- ejecuta la evaluación final abriendo la prueba una sola vez y aplica la regla de suficiencia;
- compara con la referencia R0 y sus controles: no inferioridad, anticipación, reducción de información y estados C1 a C8;
- explica las configuraciones congeladas con SHAP y LIME, por variable y por bloque;
- muestra los resultados en el visor con gráficos Plotly y exporta un reporte, todo rotulado como datos sintéticos.

En el registro del proyecto todo es **exploratorio**: no hay protocolo aprobado, y el protocolo de ejemplo es ficticio y no se puede aprobar. La evaluación final, la comparación y las explicaciones solo se ejercitan en una demostración que usa un proyecto temporal. **Ningún resultado de esta fase dice nada sobre la eficacia del método ni sobre estudiantes reales**: refleja los supuestos del generador sintético. Ninguna decisión metodológica se resolvió en esta fase (sección 5).

## 2. Hitos

| Hito | Contenido | Commit | Windows (PC de Jorge, Python 3.13.0) | Aceptación del equipo |
| --- | --- | --- | --- | --- |
| F3.1 | Historial sintético ampliado, matrices por escenario, folds y preprocesamiento por fold | `0917025` | Cinco `OK`; 645 pasan | 11-11-2026 |
| F3.2 | Las cinco familias, búsqueda, desbalance, calibración y corridas registradas | `1122610` | Cinco `OK`; 698 pasan | 12-11-2026 |
| F3.3 | Métricas con prevalencia, intervalos bootstrap y diferencias pareadas | `791a532` | Cinco `OK`; 733 pasan | 12-11-2026 |
| F3.4 | Selección de modelo y umbral; evaluación final con apertura única; demostración | `df5d69c` | Cinco `OK`; 768 pasan y 1 se omite | 12-11-2026 |
| F3.5 | Referencia R0 y controles, no inferioridad, anticipación y estados C1 a C8 | `a6e1d90` | Cinco `OK`; 812 pasan y 1 se omite | 12-11-2026 |
| F3.6 | Interpretabilidad con SHAP y LIME, importancia por bloque | `3080984` | Cinco `OK`; 875 pasan y 1 se omite | 12-11-2026 |
| F3.7 | Rótulo de datos sintéticos, reporte de resultados y página de resultados con Plotly | `6769282` | Cinco `OK`; 902 pasan y 1 se omite | 12-11-2026 |

La prueba que se omite en Windows crea un enlace simbólico, que Windows no permite sin permisos especiales. Todas las aceptaciones las comunicó Jorge en nombre del equipo y están confirmadas por Javier el 13 de noviembre de 2026. El detalle de cada hito está en `docs/gestion/registro_f3_*.md`, sus decisiones técnicas en `docs/arquitectura/decisiones_f3_*.md` (D-127 a D-194) y sus pruebas en `docs/desarrollo/pruebas_f3_*.md`.

Al cierre, el proyecto tiene 402 funciones de prueba (903 casos con sus parámetros). En cada hito se introdujeron errores a propósito para comprobar que las pruebas los detectan: 52 controles negativos en la fase, todos detectados.

## 3. Criterios de la fase

| Criterio (plan de la Fase 3) | Estado | Evidencia |
| --- | --- | --- |
| Solo datos sintéticos; el importador rechaza lo demás (regla 1) | Cumplido | Pruebas de importación desde H2.3; rótulo de F3.7 |
| Solo modo exploratorio en el registro del proyecto; lo confirmatorio solo en demostración (regla 2) | Cumplido | `registro_f3_4.md` a `registro_f3_7.md` |
| Cada decisión abierta entra como dato obligatorio, con ejemplo ficticio (regla 3) | Cumplido para DP-03, DP-06, DP-07, DP-08a, DP-08e, DP-08i, DP-09, DP-10, DP-11, DP-12, DP-19 y DP-20 | `config/ejemplos/experimentos_ficticio.yaml`; pruebas de `null` → decisión pendiente |
| La prueba sigue sellada; una sola lectura, en la evaluación final (regla 4) | Cumplido | PI-10, PI-15; la comparación y las explicaciones no agregan accesos |
| Bibliotecas nuevas solo en su hito, fijadas con hashes (regla 5) | Cumplido | Sección 4 |
| Verificación en Linux y Windows antes de cada commit (regla 6) | Cumplido | Sección 2 |
| Instalación desde el README en un entorno limpio | Cumplido en Linux: clon nuevo desde GitHub (commit `6769282`) con Python 3.12.3; cinco `OK` y 903 pasan, incluida la prueba de privacidad que necesita git. En Windows se verificó cada hito sobre el entorno existente, reinstalado desde `requirements.lock`; no se hizo un clon nuevo | `docs/gestion/evidencia_fase_3/instalacion_limpia_linux.txt` |

## 4. Bibliotecas incorporadas

| Hito | Biblioteca | Versión |
| --- | --- | --- |
| F3.1 | scikit-learn (con joblib, scipy y threadpoolctl) | 1.9.1 |
| F3.2 | xgboost-cpu (limitado a `<3.3`) y lightgbm | 3.2.0 y 4.7.0 |
| F3.6 | shap (limitado a `<0.52`) y lime (con numba, llvmlite, matplotlib y scikit-image) | 0.51.0 y 0.2.0.1 |
| F3.7 | plotly, en el grupo opcional del visor | 7.1.0 |

Todas se instalan en el equipo y no envían datos a ningún servicio. Están fijadas en `requirements.lock` con hashes y publicadas antes del 28 de octubre de 2026 (D-92). Los límites de versión hacen que Linux (Python 3.11) y Windows (Python 3.13) usen las mismas versiones.

## 5. Decisiones metodológicas

- **Ninguna DP-xx se resolvió en la Fase 3.** Todas las que el entrenamiento necesita entraron como datos obligatorios con valores inventados (sección 3).
- **Decididas por el equipo antes de esta fase:** DP-16 (SQLite) y el subcódigo DP-08h (se permite un piloto), confirmadas por Javier el 13 de noviembre de 2026; DP-08h además espera la conformidad de la asesoría.
- **Abiertas:** las otras 19. Bloquean el uso de datos reales DP-01, DP-02, DP-14, DP-15 y DP-18. Deben cerrarse antes de aprobar el protocolo DP-06, DP-07, DP-08, DP-09, DP-10, DP-12, DP-17, DP-19 y DP-20; DP-11 decide el alcance de la interpretabilidad.
- **Recomendaciones:** REC-04 y REC-05 aceptadas por el equipo. REC-01 a REC-03 aceptadas por el equipo, pendientes de la conformidad de la asesoría.

## 6. Desviaciones respecto del plan

| Qué preveía | Qué se hizo | Quién lo decidió |
| --- | --- | --- |
| Plotly "si se aprueba" | Incorporado en F3.7 | Equipo, al aceptar F3.6 |
| F3.5: comparación completa | Sin R-max (opcional), sin estabilidad de la selección (CMP-5) y sin cobertura temprana dentro de la comparación, que necesita q (DP-08i) y D3 (DP-17) | Técnico (D-172) |
| F3.6: interpretabilidad completa | Sin estabilidad de las explicaciones (RF-M5-06, complementaria) | Técnico |
| F3.6: SHAP para árboles con muestra de fondo | Con las coberturas de los árboles: la otra variante no cumplía la aditividad con algunos Random Forest | Técnico (D-176) |
| F3.7: reporte comparativo del proyecto | Reporte de la demostración; el reporte leído del registro espera un protocolo aprobado | Técnico (D-191) |
| Carpetas `experimentation/explicadores/` y `ui/componentes/` | Un módulo por tema | Técnico |
| El plan no prevé un hito de cierre | Este informe, a pedido del equipo | Equipo, 12 de noviembre de 2026 |

## 7. Limitaciones conocidas

**De alcance**
- No se pueden importar datos reales: el importador exige la marca de origen sintético (DP-02, DP-14). La seudonimización no equivale a anonimización. El proyecto no cuenta hoy con datos institucionales autorizados.
- La evaluación final, la comparación y las explicaciones exigen un protocolo aprobado; en el proyecto no existe ninguno, así que solo funcionan en la demostración.
- Los resultados de la demostración dependen del generador sintético y de valores inventados. Ninguno es evidencia sobre el método.

**Del método (de la especificación, M4 y M5)**
- La incertidumbre no incluye el reentrenamiento ni la variación entre cohortes.
- La comparación no demuestra que alertar antes cause menos deserción; nunca se declara superioridad.
- Las explicaciones describen asociaciones del modelo, no causas.

**Técnicas**
- Las explicaciones SHAP y LIME usan la salida del modelo antes de la calibración (log-odds, probabilidad o margen, según la familia); la calibración no cambia el orden de riesgo, pero las contribuciones no están en la escala de la probabilidad final.
- KernelExplainer (SVM) es lento; se usa una muestra de fondo acotada.
- LIME solo se publica como código fuente: instalar el entorno necesita conexión a internet para construirlo.
- En macOS con procesador Intel, SHAP 0.51 no se puede instalar con NumPy 2. El equipo usa Windows y Linux.
- En Windows, la verificación completa tarda entre 14 y 20 minutos; si el equipo se suspende, queda en pausa.
- La página de resultados del visor se revisó con capturas en Linux; falta verla en el navegador de Windows.
- Siguen vigentes las limitaciones técnicas de la Fase 2: el sello protege la prueba dentro del programa, la cadena de huellas puede recalcularse completa, los seudónimos cambian con la clave efímera, y las cohortes deben ordenarse como texto.

## 8. Qué sigue (propuesta, no aprobada)

1. **Asesoría:** aprobación formal de la Fase 1; conformidad con REC-01 a REC-03; comparador B del OE3.
2. **Decisiones metodológicas:** cerrar, con la asesoría donde corresponda, las que exige el protocolo (DP-06 a DP-12, DP-17, DP-19 y DP-20) y redactar el protocolo real. Ninguna debe cerrarse para facilitar la programación.
3. **Datos reales:** solo después de resolver DP-01, DP-02, DP-14, DP-15 y DP-18 y de cumplir las condiciones de la sección H.1 de la auditoría de la Fase 1, entre ellas la autorización institucional, que hoy no existe. Los datos institucionales no se envían a servicios externos ni a asistentes de IA.
4. **Pendientes técnicos complementarios:** estabilidad de explicaciones y de la selección, R-max, reporte leído del registro, interfaz definitiva (RF-UI-01, RF-UI-04) e historial comparativo (RF-M6-02).

La validación del OE3 con estudiantes reales exige los datos autorizados y el protocolo aprobado por el equipo y la asesoría.

## 9. Aceptación

| Rol | Nombre | Fecha | Conformidad |
| --- | --- | --- | --- |
| Equipo | Javier Barquinero | 13-11-2026 | Confirma la aceptación del equipo |
| Equipo | Jorge Caso | 12-11-2026 | Aceptación de los siete hitos comunicada en nombre del equipo |
| Asesoría | | 12-11-2026 | Conformidad con este informe (comunicada por Jorge) |
