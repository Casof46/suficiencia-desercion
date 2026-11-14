# Informe de cierre de la Fase 4: completar el motor con datos sintéticos

| Campo | Valor |
| --- | --- |
| Proyecto | Método temporal para determinar la suficiencia de información en la detección temprana del riesgo de deserción académica |
| Fecha | 13 de noviembre de 2026 |
| Base | Especificación Fase 1 v0.6; plan de la Fase 4 (`docs/gestion/plan_fase_4_propuesta.md`); informe de cierre de la Fase 3 |
| Repositorio | `Casof46/suficiencia-desercion`, rama `main` |
| Estado | **Fase 4 cerrada: los cuatro hitos de construcción y este informe aceptados por el equipo** el 13 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026). **La asesoría dio su conformidad con este informe** el 13 de noviembre de 2026 (comunicado por Jorge). Esa conformidad no incluye la aprobación formal de la Fase 1, la conformidad con REC-01 a REC-03 ni el comparador B del OE3, que siguen pendientes |

## 1. Resumen

La Fase 4 completó requisitos de reproducibilidad (N2) y complementarios (N3) que no dependen de una decisión abierta, o que entran como opciones apagadas. También ensayó el método completo con el dataset sintético del OE3. Todo sigue siendo **con datos sintéticos y configuraciones ficticias**. Hoy, además de lo construido hasta la Fase 3, el motor:

- escribe el reporte de una evaluación registrada y el de los escenarios en validación, por ventana y conjunto y por familia, leyéndolos del registro (F4.1);
- recorre el método completo con el dataset sintético del OE3: 40 variables, 12 cohortes y 28 escenarios factibles. Antes comprueba las huellas del dataset regenerado, y compara su etiqueta con la del generador (F4.3);
- describe, si se enciende, la estabilidad de la selección por fold de desarrollo, la estabilidad de las explicaciones entre folds y el referente R-max (F4.2);
- muestra en el visor el estado de las decisiones, desactiva la versión con datos del proyecto de cada función mientras sus decisiones sigan abiertas, y lista y compara el historial de experimentos (F4.4).

En el registro del proyecto todo sigue siendo **exploratorio**: no hay protocolo aprobado. **Ningún resultado de esta fase dice nada sobre la eficacia del método ni sobre estudiantes reales**: los resultados del ensayo reflejan los supuestos del generador sintético. Ninguna decisión metodológica se resolvió (sección 5).

## 2. Hitos

| Hito | Contenido | Commit | Windows (PC de Jorge, Python 3.13.0) | Aceptación del equipo |
| --- | --- | --- | --- | --- |
| F4.1 | Reportes desde el registro y comparación de escenarios por ventana y conjunto | `028606c` | Cinco `OK`; 908 pasan y 1 se omite | 12-11-2026 |
| F4.3 | Ensayo general con el dataset sintético del OE3; corrección del preprocesamiento | `3f7e8e5` | Cinco `OK`; 944 pasan y 1 se omite; método completo con 28 escenarios | 13-11-2026 |
| F4.2 | Estabilidad de la selección y de las explicaciones, y R-max (opcionales) | `00ede20` | Cinco `OK`; 956 pasan y 1 se omite | 13-11-2026 |
| F4.4 | Decisiones abiertas e historial de experimentos en el visor | `d117698` | Cinco `OK`; 971 pasan y 1 se omite | 13-11-2026 |

El orden fue el que aprobó el equipo: F4.1, F4.3, F4.2 y F4.4. La prueba que se omite en Windows crea un enlace simbólico, que el sistema no permite sin permisos especiales. Todas las aceptaciones las comunicó Jorge en nombre del equipo y están confirmadas por Javier el 13 de noviembre de 2026. El detalle de cada hito está en `docs/gestion/registro_f4_*.md`, sus decisiones técnicas en `docs/arquitectura/decisiones_f4_*.md` (D-195 a D-219) y sus pruebas en `docs/desarrollo/pruebas_f4_*.md`.

Al cierre, el proyecto tiene 439 funciones de prueba (972 casos con sus parámetros). En cada hito se introdujeron errores a propósito para comprobar que las pruebas los detectan: 29 controles negativos en la fase, todos detectados.

## 3. Criterios de la fase

| Criterio (plan de la Fase 4, sección 2) | Estado | Evidencia |
| --- | --- | --- |
| Solo datos sintéticos; el importador rechaza lo demás (regla 1) | Cumplido | El dataset del OE3 se convierte con `origen_datos = SINTETICO` (F4.3) |
| Solo modo exploratorio en el registro del proyecto; lo confirmatorio, solo en demostraciones (regla 2) | Cumplido | `registro_f4_1.md` a `registro_f4_4.md` |
| Ninguna DP-xx se cierra para facilitar la programación (regla 3) | Cumplido. DP-19d y DP-20g entran como opciones apagadas por omisión (F4.2). Las diferencias entre el motor y el generador del OE3 quedaron documentadas, sin cambiar el motor (F4.3) | Sección 5 |
| La prueba sigue sellada (regla 4) | Cumplido. Las métricas por cohorte de CMP-5 y R-max usan el único acceso de la evaluación final; la comparación de etiquetas del ensayo mira solo desarrollo | `test_estabilidad_demostracion.py`, `test_ensayo_oe3.py` |
| Bibliotecas nuevas solo si un hito las necesita (regla 5) | Cumplido: ninguna biblioteca nueva | Sección 4 |
| Mismo ciclo: Linux y luego Windows; registro, decisiones y pruebas; el commit lo hace el equipo (regla 6) | Cumplido | Sección 2 |
| Instalación desde el README en un entorno limpio | Cumplido en Linux: clon nuevo desde GitHub (commit `d117698`) con Python 3.12.3; cinco `OK` y 972 pasan, incluida la prueba de privacidad que necesita git. En Windows se verificó cada hito sobre el entorno existente | `docs/gestion/evidencia_fase_4/instalacion_limpia_linux.txt` |

