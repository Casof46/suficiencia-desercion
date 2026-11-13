# Plan de la Fase 4 — completar el motor con datos sintéticos

| Campo | Valor |
| --- | --- |
| Fecha | 12 de noviembre de 2026 |
| Estado | **Aprobada por el equipo** el 12 de noviembre de 2026, con el orden F4.1, F4.3, F4.2, F4.4 (comunicado por Jorge; pendiente de confirmación de Javier). Para F4.3, el dataset del OE3 se regenera con su script y su semilla. La asesoría **no** se ha pronunciado sobre este plan |
| Base | Especificación Fase 1 v0.6 (requisitos N2 y N3 pendientes); informe de cierre de la Fase 3, secciones 6 a 8; README del dataset sintético del OE3 |

## 1. Por qué una Fase 4 sin datos reales

El paso al OE3 con estudiantes reales no depende de programar más: depende del protocolo real, de cerrar las decisiones abiertas y de la autorización institucional de los datos, que hoy no existe (informe de cierre de la Fase 3, sección 8). Mientras eso avanza con la asesoría, quedan requisitos de la especificación que se pueden construir y probar con datos sintéticos:

- tres de reproducibilidad y trazabilidad (N2), que conviene tener antes del protocolo real;
- varios complementarios (N3) que no dependen de una decisión abierta;
- un ensayo general del método con el dataset sintético del OE3, más parecido en estructura a la base real que el historial de prueba actual.

## 2. Reglas de la fase

Las mismas de la Fase 3:

1. **Solo datos sintéticos.** El importador sigue rechazando todo archivo sin la marca de origen sintético (DP-02, DP-14).
2. **Solo modo exploratorio en el registro del proyecto.** Lo confirmatorio, solo en demostraciones con protocolo ficticio.
3. **Ninguna decisión DP-xx se cierra para facilitar la programación.** Lo que dependa de una decisión abierta entra como dato obligatorio con un ejemplo rotulado "EJEMPLO FICTICIO", o no se construye.
4. **La prueba sigue sellada.**
5. **Bibliotecas nuevas solo si un hito las necesita**, con aprobación del equipo y fijadas con hashes. Ningún hito propuesto las necesita.
6. **Mismo ciclo:** Linux y luego Windows; registro, decisiones y pruebas de cada hito; el commit lo hace el equipo.

## 3. Hitos propuestos

| Hito | Objetivo | Requisitos | Depende de una decisión abierta |
| --- | --- | --- | --- |
| F4.1 | Reportes del proyecto desde el registro: reporte comparativo de una evaluación registrada; tabla y gráfico de escenarios por ventana y conjunto; los cinco modelos de cada escenario en validación, en el reporte y en el visor (hoy solo en `experimentos metricas`) | RF-M6-07 (proyecto), RF-M4-10, RF-M4-14 (N2) | No. Sin protocolo aprobado, se prueba en la demostración |
| F4.2 | Estabilidad, descriptiva: de la selección por fold de desarrollo (sin inferencia entre cohortes) y de las explicaciones entre semillas y folds; referente R-max | RF-M4-22, RF-M5-06, RF-M4-16 (R-max) (N3) | RF-M4-22 y R-max quedan sujetos a DP-20 y DP-19d: entran como datos opcionales, apagados por omisión |
| F4.3 | Ensayo general con el dataset sintético del OE3: diccionario y configuraciones ficticias para sus 40 variables y 12 cohortes, y el método completo en demostración | — (prueba de extremo a extremo) | La integración de varias tablas (RF-M1-09) depende de DP-15: se usaría solo el archivo ancho (`wide`) ya integrado, salvo que el equipo decida otra cosa |
| F4.4 | Visor: estado de las decisiones y funciones desactivadas cuando dependen de una decisión abierta; historial de experimentos; revisión visual en Windows | RF-UI-04, RF-M6-02 (N3) | No |
| F4.5 | Cierre: informe de la Fase 4 | — | — |

Orden propuesto: F4.1 (N2, más útil para el protocolo real), F4.3, F4.2, F4.4. El equipo puede quitar o reordenar hitos.

## 4. No implementar en la Fase 4

- Datos reales, conexión con sistemas de la universidad o servicios externos.
- Valores reales para cualquier decisión abierta.
- Lo que solo existe si se aprueba una decisión abierta: población común entre ventanas y cobertura temprana (RF-M2-10, RF-M2-11; DP-17), curva de calibración en el criterio (RF-M4-02; DP-09), métricas por subgrupo (RF-M4-11; DP-13, que además exige atributos autorizados).
- Conclusiones sobre el método: las salidas reflejan los supuestos del generador sintético.

## 5. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El dataset del OE3 no está en el repositorio (se generó en otra sesión) | F4.3 empieza por traerlo, o por regenerarlo con su script y semilla, y comprobar sus huellas antes de usarlo |
| Las definiciones del dataset del OE3 (por ejemplo, el tratamiento del retiro total) difieren de las del motor | Se documentan como supuestos del ejemplo ficticio; no son decisiones (DP-01 sigue abierta) |
| Tiempo de verificación en Windows (14 a 20 minutos por hito, más si la PC se suspende) | Desactivar la suspensión mientras corre la verificación |
| La asesoría cambia el protocolo o una recomendación | Todo valor está parametrizado; los hitos afectados se ajustan |

## 6. Decisiones del equipo sobre este plan

1. Aprobado el 12 de noviembre de 2026.
2. Orden: F4.1, F4.3, F4.2, F4.4 y el cierre.
3. F4.3: el dataset del OE3 se regenera con su script y su semilla, y se comprueban sus huellas.
