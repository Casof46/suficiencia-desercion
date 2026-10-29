# Pruebas del hito H2.3

Con H2.3, el proyecto tiene 129 funciones de prueba, que con sus parámetros suman 281 casos: 206 hasta H2.2 y 75 nuevos. Todas usan datos **sintéticos** del generador `tests/fixtures/generador_sintetico.py`, nunca datos reales. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows; en Linux o macOS, `.venv/bin/...` y barras `/`):

```powershell
.venv\Scripts\python scripts\generar_sintetico.py --semilla 1 --salida data\sintetico\historial.xlsx
.venv\Scripts\python scripts\generar_sintetico.py --semilla 1 --salida data\sintetico\historial_errores.csv --con-errores
.venv\Scripts\suficiencia datos diccionario config\ejemplos\diccionario_sintetico.yaml
.venv\Scripts\suficiencia datos importar data\sintetico\historial.xlsx --diccionario config\ejemplos\diccionario_sintetico.yaml --clave-efimera --salida data\interim\historial.csv
.venv\Scripts\suficiencia datos importar data\sintetico\historial_errores.csv --diccionario config\ejemplos\diccionario_sintetico.yaml --clave-efimera
.venv\Scripts\suficiencia escenarios --configuracion config\ejemplos\escenarios_ficticio.yaml --diccionario config\ejemplos\diccionario_sintetico.yaml
```

La primera importación debe terminar en "APTO para M2" y la segunda en "NO APTO", con cuatro errores críticos: un obligatorio vacío, un valor fuera de rango, un tipo inválido y una clave repetida.

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_datos_sinteticos.py` (19 funciones, 26 casos) | El generador es reproducible, marca cada fila como sintética e incluye pausas, reingresos, transferencias, retiros y seguimiento incompleto. CSV y Excel se importan con sus tipos y con los ceros a la izquierda, y el seudónimo se calcula sobre el código con sus ceros. 7 tipos incorrectos o valores fuera de dominio se rechazan con el motivo y la fila. Se rechazan columnas faltantes o no declaradas. La auditoría encuentra los 4 problemas sembrados y no expone la distribución del objetivo. Los errores críticos impiden pasar a M2. La seudonimización elimina los identificadores, repite el seudónimo del mismo valor y no deja ningún código original en la tabla; sin clave, la causa es DP-14. El dataset procesado tiene huella estable y no se sobrescribe | PU-08, PU-14, PU-15, PU-17 |
| `tests/unit/test_diccionario.py` (12 funciones, 33 casos) | Un rasgo sin bloque o sin ventana, un bloque inexistente o una ventana inexistente se rechazan; solo los rasgos llevan bloque y ventana; 8 reglas por variable y 3 del diccionario; 6 errores de YAML con mensaje en español; sin diccionario del proyecto, la causa es DP-03; el diccionario alimenta los escenarios | PU-16 |
| `tests/unit/test_servicios_aplicacion.py` (+5 funciones, +5 casos) | La importación de punta a punta seudonimiza, audita y guarda dentro de `data/`. Un archivo no marcado como sintético se rechaza por DP-02 **antes** de seudonimizar. No se guarda nada fuera de `data/` ni cuando la auditoría falla. Se resume el diccionario. CU-01 y CU-02 muestran su avance | D-45, D-48, D-50 |
| `tests/architecture/test_linea_de_comandos.py` (+4 funciones, +4 casos) | `datos diccionario`; `datos importar` con resultado apto, sin ningún código original en la salida; con errores o sin clave, código de salida 1; `escenarios --diccionario`. La prueba de cp1252 incluye los comandos nuevos | PA-02 |
| `tests/unit/test_script_generar_sintetico.py` (2 funciones) | El script solo escribe dentro de `data/` y exige una semilla | D-51 |
| `tests/architecture/test_privacidad_repositorio.py` (+5 casos) | Los archivos sintéticos de `data/` quedan fuera de git; el diccionario de ejemplo, el generador y el script se versionan | PA-04 |
| `tests/architecture/test_alcance_h2_0.py` (modificada) | pandas, NumPy y openpyxl dejan de estar postergadas | D-41 |

## 3. Criterios de aceptación de H2.3

| Criterio (plan de la Fase 2) | Cómo se comprueba |
| --- | --- |
| Ninguna columna con rol identificador sale de la seudonimización | PU-08 (ningún código original en la tabla); la auditoría marca como crítico un identificador presente; la prueba de la CLI busca los códigos en la salida |
| Todo dataset generado declara su origen sintético | Columna `origen_datos = SINTETICO` en cada fila; el importador rechaza lo que no la tenga (DP-02); las salidas muestran "DATOS SINTÉTICOS" |
| Importación de códigos con ceros a la izquierda | PU-14 con CSV y Excel |
| Detección de duplicados y valores fuera de dominio | PU-14 y PU-15 |
| La auditoría no expone la distribución de la clase | PU-15 |
| No implementar la importación de datos reales ni el método definitivo de protección | D-45 y D-46 |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 280 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 281.

## 4. Controles negativos realizados

| Cambio introducido a propósito | Resultado |
| --- | --- |
| El seudonimizador conserva la columna del código | Fallan 8 pruebas, entre ellas PU-08 y la auditoría ("no se seudonimizó") |
| La auditoría informa la cardinalidad de la columna del objetivo | Fallan PU-15 y la prueba de la CLI |
| El servicio deja de exigir la marca sintética | Falla la prueba de rechazo por DP-02 |

En los tres casos, al restaurar el archivo vuelven a pasar todas las pruebas.

## 5. Lo que estas pruebas no cubren

- Datos reales: no se pueden importar (D-45).
- PI-14 (varias tablas): depende de DP-15.
- El método definitivo de protección (DP-14).
