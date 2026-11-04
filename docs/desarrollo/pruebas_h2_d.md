# Pruebas del hito H2.D — visor de demostración

| Prueba | Archivo | Qué comprueba |
| --- | --- | --- |
| Cada página se ejecuta (6 casos) | `tests/integration/test_visor.py` | Inicio, datos, escenarios, objetivo, poblaciones y registro corren sin excepciones ni errores y muestran el aviso de datos sintéticos y configuraciones ficticias |
| Falta el historial | `test_visor.py` | La página de datos explica cómo generar el Excel sintético |
| Sin distribución de la clase | `test_visor.py` | La auditoría no muestra prevalencia (RF-M1-03) |
| Matriz de escenarios | `test_visor.py` | 4 ventanas × 8 conjuntos y verificación anti-fuga |
| Sello desde el visor | `test_visor.py` | Construir muestra la prueba solo con su tamaño (42); intentar leerla se rechaza y queda registrado como `consulta_desde_el_visor`, no permitido |
| Registro | `test_visor.py` | La página de registro muestra el intento RECHAZADO e integridad correcta |
| Línea de tiempo y redacción | `test_visor.py` | El HTML marca el evento y el horizonte; los resultados se redactan en español |
| Red bloqueada salvo la interfaz local (2 casos nuevos) | `tests/unit/test_sin_red.py` | Una conexión directa a otro equipo se rechaza; la interfaz local 127.0.0.1 funciona, como la usa asyncio en Windows (D-99) |
| Solo localhost | `tests/architecture/test_privacidad_repositorio.py` | `.streamlit/config.toml` fija `server.address = "localhost"` |

Las pruebas trabajan en una copia temporal del proyecto y no escriben en `workspace/` del repositorio. Todas corren sin red (RNF-04).

Resultado esperado: cinco `OK`; **486 pasan** (470 anteriores + 16 nuevas).

Primer intento en Windows: 11 pruebas del visor fallaron porque el bloqueo de red impedía a asyncio crear su par de sockets local. Se corrigió con D-99.
