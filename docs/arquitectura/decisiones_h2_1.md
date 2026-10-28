# Decisiones técnicas del hito H2.1

Son decisiones **técnicas y reversibles** tomadas para construir H2.1 (arquitectura y contratos verificables). Ninguna resuelve una decisión metodológica DP ni acepta REC-01 a REC-03. Continúan la numeración de `decisiones_h2_0.md`.

Estados: **Aplicada**, implementada en H2.1 · **Pendiente**, no resuelta.

## Decisiones

| ID | Decisión | Alternativas consideradas | Motivo | Estado |
| --- | --- | --- | --- | --- |
| D-20 | Incorporar pydantic 2 para los contratos, con el complemento de mypy `pydantic.mypy` | dataclasses de la biblioteca estándar; attrs | La sección 5.1 lo prevé para los contratos de aplicación, y REC-05 está aceptada. Valida entradas y es el formato de una API futura (RNF-14). Entra al bloqueo con tres dependencias indirectas: `pydantic-core`, `annotated-types` y `typing-inspection` | Aplicada |
| D-21 | Los contratos de cada caso de uso se definen en el hito que lo implementa. En H2.1 solo existen los contratos generales: caso de uso, estado de servicio, estado del proyecto, solicitud de caso de uso y validación de la configuración | Definir ya las entradas y salidas de los doce casos de uso | Muchas entradas dependen de decisiones abiertas (por ejemplo, CU-03 de DP-01 y CU-05 de DP-08). Fijarlas ahora obligaría a suponer valores o a cambiarlas después | Aplicada |
| D-22 | Servicio adicional `servicio_proyecto.py`: estado del motor y validación de la configuración | Poner esas funciones en otro servicio o en la CLI | No pertenecen a ningún caso de uso. Ponerlas en la CLI violaría RNF-02 (la lógica debe estar en servicios). **Desviación menor** respecto de la sección 6, que lista siete servicios | Aplicada |
| D-23 | `application/composicion.py` es el único lugar que elige qué adaptador implementa cada puerto | Que la CLI construya los servicios | Así la CLI y la futura interfaz solo importan `application`, como exigen sus contratos, y las pruebas sustituyen adaptadores sin archivos | Aplicada |
| D-24 | `domain/puertos.py` define solo `FuenteConfiguracion` y `AlmacenArtefactos` | Definir ya `RepositorioExperimentos`, `EntrenadorModelos` y `Explicador` | Sus firmas dependen de DP-16 (H2.7) y de fases posteriores. `AlmacenArtefactos` solo depende de bytes y huellas, así que su forma ya es estable | Aplicada |
| D-25 | `ConfiguracionProyecto` pasa al dominio (`domain/proyecto.py`); `persistence.configuracion` lo reexporta | Dejarlo en persistencia | Un puerto del dominio no puede devolver un tipo de otra capa. La reexportación mantiene el código y las pruebas de H2.0 sin cambios | Aplicada |
| D-26 | Todo error del motor hereda de `ErrorSuficiencia`, con causa y acción sugerida en español. `ErrorConfiguracion` hereda de `ConfiguracionInvalida` y de `ValueError` | Mensajes libres por error | Cumple RNF-15 de forma comprobable. Heredar de `ValueError` mantiene la compatibilidad con H2.0 | Aplicada |
| D-27 | `DecisionPendiente(DP-xx, qué falta)` es el error de toda operación que necesite el valor de una decisión abierta | Valores por defecto o avisos | Aplica la regla de la Fase 2: cada decisión abierta es un parámetro obligatorio sin valor por defecto | Aplicada |
| D-28 | Línea de comandos con `argparse`, instalada como el comando `suficiencia`. Códigos de salida: 0 correcto, 1 error, 2 uso incorrecto, 3 caso de uso no implementado | Click o Typer | La sección 5.1 pide `argparse`, sin dependencias adicionales. Los códigos distinguen un fallo de un caso todavía no construido | Aplicada |
| D-29 | La salida de la CLI se limita a caracteres de cp1252, y una prueba la ejecuta con esa codificación | Forzar UTF-8 en la consola | En Windows, la salida redirigida a un archivo usa cp1252, y un carácter como "→" haría fallar el comando (lección de D-19) | Aplicada |
| D-30 | `config/proyecto.yaml` declara la especificación 0.5 | Mantener 0.4 | H2.1 se construyó sobre la v0.5. La v0.5 no cambia nada de lo que implementó H2.0 | Aplicada |

## Desviaciones respecto de la documentación de la Fase 1

| Documento | Qué preveía | Qué se hizo | Motivo |
| --- | --- | --- | --- |
| Especificación, sección 6 | Siete servicios de aplicación | Siete más `servicio_proyecto.py`, y además `_base.py`, `errores.py` y `composicion.py` | D-22, D-23 y D-26 |
| Especificación, reglas de diseño (sección 5) | Puertos `RepositorioExperimentos`, `AlmacenArtefactos`, `EntrenadorModelos` y `Explicador` | Solo `AlmacenArtefactos`, más `FuenteConfiguracion` | D-24 |
| Paquete de cierre, plan de H2.1 | Contratos de entrada y salida de los servicios | Solo los contratos generales; los de cada caso de uso, en su hito | D-21 |

## Limitaciones conocidas

- Parte de los mensajes de `argparse` siguen en inglés (por ejemplo, "argument caso:" o "invalid choice"). Los textos propios de la aplicación están en español.
- Ningún caso de uso tiene lógica: `suficiencia ejecutar CU-xx` siempre responde que todavía no está implementado e indica el hito.
- `AlmacenArtefactos` no tiene implementación hasta H2.7.

## Pendientes

| Pendiente | Responsable | Cuándo |
| --- | --- | --- |
| Meta de cobertura (RNF-11) e incorporación de pytest-cov | Equipo | Al aprobar formalmente la Fase 1 |
| Implementar `AlmacenArtefactos` | — | H2.7, cuando se autorice |
