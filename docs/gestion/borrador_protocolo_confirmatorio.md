# Borrador del protocolo confirmatorio: estructura sin valores

| Campo | Valor |
| --- | --- |
| Fecha | 13 de noviembre de 2026 |
| Para | El equipo y la asesoría |
| Base | Especificación Fase 1 v0.6 (CU-05; secciones 4 y 12); guía de las decisiones pendientes; motor en el commit `9f964c6` |
| Estado | **Estructura vacía.** Ningún campo tiene valor. Cada espacio se llena solo cuando la decisión correspondiente esté aprobada y registrada. No es un protocolo y el programa no puede guardarlo así |

## 1. Para qué sirve

El protocolo confirmatorio fija, antes de abrir la prueba, el criterio de suficiencia y las decisiones de las que depende. Este borrador ordena qué hay que escribir en él, en el formato que el motor lee, y qué falta en el motor para cada opción que se elija.

**Cómo entra en el motor:**

1. Se escribe el YAML del protocolo (sección 7) con los valores aprobados.
2. `suficiencia protocolo borrador ARCHIVO.yaml` lo guarda como borrador en el registro.
3. `suficiencia protocolo aprobar` lo aprueba. Desde entonces no se puede editar: cambiarlo exige una versión nueva y, si ya hubo experimentos confirmatorios, una desviación con su justificación (RF-M4-13).
4. Para aprobar, el protocolo tiene que traer lo decidido en DP-06, DP-07, DP-08, DP-09, DP-10, DP-12, DP-17, DP-19 y DP-20. El programa se niega a aprobar un protocolo marcado como ficticio.

## 2. Lo que el protocolo cita y se decide antes

Estas decisiones no se escriben en el protocolo, pero el protocolo depende de ellas. Deben estar registradas antes.

| Decisión | Dónde queda | Estado |
| --- | --- | --- |
| DP-01 (definición de deserción, 13 subcódigos) y DP-18 (no etiquetables) | `config/objetivo/definicion.yaml` | Abiertas |
| DP-01d (fecha índice de cada ventana) | `config/escenarios.yaml` (hoy en `null`) | Abierta |
| DP-02, DP-14 y DP-15 (autorización, protección y formato de los datos) | Fuera del motor; el importador sigue exigiendo datos sintéticos | Abiertas |
| DP-03 (bloque y ventana mínima de cada variable) | Diccionario del proyecto y `matrices.agregacion` | Abierta |
| DP-04 (diseño principal) y DP-05 con DP-08h (partición y piloto) | `config/poblaciones.yaml` | DP-08h decidida por el equipo; las demás, abiertas |

## 3. Criterio de suficiencia (DP-08)

Es la única parte que el motor ejecuta. Cada campo corresponde a un subcódigo.

| Campo | Subcódigo | Qué se escribe | Valores que el motor admite hoy |
| --- | --- | --- | --- |
| `metricas` | DP-08a | Métrica primaria y secundarias, cada una con su sentido | `auc_roc`, `brier`, `brier_escalado`, `recall_q`; sentido `mayor_es_mejor` o `menor_es_mejor` |
| `condiciones[].tipo` | DP-08b | Estructura de la regla | `umbral` o `no_inferioridad` |
| `condiciones[].limite` e `inclusivo` | DP-08c | Valor del umbral o del margen, y si igualarlo cuenta como cumplir; con su justificación bibliográfica o institucional | Un número finito; el margen no puede ser negativo |
| `condiciones[].comparador` | DP-08d | Grupo de escenarios de referencia de cada condición de no inferioridad | Un nombre de grupo |
| `condiciones[].estadistico` | DP-08e | Qué valor de la estimación se compara | `puntual`, `limite_inferior` o `limite_superior` |
| `multiplicidad` | DP-08f | Procedimiento de multiplicidad y familia confirmatoria | **Ninguno implementado** (sección 6) |
| `desempate` | DP-08g | Orden de las claves de desempate entre escenarios suficientes | `ventana_mas_temprana`, `menos_bloques`, `mejor_metrica:<métrica>`, `orden_de_conjuntos:<lista>` |

El nivel y el método de los intervalos (DP-08e) y la capacidad de alerta q (DP-08i) van en `intervalos` y `metricas.q` de `config/experimentos.yaml`.

## 4. Decisiones que el protocolo registra como texto

El motor las lee de `config/experimentos.yaml` y `config/poblaciones.yaml`. El protocolo guarda lo decidido para que quede fijado con su huella. El texto del protocolo y los archivos de configuración tienen que decir lo mismo.

