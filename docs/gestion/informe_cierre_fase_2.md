# Informe de cierre de la Fase 2 — motor sin modelos

| Campo | Valor |
| --- | --- |
| Proyecto | Método temporal para determinar la suficiencia de información en la detección temprana del riesgo de deserción académica |
| Fecha | 11 de noviembre de 2026 |
| Base | Especificación Fase 1 v0.6; plan de la Fase 2 (paquete de cierre de la Fase 1, sección E) |
| Repositorio | `Casof46/suficiencia-desercion`, rama `main` |
| Estado | **Fase 2 cerrada: los diez hitos aceptados por el equipo** (el último, el 11 de noviembre de 2026; comunicado por Jorge, pendiente de confirmación de Javier). **La asesoría dio su conformidad con este informe** el 11 de noviembre de 2026 (comunicado por Jorge). Esa conformidad no incluye la aprobación formal de la Fase 1, REC-01 a REC-03 ni el comparador B del OE3, que siguen pendientes |

## 1. Resumen

La Fase 2 construyó el motor del método **sin entrenar ningún modelo y sin datos reales**. El motor hace hoy lo que el método necesita antes de entrenar:

- construye la matriz de 32 escenarios y verifica la fuga temporal;
- importa archivos marcados como sintéticos, los seudonimiza y audita su calidad;
- etiqueta a cada estudiante según una definición de deserción parametrizada;
- construye las poblaciones D1, D2 y D3, particiona por cohortes y sella la prueba;
- guarda un protocolo confirmatorio versionado que no se puede editar una vez aprobado;
- congela configuraciones con huella;
- aplica una regla de suficiencia que recibe el criterio como datos;
- registra todo en un registro de solo agregar.

Todo se probó con datos **sintéticos** y configuraciones **ficticias**. Ningún resultado de esta fase dice nada sobre la eficacia del método ni sobre estudiantes reales. No existe ningún criterio de suficiencia, definición de deserción ni protocolo aprobados: 19 de las 20 decisiones metodológicas siguen abiertas (sección 5).

## 2. Hitos

| Hito | Contenido | Commit | Windows (PC de Jorge, Python 3.13.0) | Aceptación del equipo |
| --- | --- | --- | --- | --- |
| H2.0 | Repositorio, entorno reproducible con bloqueo y hashes, bloqueo de red en las pruebas | `cb9a955` | Cinco `OK` | 28-10-2026 |
| H2.1 | Arquitectura por capas, contratos, línea de comandos | `10aefee` | Cinco `OK`; 206 pasan | 28-10-2026 |
| H2.2 | Ventanas, conjuntos, 32 escenarios y verificador anti-fuga | `0abfc82` | Cinco `OK` | 28-10-2026 |
| H2.3 | Datos sintéticos, diccionario, importación, auditoría y seudonimización | `d8d8319` | Cinco `OK`; 326 pasan | 29-10-2026 |
| H2.7 | Trazabilidad: registro SQLite de solo agregar (DP-16) | `0689a32` | Cinco `OK` | 29-10-2026 |
| H2.4 | Objetivo y estados de etiqueta (DP-01 parametrizada) | `a572a4b` | Cinco `OK`; 433 pasan | 29-10-2026 |
| H2.5 | Poblaciones D1 a D3, partición cronológica y sello de la prueba | `69e9efe` | Cinco `OK`; 470 pasan | 29-10-2026 |
| H2.D | Visor de demostración local (fuera del plan, a pedido del profesor) | `9ae248a` | Cinco `OK`; 486 pasan | 11-11-2026 |
| H2.6 | Protocolo versionado, desviaciones, congelamiento y regla de suficiencia; configuración de VS Code | `05fbed9`, `b4f3c1e` | Cinco `OK`; 584 pasan | 11-11-2026 |
| H2.8 | Comando `decisiones`, pruebas de aceptación de CU-03 a CU-05, PI-11 determinista, este informe | `0a32344`, `ae37410` | Cinco `OK`; 600 pasan, también en un clon nuevo | 11-11-2026 |

Todas las aceptaciones las comunicó Jorge en nombre del equipo y están pendientes de confirmación de Javier. El detalle de cada hito está en `docs/gestion/registro_h2_*.md`, sus decisiones técnicas en `docs/arquitectura/decisiones_h2_*.md` y sus pruebas en `docs/desarrollo/pruebas_h2_*.md`.

## 3. Criterios de aceptación de H2.8 y de la fase

| Criterio (plan) | Estado | Evidencia |
| --- | --- | --- |
| Salida completa de pytest adjunta | Cumplido: 600 pasan en Windows sobre `0a32344` | `docs/gestion/evidencia_fase_2/pytest_windows.txt` |
| Instalación verificada desde el README en un entorno limpio | Cumplido. Linux (Python 3.12, clon nuevo): 600 pasan. Windows (Python 3.13.0, clon nuevo desde GitHub): 600 pasan | `docs/gestion/evidencia_fase_2/` |
| Lista de limitaciones conocidas | Cumplido | Sección 6 |
| Criterios de aceptación de CU-03, CU-04 y CU-05 sobre datos sintéticos | Cumplido en Linux y Windows | `tests/acceptance/test_casos_de_uso_sinteticos.py` |
| Suite completa sin red | Cumplido: Linux, 600 pasan en un clon nuevo; Windows, 600 pasan | `scripts/verificar.py` |
| PI-11 sobre las partes deterministas | Cumplido en Linux y Windows | Prueba de aceptación de PI-11 |

