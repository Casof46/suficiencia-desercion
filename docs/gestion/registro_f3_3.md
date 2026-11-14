# Registro del hito F3.3 — métricas e intervalos

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 12 de noviembre de 2026 |
| Solicitado por | Jorge, en nombre del equipo, al aceptar F3.2 |
| Base | Plan de la Fase 3 (sección 2, F3.3); especificación Fase 1 v0.6 (M4: RF-M4-01, RF-M4-03, RF-M4-18; tabla de métricas; incertidumbre y pruebas; PU-07, PU-20, PU-24) |
| Autorización | El equipo aceptó F3.2 y pidió empezar F3.3 el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |
| Riesgo aceptado | Si la asesoría cambia REC-01 a REC-03 o el diseño comparativo, las métricas se ajustan; todo valor está parametrizado |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `791a532`); aceptado por el equipo** el 12 de noviembre de 2026 (comunicado por Jorge; confirmado por Javier el 13 de noviembre de 2026) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/evaluacion/metricas.py` | Métricas, bootstrap estratificado, diferencia pareada y lectura de DP-08a, DP-08e y DP-08i como datos (D-148 a D-151) |
| `src/suficiencia/domain/experimentos.py`, `config/ejemplos/experimentos_ficticio.yaml` | Secciones obligatorias `metricas` e `intervalos`; el ejemplo sigue rotulado como ficticio |
| `src/suficiencia/persistence/corridas_archivos.py` | Lectura de las predicciones con comprobación de huella |
| `src/suficiencia/application/servicio_experimentos.py`, `contratos.py`, `composicion.py` | Servicio `metricas`, registrado como experimento exploratorio (D-152) |
| `src/suficiencia/cli.py` | Comando `suficiencia experimentos metricas` |
| Pruebas y documentación | `pruebas_f3_3.md`, `decisiones_f3_3.md`, este registro |

**No se construyó:** selección, umbral, comparación con R0 ni uso de datos reales.

## 2. Dependencias añadidas

Ninguna.

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11 (entorno de desarrollo, sin git) | Cinco `OK`; 6 contratos cumplidos; 732 pasan y 1 se omite (sin git) |
| Windows 11, Python 3.13.0 (12 de noviembre de 2026) | Cinco `OK`; 6 contratos cumplidos; **733 pasan** (6 min 36 s). `experimentos entrenar` con T2\|A+F+S+B y las cinco familias, seguido de `experimentos metricas`: ambos terminan correctamente y el cálculo queda registrado |

Con 10 corridas y el ejemplo ficticio (cuatro métricas, 1000 réplicas), el cálculo tardó unos 5 segundos en Linux.

## 4. Matriz de criterios de aceptación de F3.3

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | AUC-ROC, Brier, Recall@q y las secundarias | Cumplido en Linux y Windows | PU-07 |
| 2 | Prevalencia junto a cada métrica | Cumplido en Linux y Windows | Servicio y línea de comandos |
| 3 | Bootstrap pareado | Cumplido en Linux y Windows | PU-20, PU-24 |
| 4 | Diferencias | Cumplido en Linux y Windows | PU-24 |
| 5 | Verificación en Windows antes del commit | Cumplido | Sección 3 |

## 5. Decisiones metodológicas

Ninguna DP-xx se resolvió. DP-08a, DP-08e y DP-08i entran como datos obligatorios.

## 6. Aceptación

| Rol | Fecha | Observaciones |
| --- | --- | --- |
| Javier | 13 de noviembre de 2026 | Confirma la aceptación |
| Jorge | 12 de noviembre de 2026 | Acepta F3.3 y pide empezar F3.4 |
