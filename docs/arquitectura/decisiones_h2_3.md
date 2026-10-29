# Decisiones técnicas del hito H2.3

Son decisiones **técnicas y reversibles** tomadas para construir H2.3 (datos sintéticos, diccionario, importación, auditoría y seudonimización). Ninguna resuelve una decisión metodológica: DP-02 (autorización), DP-03 (bloques y ventanas), DP-14 (protección de datos), DP-15 (formato de entrada) y DP-01 (objetivo) siguen abiertas. Continúan la numeración de `decisiones_h2_2.md`.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-41 | Incorporar pandas, NumPy y openpyxl (ejecución) y pandas-stubs (desarrollo) | Leer CSV con la biblioteca estándar | Están en la sección 5.1 (REC-05 aceptada). pandas es la base de M1 a M3, y openpyxl es necesario para leer y escribir .xlsx (RF-M1-01) | Aplicada |
| D-42 | Todas las celdas se leen como texto y la conversión la hace la auditoría según el diccionario | Dejar que pandas infiera los tipos | La inferencia convierte `00012345` en `12345` y oculta los tipos incorrectos. Leer texto y convertir después permite contar cada problema (PU-14) | Aplicada |
| D-43 | Roles de columna: identificador, rasgo, objetivo, cohorte y fecha (los de la especificación), más `periodo` y `origen` | Solo los cinco roles | `periodo` identifica el ciclo del historial de matrícula (RF-M1-11). `origen` lleva la marca SINTETICO. **Desviación menor**, registrada | Aplicada |
| D-44 | Solo los rasgos tienen bloque y ventana mínima; cualquier otra columna que los declare se rechaza | Permitirlo y filtrarlo después | Impide que el objetivo o un identificador lleguen a un escenario por error (PU-16). El diccionario alimenta los escenarios mediante el puerto `FuenteVariables` (D-35) | Aplicada |
| D-45 | La importación solo acepta archivos con la columna de origen igual a `SINTETICO` en todas las filas. Si no, se detiene con `DecisionPendiente(DP-02)` antes de seudonimizar o auditar | Avisar y continuar | El plan excluye la importación de datos reales. La comprobación lee solo la marca de origen, que no es un dato personal | Aplicada |
| D-46 | Seudonimización provisional con HMAC-SHA256: el mismo identificador da el mismo seudónimo con la misma clave, y no se guarda tabla de correspondencia. La clave viene de la variable de entorno `SUFICIENCIA_CLAVE_SEUDONIMO` o es efímera (aleatoria, para una sola ejecución); sin clave, `DecisionPendiente(DP-14)` | Hash sin clave; tabla de correspondencia | Un hash sin clave puede revertirse probando todos los códigos de 8 dígitos. El método definitivo y la custodia de la clave son DP-14. Seudonimizar no es anonimizar | Provisional (hasta DP-14) |
| D-47 | La seudonimización ocurre antes que la auditoría y la conversión de tipos. La auditoría marca como error crítico cualquier columna identificadora que siga presente | Auditar primero | Invariante de M1: la seudonimización es la primera transformación | Aplicada |
| D-48 | Errores críticos: columna faltante o no declarada, tipo incorrecto, valor fuera de dominio, obligatorio vacío, fila sin seudónimo y clave repetida. Con alguno de ellos el dataset no es apto para M2 y no se guarda | Rechazar en el primer error | Un solo informe muestra todos los problemas (PU-14, PU-15). Una columna no declarada es crítica porque podría contener datos personales | Aplicada |
| D-49 | La auditoría no informa cardinalidad, rangos ni conteos por valor de las columnas del objetivo, y señala los problemas por número de fila, sin mostrar valores | Informe completo | RF-M1-03: antes del sellado no se expone la distribución de la clase. Mostrar los valores podría filtrar datos personales | Aplicada |
| D-50 | El dataset procesado se guarda en CSV, solo dentro de `data/`, sin sobrescribir archivos, y con la huella SHA-256 de su contenido canónico | Parquet (sección 5.1) | Parquet necesita pyarrow, una dependencia grande que hoy no aporta nada. Se incorporará cuando se persistan datasets para la partición (H2.5). **Desviación menor** | Aplicada |
| D-51 | Generador sintético en `tests/fixtures/` (como dice la especificación), con historiales fijos para los cuatro casos especiales. `scripts/generar_sintetico.py` lo usa para generar archivos de prueba dentro de `data/` | Ponerlo en el paquete | Los datos sintéticos son solo para pruebas y nunca forman parte del motor. Los casos fijos garantizan que pausas, reingresos, transferencias y retiros aparezcan siempre | Aplicada |
| D-52 | `config/ejemplos/diccionario_sintetico.yaml` es un diccionario **ficticio**, con bloques y ventanas inventados para el generador | — | El diccionario real depende de DP-03 y DP-15 | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Especificación, sección 7 (Variable) | Roles id, rasgo, objetivo, cohorte y fecha | Además, `periodo` y `origen` | D-43 |
| Especificación, M1 (salidas) | Dataset procesado en Parquet | CSV dentro de `data/` | D-50 |
| Especificación, sección 6 | `domain/datos/` con diccionario, roles, auditoría, objetivo y estados de etiqueta | `diccionario.py` y `auditoria.py`; el objetivo y los estados llegan en H2.4 | Alcance de H2.3 |
| — | — | Módulos nuevos `persistence/diccionario_yaml.py` y `scripts/generar_sintetico.py` | Lectura del diccionario y generación de pruebas |

## No implementado en H2.3

- Importación de datos reales: bloqueada hasta DP-02 y DP-14.
- Método definitivo de protección de datos (DP-14).
- Integración de varias tablas por la clave seudonimizada (RF-M1-09, PI-14): solo se necesita si DP-15 resulta en varias tablas.
- Construcción del objetivo y de los estados de etiqueta (H2.4).
- La exigencia de una auditoría apta antes de generar poblaciones y particiones (PU-17) está implementada como `exigir_apto`; se conectará a CU-04 cuando CU-04 use datasets, en H2.5.

## Limitaciones conocidas

- Los decimales deben usar punto (`60.5`); con coma se marcan como tipo inválido.
- Los CSV deben estar en UTF-8; el separador puede indicarse con `--separador`.
- El Excel se lee desde la primera hoja.
- Con la clave efímera, los seudónimos cambian en cada importación: sirve para probar, no para unir tablas importadas por separado.