| Decisión | Qué se escribe | Campo de la configuración |
| --- | --- | --- |
| DP-06 | Tratamiento del desbalance y regla del umbral | `desbalance`; `umbral.regla` |
| DP-07 | Validación interna, búsqueda y presupuesto | `validacion`; `busqueda`; `modelos` |
| DP-09 | Uso de Brier y calibración, y su método | `calibracion`; métricas de DP-08a |
| DP-10 | Selección del modelo representativo: métrica, margen, desempate y reentrenamiento | `seleccion` |
| DP-12 | Tratamiento de faltantes | `preprocesamiento.perfiles` |
| DP-17 | Análisis complementarios de población | `analisis_complementarios` |
| DP-19 | Referencia R0 y controles (DP-19a a DP-19e) | `referencia` (incluye `r_max`) |
| DP-20 | Protocolo comparativo (DP-20a a DP-20g) | `comparacion` (incluye `estabilidad`) |

DP-11 (interpretabilidad) y DP-13 (equidad) no son obligatorias para aprobar, pero conviene fijarlas en el mismo protocolo si se van a reportar.

## 5. Lista de control antes de aprobar

- [ ] DP-01, DP-01d, DP-03, DP-04, DP-05 y DP-18 registradas, y sus archivos de configuración llenos.
- [ ] Datos autorizados (DP-02, DP-14, DP-15) y la prueba sellada con la partición aprobada.
- [ ] DP-08 completa (DP-08a a DP-08i), sin ningún valor elegido después de ver resultados de desarrollo.
- [ ] DP-06, DP-07, DP-09, DP-10, DP-12, DP-17, DP-19 y DP-20 registradas, y el texto del protocolo coincide con `config/experimentos.yaml` y `config/poblaciones.yaml`.
- [ ] Lo que falta en el motor para las opciones elegidas (sección 6) ya está construido y verificado en Linux y Windows.
- [ ] `ficticio: false`.

## 6. Lo que falta en el motor según lo que se decida

Con los ejemplos ficticios, el motor recorre el método completo. Algunas opciones de la especificación y del manuscrito todavía no tienen código. Se construirían cuando el equipo y la asesoría las elijan:

| Si se decide… | Qué falta construir | Requisitos |
| --- | --- | --- |
| Un procedimiento de multiplicidad (DP-08f) | El procedimiento en el motor. Hoy no hay ninguno: el de la demostración es ficticio y no se puede aprobar | RF-M4-04 a RF-M4-06 |
| Condiciones de no inferioridad entre escenarios (DP-08b y DP-08d), como en la propuesta del manuscrito | El cálculo de las diferencias pareadas de cada escenario frente a su grupo de comparadores en la evaluación final. Hoy el motor no las calcula, y esas condiciones quedarían como no evaluables | RF-M4-04 |
| Una compuerta de calibración por intercepto y pendiente (DP-09), como en la propuesta del manuscrito | Esas métricas y la curva de calibración | RF-M4-02 |
| D2 o D3 como análisis complementarios (DP-17) o la cobertura temprana (DP-20f) | La población común y la cobertura temprana dentro de la comparación | RF-M2-10, RF-M2-11 |
| Métricas por subgrupo (DP-13) | Las métricas por subgrupo, con atributos autorizados | RF-M4-11 |
| Búsqueda bayesiana (DP-07) | El método de búsqueda | RF-M3-04 |
| Varias tablas de entrada (DP-15) | La integración de tablas | RF-M1-09 |

## 7. Plantilla del YAML del protocolo

Todos los valores están en `null`: con este archivo, el motor se detiene y nombra la decisión pendiente. La plantilla vive en este documento y no en `config/`, porque el repositorio no debe tener ningún protocolo que no sea un ejemplo ficticio (criterio de H2.6).

```yaml
# PROTOCOLO CONFIRMATORIO DEL PROYECTO. Llenar solo con decisiones aprobadas y
# registradas. Ningún valor puede elegirse después de ver resultados de desarrollo.
ficticio: false

criterio_suficiencia:
  metricas:                 # DP-08a: [{nombre: ..., sentido: ...}, ...]
  condiciones:              # DP-08b, c, d y e: [{tipo, metrica, estadistico, limite, inclusivo, comparador}, ...]
  multiplicidad:            # DP-08f: nombre de un procedimiento implementado
  desempate:                # DP-08g: lista ordenada de claves

decisiones:                 # Texto de lo decidido, con fecha y responsable
  DP-06:
  DP-07:
  DP-08:
  DP-09:
  DP-10:
  DP-12:
  DP-17:
  DP-19:
  DP-20:
```

## 8. Advertencias

- Este borrador no propone valores. Los de `config/ejemplos/` son inventados y no deben copiarse al protocolo.
- Ninguna decisión debe cerrarse para facilitar la programación.
- Aprobar el protocolo no autoriza el uso de datos reales: eso depende de DP-02 y DP-14 y de la autorización institucional, que hoy no existe.
