# Decisiones técnicas del hito H2.7

Son decisiones **técnicas y reversibles** tomadas para construir H2.7 (trazabilidad y registro). La decisión metodológica que lo habilitó, DP-16 (SQLite), la tomó el equipo el 29 de octubre de 2026 y está en `docs/decisiones/DP-16.md`. Ninguna otra DP se resuelve aquí. Continúan la numeración de `decisiones_h2_3.md`.

H2.4 a H2.6 no se construyeron: esperan la revisión de la asesoría. Por eso H2.7 se ejecutó antes que ellos, como permite el plan (H2.7 depende de H2.3 y DP-16).

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-53 | Un solo archivo `workspace/registro.sqlite` con tres tablas: experimentos, decisiones y accesos | Un archivo por tipo | Una sola cosa que respaldar y verificar. `workspace/` no se versiona (RNF-07) | Aplicada |
| D-54 | Disparadores de SQLite que rechazan toda modificación o borrado | Confiar en que el programa no edite | Invariante de M6: los registros solo se agregan | Aplicada |
| D-55 | Cada registro guarda una huella SHA-256 encadenada con la del anterior, y `suficiencia registro verificar` la recalcula | Solo disparadores | Los disparadores pueden quitarse con un visor de SQLite. La cadena delata la modificación, el borrado o el recálculo parcial de huellas | Aplicada |
| D-56 | La conexión se abre y se cierra en cada operación | Una conexión abierta durante toda la ejecución | En Windows, un archivo abierto queda bloqueado | Aplicada |
| D-57 | El entorno registra la versión de Python, el sistema, la huella de `requirements.lock`, el commit y si hay cambios sin guardar en git, los núcleos, las variables de hilos y las versiones de los paquetes principales. No registra usuario, nombre del equipo ni rutas | Incluir todo el entorno | RNF-17, sin datos personales del investigador | Aplicada |
| D-58 | `RegistradorCorridas` ejecuta una función de experimento y registra el resultado o el error (tipo y mensaje, sin la traza). Una falla no detiene un lote | Registrar solo las exitosas | RF-M3-11 y PI-12: las fallidas también se registran | Aplicada |
| D-59 | Un experimento confirmatorio sin versión de protocolo se rechaza al registrarlo | Permitirlo | Coherente con CU-06. El protocolo llega en H2.6 | Aplicada |
| D-60 | Filtro de identificadores: si una exportación tiene una columna identificadora (las del diccionario o una lista fija como `dni` o `correo`), se detiene. No elimina columnas en silencio | Quitar las columnas y seguir | RNF-05 y PI-04. Detenerse obliga a corregir el origen | Aplicada |
| D-61 | Las exportaciones van solo a la carpeta de reportes (`reports/`, no versionada), en CSV o Excel, sin sobrescribir y con huella | Cualquier ruta | RNF-07 y RF-M6-03 | Aplicada |
| D-62 | `suficiencia registro demostracion` escribe dos corridas simuladas en un archivo aparte (`registro_demostracion.sqlite`) | Escribirlas en el registro del proyecto | Así las simulaciones nunca se mezclan con experimentos reales | Aplicada |
| D-63 | Las decisiones DP resueltas tienen una ficha versionada en `docs/decisiones/` y pueden registrarse también en el registro local con `suficiencia registro decision` | Solo una de las dos | La ficha viaja con el repositorio; el registro local tiene fecha y huella | Aplicada |
| D-64 | `RepositorioRegistros` reemplaza al `RepositorioExperimentos` de la especificación y cubre también decisiones y accesos | Tres puertos | Las tres listas comparten el mismo mecanismo de solo agregar | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Especificación, sección 5 | Puerto `RepositorioExperimentos` | `RepositorioRegistros` | D-64 |
| Plan de la Fase 2 | Orden H2.4 → H2.7 | H2.7 antes que H2.4 a H2.6 | H2.4 a H2.6 esperan a la asesoría; H2.7 solo dependía de H2.3 y DP-16 |
| — | — | Módulos nuevos `persistence/exportacion.py` y `application/registro_corridas.py` | D-58 y D-61 |

## No implementado en H2.7

- Los reportes de experimento y el reporte comparativo (RF-M6-04, RF-M6-07): necesitan experimentos reales, que llegan en fases posteriores.
- El registro de accesos a la partición de prueba ya existe (`RegistroAcceso`), pero todavía nadie lo escribe: el sello de la prueba llega en H2.5 (PI-02).
- PI-03 se probó con corridas simuladas, sin modelos.

## Limitaciones conocidas

- La cadena de huellas detecta cambios parciales. Quien recalcule **toda** la cadena desde el registro alterado podría falsificarla. Para evitarlo, conviene copiar periódicamente la última huella (la muestra `suficiencia registro ver`) en un lugar externo, por ejemplo en el mensaje de un commit.
- El mensaje de error de una corrida fallida se guarda tal cual. Si una función incluyera un dato personal en su mensaje de error, quedaría registrado. Las funciones del motor no deben hacerlo.
- La fecha de cada registro está en UTC.
