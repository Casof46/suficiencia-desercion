# Decisiones técnicas del hito H2.2

Son decisiones **técnicas y reversibles** tomadas para construir H2.2 (ventanas, conjuntos, escenarios y verificador de fuga). Ninguna resuelve una decisión metodológica: DP-01d (fechas índice) y DP-03 (bloque y ventana mínima de cada variable) siguen abiertas. Continúan la numeración de `decisiones_h2_1.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-31 | Bloques, ventanas y conjuntos están en el código; `config/escenarios.yaml` los declara y el programa rechaza cualquier diferencia | Leerlos libremente de la configuración | Son definiciones (DEF) de la especificación (RF-M2-01, RF-M2-02). La configuración los declara (RNF-10), pero no puede cambiarlos sin cambiar la especificación | Aplicada |
| D-32 | La fecha índice se guarda como texto obligatorio, sin valor por defecto. Si falta, la operación se detiene con `DecisionPendiente(DP-01d)` | Tipo fecha; valor por defecto; avisar y seguir | DP-01d todavía no dice si será una fecha del calendario o un momento del ciclo. El verificador solo usa el orden de las ventanas, que es DEF | Aplicada |
| D-33 | `config/escenarios.yaml` deja las cuatro fechas índice en `null`, así que `suficiencia escenarios` se detiene por DP-01d hasta que se apruebe | Poner fechas de ejemplo en la configuración real | Un valor de ejemplo en la configuración real podría tomarse por una decisión | Aplicada |
| D-34 | Ejemplos en `config/ejemplos/`, declarados `ficticio: true`. La salida empieza con "EJEMPLO FICTICIO" | No incluir ejemplos | Permiten probar y mostrar el programa sin decidir nada. El rótulo aplica el principio de RNF-19 a la configuración | Aplicada |
| D-35 | Las variables entran por el puerto `FuenteVariables`. En H2.2 se leen de un YAML simple (nombre, bloque y ventana mínima). Si falta el archivo del proyecto (`config/diccionario/variables.yaml`), la causa es DP-03 | Esperar al diccionario de H2.3 | El escenario solo necesita esos tres datos. En H2.3 el diccionario será otra implementación del mismo puerto, sin cambiar M2 | Aplicada |
| D-36 | La disponibilidad se decide con la ventana mínima de cada variable: entra en Tj si su ventana mínima Tk cumple k ≤ j | Comparar fechas | Es la invariante de M2 en la especificación. Equivale a RF-M2-04 una vez que DP-03 asigne ventanas mínimas coherentes con las fechas índice de DP-01d | Aplicada |
| D-37 | El verificador de fuga es independiente del constructor: revisa cada escenario contra las ventanas mínimas, y una variable desconocida cuenta como fuga | Confiar en el constructor | Defensa en profundidad. Una prueba inserta a mano el canario en un escenario T1 y comprueba que el verificador lo detecta (PU-03) | Aplicada |
| D-38 | Un escenario con un bloque sin variables queda "no factible" y lista los bloques que faltan; no se imputa nada | Excluirlo de la matriz | RF-M2-03 y RM-09: la matriz siempre tiene 32 escenarios y muestra por qué alguno no se puede ejecutar | Aplicada |
| D-39 | Incorporar hypothesis (desarrollo) para PU-02, con un perfil que fija la secuencia de casos (`derandomize`) y no guarda ejemplos | Casos escritos a mano | La especificación pide una prueba basada en propiedades (sección 5.1 y PU-02). La secuencia fija hace que el resultado sea igual en cada equipo | Aplicada |
| D-40 | `CasoDeUso` y la definición de cada caso tienen un campo `avance`, que dice qué parte ya funciona | Marcar CU-04 como disponible | CU-04 también incluye poblaciones y particiones (H2.5). Marcarlo disponible sería falso | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Especificación, sección 6 | `domain/escenarios/` con ventanas, bloques, conjuntos, escenarios, poblaciones y anti-fuga | `modelo.py` y `construccion.py`; las poblaciones llegan en H2.5 | Alcance de H2.2 |
| Especificación, sección 6 | `config/diccionario/` | Todavía no existe; su ausencia es la causa DP-03 que muestra el programa | DP-03 abierta (D-35) |
| — | — | Carpeta nueva `config/ejemplos/` | D-34 |

## Limitaciones conocidas

- Mientras DP-01d y DP-03 sigan abiertas, `suficiencia escenarios` solo funciona con los ejemplos ficticios.
- El verificador comprueba ventanas mínimas declaradas. No puede detectar una variable cuya ventana mínima esté mal asignada en el diccionario: esa responsabilidad es de DP-03 y de la revisión del diccionario (H2.3).
- La factibilidad depende solo de que el bloque tenga alguna variable; no evalúa su calidad ni sus faltantes (DP-12).