## 4. Bibliotecas

Ninguna biblioteca nueva en la Fase 4. El generador del dataset del OE3 usa numpy, pandas y openpyxl, que ya estaban en el entorno.

## 5. Decisiones metodológicas

- **Ninguna DP-xx se resolvió en la Fase 4.**
- **Decididas antes:** DP-16 (SQLite), que está en el registro del proyecto, y el subcódigo DP-08h (se permite un piloto; informe de cierre de la Fase 3), ambas confirmadas por Javier el 13 de noviembre de 2026. Según `suficiencia decisiones` en la PC del proyecto, hoy hay 1 decisión registrada (DP-16) y 19 abiertas.
- **Nuevas como opciones apagadas:** el referente R-max (DP-19d), la estabilidad de la selección (CMP-5; DP-20g) y la estabilidad de las explicaciones entre folds (RF-M5-06; DP-11). Solo se encienden en ejemplos ficticios.
- **Datos para DP-01, no decisiones:** el ensayo con el OE3 mostró que el motor y el generador difieren en cómo confirman el evento cuando hay reservas al final del horizonte o en el ciclo H+1, y en el fallecimiento en H+1. En desarrollo coinciden 2655 de 2681 etiquetas. El equipo decidió dejarlo documentado (`decisiones_f4_3.md`).

## 6. Desviaciones respecto del plan

| Qué preveía | Qué se hizo | Quién lo decidió |
| --- | --- | --- |
| F4.3: usar solo el archivo ancho del dataset del OE3 | Combinar el ancho y el longitudinal del mismo generador, con un script fuera del motor: el ancho no trae el estado de matrícula por ciclo (D-202) | Equipo, al aceptar F4.3 |
| F4.2: estabilidad de las explicaciones entre semillas y folds | Solo entre folds: entre semillas habría que reentrenar los modelos (D-212) | Equipo, al aceptar F4.2 |
| F4.4: revisión visual en Windows | Revisión visual en Linux; en Windows corrieron las pruebas de las páginas (D-219) | Equipo, al aceptar F4.4 |
| No previsto | Corrección del orden de columnas del preprocesamiento, que el ensayo con el OE3 puso en evidencia (D-203) | Equipo, al aceptar F4.3 |
| No previsto | El historial del ensayo se escribe con fin de línea LF, para que su huella sea la misma en Windows y en Linux (D-208) | Técnico |

## 7. Limitaciones conocidas

**De alcance**
- No se pueden importar datos reales (DP-02, DP-14). La seudonimización no equivale a anonimización. El proyecto no cuenta hoy con datos institucionales autorizados.
- La evaluación final, la comparación, las explicaciones y la estabilidad exigen un protocolo aprobado; en el proyecto no hay ninguno, así que solo funcionan en la demostración.
- El ensayo con el OE3 usa un generador con relaciones inventadas. Muestra que el motor recorre el método de punta a punta con datos de esa estructura, no qué ventana o qué bloques bastan en una universidad real.

**Técnicas**
- El ensayo con el OE3 usa la población D1 del motor, que incluye a estudiantes que el generador saca de R(t); sus variables desde T1 quedan vacías y se imputan (`decisiones_f4_3.md`).
- Las selecciones de familia pueden variar entre sistemas y entre ejecuciones de la demostración: la clave de seudonimización es aleatoria y el margen de selección es pequeño. La regla y el estado de la comparación coincidieron en Linux y Windows.
- La verificación completa en Windows ya tarda entre 25 y 30 minutos.
- La lista de decisiones de cada función del visor se mantiene a mano.
- Siguen vigentes las limitaciones técnicas de las Fases 2 y 3.

## 8. Qué sigue (propuesta, no aprobada)

1. **Asesoría:** la aprobación formal de la Fase 1; la conformidad con REC-01 a REC-03; el comparador B del OE3.
2. **Decisiones metodológicas:** cerrar, con la asesoría donde corresponda, las que exige el protocolo (DP-06 a DP-12, DP-17, DP-19 y DP-20) y redactar el protocolo real. Las diferencias entre el motor y el generador del OE3 pueden servir de insumo para DP-01. Ninguna decisión debe cerrarse para facilitar la programación.
3. **Datos reales:** solo después de resolver DP-01, DP-02, DP-14, DP-15 y DP-18 y de cumplir las condiciones de la sección H.1 de la auditoría de la Fase 1, entre ellas la autorización institucional, que hoy no existe. Los datos institucionales no se envían a servicios externos ni a asistentes de IA.

La validación del OE3 con estudiantes reales exige los datos autorizados y el protocolo aprobado por el equipo y la asesoría.

## 9. Aceptación

| Rol | Nombre | Fecha | Conformidad |
| --- | --- | --- | --- |
| Equipo | Javier Barquinero | 13-11-2026 | Confirma la aceptación del equipo |
| Equipo | Jorge Caso | 13-11-2026 | Aceptación del informe y de los cuatro hitos comunicada en nombre del equipo |
| Asesoría | | 13-11-2026 | Conformidad con este informe (comunicada por Jorge) |
