# Registro del hito H2.0 — repositorio y entorno reproducible

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 21 de octubre de 2026 |
| Solicitado por | Javier |
| Base | Especificación Fase 1 v0.4; documento "Fase 1 — Auditoría final y acta de cierre" (sección G) |
| Autorización formal | **No registrada.** El acta de cierre de la Fase 1 está sin firmar; H2.0 se ejecutó con el contrato provisional descrito en su apartado 6 |
| Estado del hito | **Ejecutado técnicamente; pendiente de aceptación por el equipo** |

## 1. Archivos

El repositorio es nuevo: no existía ningún repositorio ni estructura previa en el entorno de trabajo, así que no se modificó ni sobrescribió ningún archivo existente. La especificación v0.4 no se modificó.

| Archivo | Propósito |
| --- | --- |
| `pyproject.toml` | Metadatos, dependencias y configuración de ruff, mypy y pytest |
| `requirements.lock` | Bloqueo universal con versiones exactas y hashes (24 paquetes) |
| `.gitignore` | Exclusión de datos, bases locales, modelos, secretos, entornos y cachés |
| `.importlinter` | Cuatro contratos de dependencias entre capas |
| `.streamlit/config.toml` | Telemetría desactivada (PA-03) |
| `README.md` | Propósito, estado, instalación, verificación y estructura |
| `config/proyecto.yaml` | Configuración no sensible, sin valores pendientes |
| `data/README.md` | Advertencias sobre datos institucionales |
| `src/suficiencia/__init__.py` y las cinco capas `domain`, `application`, `experimentation`, `persistence` y `ui` | Estructura de capas documentada, sin lógica |
| `src/suficiencia/persistence/configuracion.py` | Lector y validador de `config/proyecto.yaml` |
| `tests/conftest.py` | Bloqueo de red durante las pruebas |
| `tests/unit/test_paquete.py`, `test_configuracion.py`, `test_sin_red.py` | Pruebas unitarias |
| `tests/architecture/test_contratos_capas.py`, `test_privacidad_repositorio.py`, `test_alcance_h2_0.py` | Pruebas de arquitectura, privacidad y alcance |
| `scripts/verificar.py` | Todas las comprobaciones con un comando |
| `docs/especificacion/especificacion_fase_1_v0.4.md` | Copia de referencia, revisión 114 |
| `docs/diagramas/*.mmd` (4) | Fuentes Mermaid; validadas con el parser oficial |
| `docs/gestion/acta_cierre_fase_1_propuesta.md` | Propuesta de acta (Parte A) |
| `docs/gestion/registro_h2_0.md` | Este registro |
| `docs/arquitectura/decisiones_h2_0.md` | Decisiones D-01 a D-18, desviaciones y pendientes |
| `docs/arquitectura/estructura_repositorio.md` | Estructura, equivalencias y límites entre capas |
| `docs/desarrollo/entorno_reproducible.md` | Instalación y verificación en Windows, Linux y macOS |
| `docs/desarrollo/pruebas_h2_0.md` | Pruebas, comandos, criterios y resultados reales |

## 2. Dependencias añadidas

| Paquete | Tipo | Motivo |
| --- | --- | --- |
| PyYAML | Ejecución | Leer `config/proyecto.yaml` (RNF-10) |
| pytest | Desarrollo | Ejecutar las pruebas |
| ruff | Desarrollo | Errores, estilo, orden de imports y formato |
| mypy, types-PyYAML | Desarrollo | Tipos (RNF-11) |
| import-linter | Desarrollo | Contratos entre capas (RNF-01, PA-01) |
| hatchling, editables | Desarrollo | Instalar el paquete en modo editable con versiones fijadas |

Las 16 dependencias indirectas restantes están en `requirements.lock`, con el paquete que las requiere. No se añadieron bibliotecas de aprendizaje automático, interfaz, interpretabilidad ni bases de datos.

## 3. Pruebas ejecutadas

Detalle en `docs/desarrollo/pruebas_h2_0.md`, sección 4. Resumen:

