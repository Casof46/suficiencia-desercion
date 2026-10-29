# Acta de cierre de la Fase 1 — PROPUESTA

> **Estado: propuesta sin firmar, con decisiones parciales del equipo.** Cada casilla se marca y cada espacio se completa solo cuando la persona indicada lo confirme expresamente. El 28 de octubre de 2026, Jorge comunicó en nombre del equipo las decisiones marcadas en los apartados 5.1 y 6; falta que Javier las confirme y la firma de ambos en el apartado 8. REC-01 a REC-03 y las decisiones DP-01 a DP-20 siguen sin aceptar ni resolver.

## 1. Identificación

| Campo | Valor |
| --- | --- |
| Proyecto | Método temporal para determinar la suficiencia de información en la detección temprana del riesgo de deserción académica |
| Documento revisado | "Fase 1 — Especificación funcional y arquitectura de software", versión 0.5 |
| Ubicación vigente | Documento en línea de la especificación (revisión 179 del historial). Copia de referencia en `docs/especificacion/` |
| Documentos de apoyo | "Fase 1 — Auditoría final y acta de cierre"; "Cierre de la Fase 1 — Paquete de revisión y decisión" (referencia histórica) |
| Versiones anteriores | v0.4 (revisión 114), v0.3 (revisión 79) y v0.2 (revisión 46) en el historial del documento |
| Fecha de preparación de esta propuesta | 21 de octubre de 2026; actualizada a la v0.5 el 28 de octubre de 2026 |
| Fecha de la reunión de cierre | ____________________ |

## 2. Alcance revisado

La Fase 1 especifica la aplicación web experimental local que ejecutará el método temporal. No incluye código de la aplicación, datos, métricas ni resultados. La especificación v0.5 contiene:

- Visión, alcance y supuestos (sección 1).
- 74 requisitos funcionales y 19 no funcionales, con origen y nivel N1, N2 o N3 (sección 2).
- 12 casos de uso, con su orden de ejecución (sección 3).
- Los seis módulos M1 a M6, la comparabilidad temporal con los diseños D1, D2 y D3, el protocolo en cuatro etapas E1 a E4 y la evaluación comparativa frente a la referencia convencional R0 (sección 4, M4).
- Arquitectura de cinco capas, dependencias y alcance de la reproducibilidad (sección 5).
- Estructura del repositorio y modelo conceptual de datos con 25 entidades (secciones 6 y 7).
- Cuatro diagramas Mermaid (secciones 5, 7, 8.1 y 8.2).
- 48 pruebas definidas, ninguna ejecutable todavía porque no existe código de la aplicación (sección 9).
- Plan de evolución, 29 riesgos, 20 decisiones pendientes y 26 criterios de aceptación (secciones 10 a 13).

Quedan fuera de este cierre las decisiones metodológicas DP-01 a DP-20, que siguen abiertas y tienen su propio calendario.

## 3. Estado de los criterios de aceptación

Según la sección 16 de la v0.5:

| Estado | Criterios | Total |
| --- | --- | --- |
| Cumplido y verificado (comprobación ejecutada) | CA-02, CA-03, CA-17, CA-19, CA-26 | 5 |
| Cumplido documentalmente, pendiente de comprobación | CA-01, 04, 05, 06, 07, 08, 09, 11, 12, 13, 14, 15, 18, 20, 25 | 15 |
| Pendiente de decisión del equipo | CA-16, 21, 22, 23, 24 | 5 |
| Pendiente de aprobación de la asesoría | CA-10 | 1 |
| Pendiente de autorización o información institucional | — | 0 |
| Bloqueado por una dependencia técnica | — | 0 |

De los 15 criterios cumplidos documentalmente:

- 9 se cierran con la confirmación del equipo en esta acta: CA-01, 04, 05, 06, 07, 08, 09, 18 y 20.
- 1 se cierra con la revisión metodológica de la asesoría, junto con CA-10: CA-25.
- 5 se comprueban ejecutando pruebas en los hitos H2.0 y H2.1: CA-11 a CA-15. Se propone que no condicionen la aprobación de la Fase 1.

## 4. Decisiones pendientes

**Del equipo (Javier y Jorge):** REC-04 (priorización N1–N3), REC-05 (dependencias y nombre del paquete), responsables de los 29 riesgos (CA-21), alcance autorizado de la Fase 2 (CA-24), y DP-06, DP-07, DP-11, DP-12 y DP-16.

