# Decisiones técnicas del hito H2.8 — CLI mínima y cierre de la Fase 2

Son decisiones **técnicas y reversibles**. Ninguna resuelve una decisión metodológica DP-xx. Continúan la numeración de `decisiones_h2_6.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-121 | Catálogo de las 20 decisiones metodológicas en `config/decisiones_metodologicas.yaml`: código, nombre corto, quién decide y antes de qué debe resolverse, tomados de la sección 12 de la especificación v0.6. No contiene ninguna decisión ni valor | Escribir la lista en el código | El plan pide consultar el estado de las decisiones; la lista es documentación y puede actualizarse sin tocar el código | Aplicada |
| D-122 | Comando `suficiencia decisiones`: cruza el catálogo con el registro de decisiones de H2.7. Una decisión figura como registrada solo si el registro tiene su código exacto; los subcódigos registrados (por ejemplo, DP-08h) se muestran junto a su decisión sin cerrarla. Si existe una ficha en `docs/decisiones/` pero la decisión no está en el registro, lo avisa | Contar un subcódigo como decisión registrada | La especificación dice que DP-08 sigue abierta aunque DP-08h esté decidida. El registro es la fuente de verdad (RF-M6-05) | Aplicada |
| D-123 | Las pruebas de aceptación de CU-03, CU-04 y CU-05 están en `tests/acceptance/` y recorren cada caso de uso por la línea de comandos, con datos sintéticos y configuraciones ficticias en un proyecto temporal | Repetir las pruebas de integración de los servicios | La especificación reserva `tests/acceptance/` para "escenarios por caso de uso". Probar por la línea de comandos es probar lo que usará el equipo | Aplicada |
| D-124 | PI-11 solo en su parte determinista: dos ejecuciones con la misma clave de seudonimización deben producir exactamente los mismos archivos (etiquetas y particiones). La tolerancia de métricas (`tolerancia_metricas`, RNF-03) sigue sin valor | Fijar una tolerancia | Todavía no hay métricas. Para salidas deterministas, la única tolerancia correcta es ninguna diferencia | Aplicada |
| D-125 | La evidencia del cierre (salida completa de pytest en Windows e instalación limpia desde el README) se guarda como texto en `docs/gestion/evidencia_fase_2/` | Adjuntarla solo en el chat | El plan exige "salida completa de pytest adjunta"; en el repositorio queda versionada junto al informe | Aplicada |
| D-126 | La instalación limpia se verifica clonando el repositorio en una carpeta nueva y siguiendo el README tal cual: en Linux con Python 3.12, y en Windows con un clon desde GitHub en `C:\proyectos\suficiencia-desercion-limpia` | Verificar sobre el entorno ya instalado | Un entorno usado esconde dependencias olvidadas; un clon nuevo no | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Plan de la Fase 2, H2.8 | Comandos para validar configuración, escenarios, objetivo, poblaciones y estado del protocolo | Todos ya existían desde H2.1 a H2.6; H2.8 agrega `decisiones` y las pruebas de aceptación | No hacía falta duplicarlos |
| Especificación, PI-11 | Métricas dentro de una tolerancia | Solo la parte determinista | D-124 |

## No implementado en H2.8

- Streamlit más allá del visor de H2.D, entrenamiento de modelos y datos reales (excluidos por el plan).
- La comparación de métricas de PI-11.
