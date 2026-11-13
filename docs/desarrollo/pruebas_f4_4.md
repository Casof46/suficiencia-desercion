# Pruebas del hito F4.4

Con F4.4, el proyecto tiene 439 funciones de prueba que, con sus parámetros, suman 972 casos: 957 hasta F4.2 y 15 nuevos. Las cuatro comprobaciones estáticas y los 6 contratos de import-linter se mantienen.

Todos los datos son sintéticos y todas las configuraciones son ficticias.

## 1. Cómo ejecutarlas

```powershell
.venv\Scripts\python scripts\verificar.py
```

## 2. Pruebas nuevas o modificadas

| Archivo | Qué demuestra | Requisito o prueba de la especificación |
| --- | --- | --- |
| `tests/unit/test_historial.py` (4 funciones) | Cada función del visor nombra decisiones del catálogo, sin repetirse. Una función solo queda disponible con datos del proyecto si todas sus decisiones están registradas; una decisión ausente del registro cuenta como abierta. La comparación de dos registros aplana los campos, marca «—» lo que falta en uno, no compara el entorno y queda en orden. Las tablas del visor marcan "DESACTIVADA" y filtran los campos iguales | RF-UI-04, RF-M6-02 |
| `tests/integration/test_visor.py` (4 funciones y 8 casos nuevos; modificada) | Las páginas "Historial de experimentos" y "Decisiones" se ejecutan con el aviso. Las seis páginas con funciones del motor muestran desactivado el botón de los datos del proyecto, con las decisiones abiertas. Con DP-01 y DP-18 registradas (EJEMPLO FICTICIO en un proyecto temporal), la página del objetivo deja de estar desactivada y las demás siguen desactivadas. La página de decisiones muestra 0 registradas y 20 abiertas. El historial está vacío sin corridas; con dos corridas, las lista con su rótulo y compara sus campos. Las pruebas anteriores buscan los botones por su texto | RF-UI-04, RF-M6-02, RNF-19 |

## 3. Criterios de aceptación de F4.4

| Criterio (plan de la Fase 4) | Cómo se comprueba |
| --- | --- |
| Estado de las decisiones en el visor | `test_la_pagina_de_decisiones_muestra_el_estado_y_las_funciones` |
| Funciones desactivadas cuando dependen de una decisión abierta | `test_rf_ui_04_*`, `test_historial.py` |
| Historial de experimentos en el visor | `test_rf_m6_02_el_historial_lista_y_compara_experimentos` |
| Revisión en Windows | `verificar_f44.cmd` (pruebas de las páginas) |

Resultado esperado de `scripts/verificar.py`: cinco `OK`; 971 casos pasan y 1 se omite (fuera de un repositorio git; en Windows, la prueba del enlace simbólico).

## 4. Controles negativos realizados

| Cambio introducido a propósito | Prueba | Resultado |
| --- | --- | --- |
| Una decisión ausente del registro cuenta como registrada | `test_una_funcion_solo_queda_disponible_*` | Detectado |
| Una función queda disponible con una sola decisión registrada | `test_una_funcion_solo_queda_disponible_*` | Detectado |
| El botón de los datos del proyecto no se desactiva | `test_rf_ui_04_cada_pagina_desactiva_*` | Detectado |
| La comparación ignora un campo que solo tiene uno de los registros | `test_aplanar_y_comparar_registros` | Detectado |
| "Mostrar solo los campos distintos" no filtra | `test_tablas_del_visor` | Detectado |
| El historial pierde el rótulo de origen de los datos | `test_rf_m6_02_el_historial_lista_y_compara_experimentos` | Detectado |

Cada cambio se revirtió después de comprobarlo.