**De la asesoría:** REC-01 (validación cronológica), REC-02 (protocolo en cuatro etapas), REC-03 (exclusión de no etiquetables); DP-01, DP-03, DP-04, DP-05 junto con DP-08h, DP-08a a DP-08g, DP-09, DP-10, DP-13, DP-17 y DP-18; y su revisión de la Fase 1 (CA-10), que incluye el diseño comparativo (CA-25).

**Del equipo y la asesoría conjuntamente:** DP-19 (referencia convencional R0 y controles) y DP-20 (protocolo comparativo, incluido el margen de no inferioridad frente a R0).


**De la institución:** DP-02 (autorización de uso y dictamen ético), DP-14 (protección y custodia de la correspondencia), DP-15 (formato de los archivos e historial de matrícula), DP-08i (capacidad de alerta q), y la información necesaria para DP-01, DP-03, DP-05, DP-18 y DP-19a (ventana de decisión vigente, si existe).

## 5. Condiciones de aprobación

**5.1 Confirmaciones del equipo**

- [ ] Leímos la v0.5 y confirmamos CA-01, CA-04, CA-06, CA-08, CA-09 y CA-20.
- [ ] Revisamos la cadena de dependencias de los apartados 14.3 y 14.4 y confirmamos CA-05 y CA-07.
- [ ] Abrimos la especificación en el visor y los cuatro diagramas se ven completos en las secciones 5, 7, 8.1 y 8.2 (CA-18).
- [x] REC-04, priorización N1–N3: **aceptada** (28 de octubre de 2026). Detalle: sin modificaciones; los hitos siguen el orden del plan y la interfaz completa se construye después del motor.
- [x] REC-05, dependencias y nombre del paquete: **aceptada** (28 de octubre de 2026). Nombre del paquete: `suficiencia`. Cada dependencia se añade en el hito que la usa.
- [ ] Responsable asignado a cada uno de los 29 riesgos de la sección 11 (CA-21).
- [x] Alcance de la Fase 2: se autorizan los hitos **H2.1 a H2.3** (28 de octubre de 2026) (CA-24). H2.4 en adelante esperan al apartado 5.2.

**5.2 Confirmaciones de la asesoría**

- [ ] REC-01, validación cronológica: conforme / con cambios / no conforme. Detalle: ____________________
- [ ] REC-02, protocolo en cuatro etapas, y DP-08h (piloto): conforme / con cambios / no conforme. Detalle: ____________________
- [ ] REC-03, exclusión de no etiquetables: conforme / con cambios / no conforme. Detalle: ____________________
- [ ] Calendario acordado para DP-01, DP-04, DP-05 con DP-08h, DP-08, DP-17, DP-18, DP-19 y DP-20 (CA-10): ____________________
- [ ] Diseño de la evaluación comparativa frente a R0 (sección 4, M4; CA-25): conforme / con cambios / no conforme. Detalle: ____________________

**5.3 Decisión de cierre (marcar una)**

- [ ] Fase 1 aprobada formalmente: los apartados 5.1 y 5.2 están completos.
- [ ] Fase 1 aprobada con condiciones: el apartado 5.1 está completo y se autorizan H2.0 a H2.3. Los hitos H2.4 a H2.6 quedan condicionados al apartado 5.2.
- [ ] Fase 1 no aprobada. Motivo: ____________________

Recomendación técnica, no vinculante: la segunda opción. H2.0 a H2.3 no dependen de ninguna decisión metodológica y no fijan valores metodológicos en el código.

## 6. Alcance para iniciar H2.0

**Condición documentada:** H2.0 (repositorio y entorno reproducible) no depende de ninguna decisión DP ni de REC-01 a REC-03. Depende de REC-05 solo en dos aspectos reversibles: el nombre del paquete y la lista de dependencias. Por eso puede iniciarse con un contrato provisional:

- El nombre `suficiencia` se usa como provisional.
- Solo se instalan las dependencias que el propio H2.0 necesita.
- sqlite3 no se incorpora, porque DP-16 está pendiente.

**Hecho registrado:** el 21 de octubre de 2026, a pedido de Javier, se ejecutó técnicamente H2.0 con ese contrato provisional, antes de la firma de esta acta. Esa ejecución **no equivale a la aprobación formal de la Fase 1** ni a la aceptación de REC-05. Su aceptación como hito queda sujeta a:

