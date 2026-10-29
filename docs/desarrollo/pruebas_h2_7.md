# Pruebas del hito H2.7

Con H2.7, el proyecto tiene 157 funciones de prueba, que con sus parámetros suman 326 casos: 281 hasta H2.3 y 45 nuevos. Aparece la carpeta `tests/integration/` (sección 6 de la especificación). Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

Prueba manual (Windows):

```powershell
.venv\Scripts\suficiencia entorno
.venv\Scripts\suficiencia registro decision --codigo DP-16 --decision "SQLite para el registro de experimentos, decisiones y accesos" --justificacion "Solo agregar, un archivo, sin dependencias nuevas" --responsable "Jorge, en nombre del equipo" --observaciones "Pendiente de confirmacion de Javier"
.venv\Scripts\suficiencia registro ver decisiones
.venv\Scripts\suficiencia registro verificar
.venv\Scripts\suficiencia registro exportar decisiones --salida reports\decisiones.xlsx
.venv\Scripts\suficiencia registro demostracion
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_trazabilidad.py` (11 funciones, 22 casos) | Validación de decisiones, experimentos y accesos; un confirmatorio necesita protocolo y una corrida fallida, su error; JSON canónico; la cadena de huellas detecta contenido modificado y registros faltantes; el filtro reconoce identificadores conocidos y declarados | RF-M6-05, RNF-05 |
| `tests/integration/test_registro_trazabilidad.py` (13 funciones, 14 casos) | El registro agrega en orden y su cadena es válida. **Solo admite agregar**: UPDATE y DELETE se rechazan. Una modificación hecha quitando los disparadores se detecta, incluso si se rehacen las huellas del registro alterado y del siguiente. El archivo no queda bloqueado. El entorno registra Python, la huella del bloqueo, el paralelismo y el commit (con git). **PI-03 y PI-12**: una corrida confirmatoria exitosa y una exploratoria fallida quedan registradas con modo, protocolo, configuración, semillas, entorno, huella de datos, commit y error. El servicio registra, consulta, verifica y exporta en CSV y Excel. **PI-04**: ninguna exportación contiene columnas identificadoras, y solo se exporta dentro de `reports/`. La demostración usa un registro aparte | PI-03, PI-04, PI-12, RF-M6-01, 03, 05 y 06, RNF-17 |
| `tests/architecture/test_linea_de_comandos.py` (+4 funciones, +4 casos) | `entorno`; `registro decision`, `ver`, `verificar` y `exportar`; `verificar` termina con código 1 si se borró un registro; `registro demostracion`. La prueba de cp1252 incluye los comandos nuevos | PA-02 |
| `tests/architecture/test_privacidad_repositorio.py` (+5 casos) | `workspace/registro.sqlite` y las exportaciones de `reports/` quedan fuera de git; la ficha DP-16 y el repositorio SQLite se versionan | PA-04, RNF-07 |
| `tests/architecture/test_alcance_h2_0.py` (modificada) | Solo `persistence/repositorio_sqlite.py` usa sqlite3 (antes, nadie podía usarlo mientras DP-16 estuviera abierta) | DP-16 |

**PI-05** (la suite completa pasa sin red): todas las pruebas se ejecutan con la red bloqueada desde `tests/conftest.py`, incluidas las nuevas.

## 3. Criterios de aceptación de H2.7

| Criterio (plan de la Fase 2) | Cómo se comprueba |
| --- | --- |
| Los registros solo admiten agregar | Disparadores probados con UPDATE y DELETE; cadena de huellas verificada; tres tipos de alteración detectados |
| Ninguna exportación contiene identificadores | PI-04 con CSV y Excel, y con identificadores conocidos y declarados |
| La suite completa pasa sin red | PI-05 |
| PI-03 con un registro simulado y PI-12 con una corrida simulada que falla | `test_pi03_y_pi12_las_corridas_exitosas_y_fallidas_quedan_registradas` |
| No implementar reportes de resultados científicos | No existen; ver `decisiones_h2_7.md` |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 325 casos pasan y 1 se omite fuera de un repositorio git; en un repositorio git pasan los 326.

Resultado obtenido en Windows 11 con Python 3.13.0 (29 de octubre de 2026): cinco `OK` y 326 casos pasan. En la prueba manual también se intentó borrar el registro por fuera del programa:

```powershell
.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('workspace/registro.sqlite'); c.execute('DELETE FROM decisiones')"
```

SQLite lo rechazó con `sqlite3.IntegrityError: El registro solo admite agregar`, y `suficiencia registro verificar` confirmó después que la integridad seguía correcta.

## 4. Controles negativos realizados

| Cambio introducido a propósito | Resultado |
| --- | --- |
| Los disparadores dejan de rechazar UPDATE y DELETE | Fallan los 2 casos de "solo admite agregar" |
| La exportación deja de pasar por el filtro de identificadores | Falla PI-04 |
| La huella deja de incluir la del registro anterior | Falla la prueba de huellas rehechas |

En los tres casos, al restaurar el archivo vuelven a pasar todas las pruebas.