- Instalación limpia desde el bloqueo y `scripts/verificar.py` en Linux con Python 3.11.17, 3.12.3 y 3.13.16: las cinco comprobaciones en `OK`; 82 pruebas pasan y 1 se omite (requiere repositorio git).
- Con `git init` y `git add -A`: las 83 pasan, y ningún archivo sensible ficticio queda preparado para versionar.
- Controles negativos: una violación deliberada de capas hace fallar la verificación, y retirar la corrección D-15 hace fallar su prueba de regresión.
- Windows: el 28 de octubre de 2026, en la PC de Jorge con Python 3.13.0, la instalación desde el bloqueo y `scripts/verificar.py` terminaron con las cinco comprobaciones en `OK` (82 pasan, 1 omitida). El primer intento falló porque no se había descomprimido el ZIP y se usó `py -3.12` sin esa versión instalada; con los pasos de la documentación funcionó.
- Esa ejecución mostró el defecto D-19 (tildes mal mostradas por import-linter en Windows). Se corrigió, se añadió una prueba (ahora 84 casos) y se comprobó en Linux; falta repetirlo en Windows.
- **No ejecutado:** instalación y pruebas en macOS.

## 4. Matriz de criterios de aceptación de H2.0

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Estructura creada y documentada | Cumplido | Árbol en `estructura_repositorio.md`; la prueba `test_no_existen_subpaquetes_fuera_de_las_cinco_capas` fija las capas |
| 2 | El entorno puede reconstruirse a partir de las instrucciones | **Cumplido en Linux y en Windows; pendiente repetir en Windows tras D-19** | Linux: copias limpias con 3.11, 3.12 y 3.13. Windows: Python 3.13.0, 28 de octubre de 2026 |
| 3 | Dependencias justificadas y fijadas de forma reproducible | Cumplido | Tabla 2; `requirements.lock` con hashes; pruebas `test_toda_dependencia_directa_esta_fijada_en_el_lock` y `test_el_lock_fija_versiones_exactas_con_hashes`. El nombre y la lista dependen de REC-05 (provisional) |
| 4 | El paquete puede importarse | Cumplido | `tests/unit/test_paquete.py`, en las tres versiones |
| 5 | Pruebas ejecutadas y resultados registrados | Cumplido | `pruebas_h2_0.md`, sección 4 |
| 6 | Restricciones de arquitectura comprobadas por herramientas | Cumplido, con alcance limitado | import-linter con 4 contratos; control negativo de 11 violaciones; límites documentados. Las capas están vacías, así que el cumplimiento real se pondrá a prueba desde H2.1 |
| 7 | Archivos sensibles excluidos del control de versiones | Cumplido | PA-04: 23 rutas sensibles ignoradas y comprobación en un repositorio git real |
| 8 | Otra persona puede reproducir las comprobaciones | **Reproducido; pendiente de confirmación del equipo** | Instalación y comprobaciones en la PC de Jorge, en Windows, siguiendo la documentación con indicaciones por chat |
| 9 | Decisiones pendientes y supuestos identificados | Cumplido | `decisiones_h2_0.md`: decisiones, desviaciones, supuestos y pendientes |
| 10 | Sin funcionalidades de hitos posteriores | Cumplido | Solo existe el lector de configuración; `test_h2_0_no_incorpora_bibliotecas_de_fases_posteriores`; sin CLI, puertos, servicios, Streamlit ni SQLite |

**Conclusión:** 8 criterios cumplidos; el criterio 2 falta repetirlo en Windows tras D-19 y el criterio 8 requiere la confirmación del equipo. El hito no se declara completado hasta que el equipo lo acepte en el apartado 6 del acta.

## 5. Limitaciones y riesgos

- macOS no comprobado. Windows se comprobó una vez con Python 3.13.0.
- La primera instalación necesita acceso a PyPI. Un proxy institucional podría exigir configurar `pip`.
- Las herramientas del bloqueo son versiones recientes (por ejemplo, pytest 9.1, mypy 2.4, ruff 0.17); un cambio de versión puede producir nuevos avisos. Por eso el bloqueo fija versiones exactas.
- Los contratos de capas se cumplen hoy de forma trivial; su eficacia está demostrada solo con el control negativo.
- El nombre del paquete es provisional (REC-05); cambiarlo afecta a varios archivos (D-02).
- No hay historial git (D-18).
