# Registro del hito H2.1 — arquitectura y contratos verificables

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 28 de octubre de 2026 |
| Solicitado por | Javier |
| Base | Especificación Fase 1 v0.5; plan de la Fase 2 (paquete de cierre, sección E) |
| Autorización | El equipo autorizó H2.1 a H2.3 el 28 de octubre de 2026 (acta, apartado 5.1), con REC-04 y REC-05 aceptadas. La Fase 1 sigue sin aprobación formal (apartado 5.3) |
| Estado del hito | **Ejecutado técnicamente; pendiente de verificación en Windows y de aceptación por el equipo** |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/errores.py` | `ErrorSuficiencia` con causa y acción sugerida; `ConfiguracionInvalida`, `DecisionPendiente`, `CasoDeUsoNoDisponible`, `HuellaInvalida` |
| `src/suficiencia/domain/huella.py` | Huella SHA-256 (RNF-16) |
| `src/suficiencia/domain/proyecto.py` | `ConfiguracionProyecto`, trasladado desde persistencia (D-25) |
| `src/suficiencia/domain/puertos.py` | Puertos `FuenteConfiguracion` y `AlmacenArtefactos` (D-24) |
| `src/suficiencia/application/contratos.py` | Contratos pydantic generales (D-21) |
| `src/suficiencia/application/errores.py` | Errores reexportados para la CLI y la interfaz |
| `src/suficiencia/application/_base.py` | Base de los servicios de casos de uso |
| `src/suficiencia/application/servicio_*.py` | Siete servicios con los 12 casos de uso, sin lógica, y el servicio del proyecto (D-22) |
| `src/suficiencia/application/composicion.py` | Construcción de los servicios con sus adaptadores (D-23) |
| `src/suficiencia/persistence/configuracion.py` | Implementa `FuenteConfiguracion` (`FuenteConfiguracionYaml`) |
| `src/suficiencia/cli.py` | Comando `suficiencia`: `estado`, `config validar`, `ejecutar CU-xx` (D-28, D-29) |
| `.importlinter` | 6 contratos (antes 4): CLI solo usa aplicación; ninguna capa usa la CLI; el dominio no usa pydantic |
| `pyproject.toml`, `requirements.lock` | pydantic y el complemento de mypy; comando `suficiencia` |
| `config/proyecto.yaml` | Especificación 0.5 (D-30) |
| Pruebas | `docs/desarrollo/pruebas_h2_1.md` |
| Documentación | `decisiones_h2_1.md`, `pruebas_h2_1.md`, este registro; actualizados `README.md`, `estructura_repositorio.md` y `entorno_reproducible.md` |

**No se construyó:** ninguna lógica científica, ventanas, escenarios, objetivo, poblaciones, protocolo, modelos, interfaz Streamlit ni almacenamiento. No se usaron datos, ni reales ni sintéticos.

## 2. Dependencias añadidas

| Paquete | Tipo | Motivo |
| --- | --- | --- |
| pydantic | Ejecución | Contratos de los servicios (sección 5.1, RNF-14; D-20) |
| pydantic-core, annotated-types, typing-inspection | Indirectas | Requeridas por pydantic |

## 3. Matriz de criterios de aceptación de H2.1

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | El dominio no importa Streamlit ni scikit-learn | Cumplido | Contrato `dominio-sin-dependencias-externas`, con control negativo |
| 2 | Cada servicio se invoca desde la CLI (PA-02) | Cumplido | `tests/architecture/test_linea_de_comandos.py`: un caso de uso de cada uno de los 7 servicios |
| 3 | Contratos de dependencias verificables (PA-01) | Cumplido | 6 contratos; control negativo con 17 violaciones |
| 4 | Prueba negativa con un import prohibido | Cumplido | Control negativo automático y control manual (`pruebas_h2_1.md`, sección 4) |
| 5 | Sin lógica de aprendizaje automático ni interfaz | Cumplido | Ningún caso de uso disponible; bibliotecas postergadas ausentes |
| 6 | La instalación y las comprobaciones funcionan en el sistema de trabajo | **Cumplido en Linux; pendiente en Windows** | Linux con 3.11, 3.12 y 3.13 |

Estos criterios cierran la comprobación de CA-11 a CA-13 de la especificación en lo que H2.1 alcanza: estructura de capas, contratos y ejecución sin interfaz.

## 4. Limitaciones

- Ver `docs/arquitectura/decisiones_h2_1.md`, "Limitaciones conocidas".
- Actualizar un entorno de H2.0 exige reinstalar desde el bloqueo y volver a instalar el paquete, para registrar el comando `suficiencia` (`entorno_reproducible.md`, sección 2, "Actualizar un entorno existente").