- [ ] Que el equipo apruebe la Fase 1 con o sin condiciones (apartado 5.3).
- [x] Que el equipo decida REC-05 y, si cambia el nombre del paquete o la lista de dependencias, que se ajuste el repositorio. Aceptada sin cambios; no hubo que ajustar nada.
- [x] Que un miembro del equipo reproduzca la instalación y las comprobaciones en Windows siguiendo `docs/desarrollo/entorno_reproducible.md`. Hecho el 28 de octubre de 2026 en la PC de Jorge.

Aceptación de H2.0 por el equipo: **aceptado**. Comunicado por: Jorge, en nombre del equipo; pendiente de confirmación de Javier. Fecha: 28 de octubre de 2026. Verificado en Windows con Python 3.13.0 en la PC de Jorge (84 pruebas pasan); ver `docs/gestion/registro_h2_0.md`.

Aceptación de los hitos siguientes por el equipo:

| Hito | Decisión | Comunicado por | Fecha | Evidencia |
| --- | --- | --- | --- | --- |
| H2.1 — Arquitectura y contratos | **Aceptado** | Jorge, en nombre del equipo; pendiente de confirmación de Javier | 28 de octubre de 2026 | `docs/gestion/registro_h2_1.md`; 150 pruebas en Windows; commit `10aefee` |
| H2.2 — Ventanas, conjuntos, escenarios y anti-fuga | **Aceptado** | Jorge, en nombre del equipo; pendiente de confirmación de Javier | 28 de octubre de 2026 | `docs/gestion/registro_h2_2.md`; 206 pruebas en Windows; commit `0abfc82` |
| H2.3 — Datos sintéticos, diccionario, importación, auditoría y seudonimización | **Aceptado** | Jorge, en nombre del equipo; pendiente de confirmación de Javier | 29 de octubre de 2026 | `docs/gestion/registro_h2_3.md`; 281 pruebas en Windows; commit `d8d8319` |

Decisiones y autorizaciones posteriores del equipo:

| Fecha | Decisión | Comunicado por | Registro |
| --- | --- | --- | --- |
| 29 de octubre de 2026 | **DP-16 decidida: SQLite** para el registro de experimentos, decisiones y accesos (`workspace/registro.sqlite`) | Jorge, en nombre del equipo; pendiente de confirmación de Javier | `docs/decisiones/DP-16.md` |
| 29 de octubre de 2026 | **Se autoriza H2.7** (trazabilidad y registro), que dependía de H2.3 y DP-16 | Jorge, en nombre del equipo; pendiente de confirmación de Javier | Este apartado |

H2.4 a H2.6 siguen esperando la revisión de la asesoría (apartado 5.2).

La decisión de cierre del apartado 5.3 sigue sin marcar: el equipo aceptó H2.0 y autorizó H2.1 a H2.3 sin esperar la aprobación formal de la Fase 1 ni la revisión de la asesoría. Esos hitos no dependen de ninguna decisión metodológica.

## 7. Actividades expresamente excluidas de esta autorización

- Hitos H2.4 a H2.6 y H2.8. (H2.1 a H2.3 quedaron autorizados en el apartado 5.1, y H2.7 el 29 de octubre de 2026.)
- Cualquier carga, copia o procesamiento de datos institucionales reales.
- La definición de deserción, los umbrales o márgenes de suficiencia, los cortes cronológicos, los procedimientos de multiplicidad, la referencia R0, el margen de no inferioridad frente a ella y cualquier otro valor metodológico.
- Entrenamiento de modelos, selección de modelos, evaluación final, evaluación comparativa frente a R0 e interpretabilidad (SHAP y LIME).
- La interfaz Streamlit, salvo su archivo de configuración con la telemetría desactivada.
- Otra base de datos distinta de SQLite (DP-16 se decidió por SQLite, solo para el registro local en `workspace/`).
- Servicios cloud, servidores institucionales, autenticación, credenciales o servicios de pago.
- El envío de datos institucionales a servicios externos o asistentes de IA.

## 8. Responsables

| Rol | Nombre | Decisión registrada | Fecha | Firma |
| --- | --- | --- | --- | --- |
| Tesista | Javier ____________________ | ____________________ | __________ | __________ |
| Tesista | Jorge ____________________ | ____________________ | __________ | __________ |
| Asesoría | ____________________ | ____________________ | __________ | __________ |

Observaciones:

____________________________________________________________________

____________________________________________________________________