## 4. Desviaciones respecto del plan

| Qué preveía | Qué se hizo | Quién lo decidió |
| --- | --- | --- |
| Empezar la Fase 2 con la Fase 1 aprobada formalmente (principio 15 del contexto maestro) | La Fase 2 avanzó con la conformidad del equipo con la especificación; la aprobación formal espera la conformidad de la asesoría y la firma del acta | Equipo, 28 y 29 de octubre de 2026 |
| H2.4, H2.5 y H2.6 después de la conformidad de la asesoría con REC-01 a REC-03 | Construidos con la aceptación del equipo. Si la asesoría pide cambios, esos hitos se ajustan | Equipo, 29 de octubre y 4 de noviembre de 2026 |
| Sin interfaz en la Fase 2 | Visor de demostración local de solo lectura (H2.D) | Equipo, a pedido del profesor |
| Orden H2.0 a H2.8 | H2.7 antes de H2.4 | Equipo |
| PI-11 con métricas | Solo la parte determinista | Técnico (D-124) |

## 5. Decisiones metodológicas

`suficiencia decisiones` muestra el estado según el registro de cada equipo.

- **Decididas por el equipo:** DP-16 (SQLite) y el subcódigo DP-08h (se permite un piloto), ambas el 29 de octubre de 2026, pendientes de confirmación de Javier. DP-08h además espera la conformidad de la asesoría.
- **Abiertas:** las otras 19, entre ellas las que bloquean el uso de datos reales: DP-01, DP-02, DP-14, DP-15 y DP-18. También siguen abiertas las nueve que deben cerrarse antes de aprobar el protocolo: DP-06, 07, 08, 09, 10, 12, 17, 19 y 20.
- **Recomendaciones:** REC-04 y REC-05 aceptadas por el equipo el 28 de octubre de 2026. REC-01 a REC-03 aceptadas por el equipo el 29 de octubre de 2026, pendientes de la conformidad de la asesoría.

## 6. Limitaciones conocidas

**De alcance**
- No hay modelos, métricas, intervalos, selección de modelo, evaluación final, comparación con R0 ni interpretabilidad.
- No se pueden importar datos reales: el importador exige la marca de origen sintético (DP-02, DP-14). La seudonimización no equivale a anonimización.
- Sin las decisiones abiertas, los comandos solo funcionan con los ejemplos ficticios de `config/ejemplos/`.

**Técnicas**
- El sello protege la prueba dentro del programa. Quien abra `prueba.csv` con otro programa no queda registrado; la huella delata una modificación, no una lectura.
- El registro detecta modificaciones parciales por la cadena de huellas. Quien recalcule toda la cadena podría falsificarla; conviene guardar aparte la última huella (`registro verificar`).
- La regla de suficiencia solo admite la conjunción de condiciones de umbral y de no inferioridad. Los cinco estados por escenario del manuscrito no están implementados hasta que DP-08 los defina.
- Con la clave efímera, los seudónimos cambian en cada ejecución: cada partición vale solo para esa ejecución.
- Los códigos de cohorte deben ordenarse cronológicamente como texto (por ejemplo, `2014-1`).
- Los decimales de los archivos de entrada deben usar punto, y los CSV deben estar en UTF-8.
- La revisión visual del visor se hizo con capturas en Linux.
- El verificador anti-fuga comprueba las ventanas declaradas: no detecta una ventana mal asignada en el diccionario (DP-03).
- Las herramientas remotas no pueden escribir la carpeta `.vscode`: su configuración se instala a mano.

## 7. Qué sigue (propuesta, no aprobada)

La Fase 2 no incluye el entrenamiento. Para una fase posterior se propone, en este orden, primero con datos sintéticos:

1. Folds rolling-origin por cohortes y preprocesamiento dentro de cada partición.
2. Entrenamiento de las cinco familias, búsqueda de hiperparámetros y calibración.
3. Métricas, intervalos bootstrap pareados y diferencias.
4. Selección por escenario, congelamiento y evaluación final con apertura única de la prueba.
5. Comparación con R0 y los controles, anticipación y no inferioridad.
6. SHAP y LIME sobre los modelos congelados.
7. Páginas de resultados en el visor.

La validación del OE3 con estudiantes reales exige además los datos autorizados y el protocolo aprobado por el equipo y la asesoría.

## 8. Aceptación

| Rol | Nombre | Fecha | Conformidad |
| --- | --- | --- | --- |
| Equipo | Javier Barquinero | | Pendiente de confirmación |
| Equipo | Jorge Caso | 11-11-2026 | Aceptación comunicada en nombre del equipo |
| Asesoría | | 11-11-2026 | Conformidad con este informe (comunicada por Jorge) |
