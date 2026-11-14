# Registro del hito F3.2 — los cinco modelos

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 11 y 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F3.1 |
| Base | Plan de la Fase 3 (sección 2, F3.2); especificación Fase 1 v0.6 (M3: RF-M3-01, 04 a 09, 11; PI-06, PI-08, PI-11, PI-12; RT-01, RT-02) |
| Autorización | El equipo aceptó F3.1 y pidió empezar F3.2 el 11 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |
| Riesgo aceptado | Si la asesoría cambia REC-01 a REC-03 o el diseño comparativo, el entrenamiento se ajusta; todo valor está parametrizado |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `1122610`); aceptado por el equipo** el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/experimentos.py` | Familias, búsqueda (DP-07), espacios por familia, desbalance (DP-06), calibración (DP-09) y semilla, como datos obligatorios; combinaciones a evaluar; resultados por fold |
| `config/ejemplos/experimentos_ficticio.yaml` | EJEMPLO FICTICIO ampliado con `busqueda`, `modelos`, `desbalance`, `calibracion` y `semilla` |
| `src/suficiencia/experimentation/modelos.py` | Las cinco familias, búsqueda en la cohorte de calibración, desbalance y calibración dentro de cada fold (D-137 a D-141) |
| `src/suficiencia/experimentation/pipelines.py` | Conversión de tipos que se puede guardar con joblib (D-146) |
| `src/suficiencia/persistence/corridas_archivos.py` | Predicciones, modelos y manifiesto de cada corrida (D-143) |
| `src/suficiencia/persistence/entorno.py` | Versiones de las bibliotecas de modelos en el entorno registrado (D-145) |
| `src/suficiencia/application/servicio_experimentos.py`, `contratos.py`, `composicion.py` | Servicio `entrenar`: corridas exploratorias registradas, fallas que no detienen el lote, reanudación (D-142, D-144, D-147) |
| `src/suficiencia/cli.py` | Comando `suficiencia experimentos entrenar` con `--escenario` y `--familia` |
| Pruebas y documentación | `pruebas_f3_2.md`, `decisiones_f3_2.md`, este registro |

**No se construyó:** métricas, selección del modelo representativo, umbrales ni uso de datos reales.

## 2. Dependencias añadidas

xgboost-cpu 3.2.0 y LightGBM 4.7.0, en `requirements.lock` con hashes (D-136). **Hay que reinstalar el entorno desde el bloqueo.**

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 697 pasan y 1 se omite (sin git) |
| Windows 11, Python 3.13.0 (12 de noviembre de 2026), después de reinstalar desde `requirements.lock` | Cinco `OK`; 6 contratos cumplidos; **698 pasan** (5 min 42 s). `experimentos entrenar` con el escenario T2\|A+F+S+B y las cinco familias: 5 corridas exitosas, 60 combinaciones evaluadas, 29 segundos |

Tiempo medido con datos sintéticos (insumo para DP-07, que pide el tiempo con datos sintéticos antes de fijar el presupuesto): con el historial ampliado de 1200 estudiantes y el ejemplo ficticio (dos combinaciones por familia, seis folds), los 28 escenarios con las cinco familias tardaron 205 segundos en el entorno Linux de desarrollo: 140 corridas exitosas, 1680 combinaciones evaluadas y 153 MB de archivos en `workspace/experimentos/`. Es solo una referencia: depende del equipo y de los espacios declarados.

## 4. Matriz de criterios de aceptación de F3.2

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Fábrica de LR, RF, XGBoost, LightGBM y SVM | Cumplido en Linux y Windows | PI-06 |
| 2 | Búsqueda con espacio y presupuesto como datos (DP-07) | Cumplido en Linux y Windows | `test_la_busqueda_*`, PI-08 |
| 3 | Desbalance dentro del fold (DP-06) | Cumplido en Linux y Windows | RF-M3-05 |
| 4 | Calibración (DP-09) | Cumplido en Linux y Windows | RF-M3-09 |
| 5 | Semillas | Cumplido en Linux y Windows | PI-11 |
| 6 | Corridas registradas, también las fallidas | Cumplido en Linux y Windows | PI-12 |
| 7 | Verificación en Windows antes del commit | Cumplido | Sección 3 |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. DP-06, DP-07 y DP-09 entran como datos obligatorios; sin `config/experimentos.yaml` el programa se detiene con DP-07.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | 13 de noviembre de 2026 | Confirma la aceptación |
| Jorge | 12 de noviembre de 2026 | Acepta F3.2 y pide empezar F3.3 |
