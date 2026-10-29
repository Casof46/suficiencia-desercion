# Registro del hito H2.3 — datos sintéticos, diccionario, importación, auditoría y seudonimización

| Campo | Valor |
| --- | --- |
| Fecha de ejecución | 28 de octubre de 2026 |
| Solicitado por | Jorge, en nombre del equipo |
| Base | Especificación Fase 1 v0.5 (M1; RF-M1-01 a 05, 07 y 08; PU-08 y PU-14 a 17); plan de la Fase 2 (paquete de cierre, sección E) |
| Autorización | H2.1 a H2.3 autorizados el 28 de octubre de 2026 (acta, apartado 5.1), pendiente de confirmación de Javier |
| Estado del hito | **Ejecutado y verificado en Linux y Windows; versionado en git y en GitHub (commit `d8d8319`); aceptado por el equipo** el 29 de octubre de 2026 (comunicado por Jorge; pendiente de confirmación de Javier) |

## 1. Qué se construyó

| Archivo | Contenido |
| --- | --- |
| `src/suficiencia/domain/datos/diccionario.py` | Tipos, roles, obligatoriedad y dominio de cada columna; reglas de PU-16; rasgos para los escenarios |
| `src/suficiencia/domain/datos/auditoria.py` | Conversión de tipos según el diccionario y auditoría: vacíos, tipos, dominio, clave repetida, copias exactas, errores críticos y alertas, sin la distribución del objetivo; `exigir_apto` (PU-17) |
| `src/suficiencia/domain/puertos.py` | Puerto nuevo `Seudonimizador` |
| `src/suficiencia/persistence/lectores.py` | Lectura de CSV y Excel como texto, con huella del archivo; escritura del dataset procesado con huella |
| `src/suficiencia/persistence/seudonimizacion.py` | Seudonimizador provisional HMAC-SHA256 (DP-14), sin tabla de correspondencia |
| `src/suficiencia/persistence/diccionario_yaml.py` | Lectura del diccionario YAML y fuente de variables para los escenarios |
| `src/suficiencia/application/servicio_datos.py` | `validar_diccionario` e `importar_dataset`, que rechaza todo lo que no sea sintético (DP-02) |
| `src/suficiencia/cli.py` | Comandos `datos diccionario`, `datos importar` y la opción `escenarios --diccionario` |
| `tests/fixtures/generador_sintetico.py` | Generador de historiales **sintéticos** con casos especiales y siembra de problemas |
| `scripts/generar_sintetico.py` | Genera archivos sintéticos CSV o Excel dentro de `data/` |
| `config/ejemplos/diccionario_sintetico.yaml` | Diccionario **ficticio** para el generador |
| Pruebas y documentación | `pruebas_h2_3.md`, `decisiones_h2_3.md`, este registro |

**No se construyó:** importación de datos reales, método definitivo de protección, integración de varias tablas ni el objetivo. No se usó ningún dato real.

## 2. Dependencias añadidas

| Paquete | Tipo | Motivo |
| --- | --- | --- |
| pandas, NumPy | Ejecución | Tablas de datos (sección 5.1; D-41) |
| openpyxl | Ejecución | Archivos .xlsx (RF-M1-01) |
| pandas-stubs | Desarrollo | Tipos de pandas para mypy |
| python-dateutil, tzdata, six, et-xmlfile | Indirectas | Requeridas por pandas y openpyxl |

## 3. Resultados

| Entorno | Resultado |
| --- | --- |
| Linux, Python 3.11.17, 3.12.3 y 3.13.16, instalación limpia desde el bloqueo | Cinco `OK`; 6 contratos cumplidos; 280 pasan y 1 se omite (sin git) |
| Linux, Python 3.12.3, con `git init` y `git add -A` | 281 pasan |
| Descarga para Windows de 64 bits con Python 3.13 | Las ruedas de pandas, NumPy, openpyxl y sus dependencias existen y sus hashes coinciden con el bloqueo |
| Windows, Python 3.13.0, PC de Jorge (29 de octubre de 2026), entorno de H2.2 actualizado | Instalación de pandas, NumPy, openpyxl y sus dependencias desde el bloqueo; cinco `OK`; 6 contratos cumplidos; **281 pasan, 0 omitidas**. Prueba manual: se generaron un Excel sintético (300 estudiantes, 1767 filas) y un CSV con problemas sembrados; el diccionario se validó; el Excel se importó como APTO, con la distribución del objetivo omitida y el dataset guardado en `data/interim/`; el CSV resultó NO APTO con exactamente los 4 errores críticos sembrados (filas 2, 3 y 4 y la clave repetida) |

## 4. Matriz de criterios de aceptación de H2.3

| # | Criterio | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Ninguna columna con rol identificador sale de la seudonimización | Cumplido | PU-08; la auditoría marca como crítico un identificador presente; control negativo |
| 2 | Todo dataset generado declara su origen sintético | Cumplido | Marca en cada fila; rechazo por DP-02; rótulos en la salida |
| 3 | Códigos con ceros a la izquierda | Cumplido | PU-14 con CSV y Excel |
| 4 | Duplicados y valores fuera de dominio detectados | Cumplido | PU-14 y PU-15 |
| 5 | La auditoría no expone la distribución de la clase | Cumplido | PU-15 y control negativo |
| 6 | Sin importación real ni método definitivo de protección | Cumplido | D-45 y D-46 |
| 7 | Funciona en el sistema de trabajo | Cumplido | Linux con 3.11, 3.12 y 3.13; Windows con 3.13.0, pruebas y prueba manual |

## 5. Limitaciones

Ver `docs/arquitectura/decisiones_h2_3.md`, "No implementado en H2.3" y "Limitaciones conocidas".
