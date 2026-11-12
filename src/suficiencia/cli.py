"""Línea de comandos del motor (RNF-02, PA-02).

Ejecuta los servicios de aplicación sin interfaz gráfica. Solo usa la capa de
aplicación, como exige ``.importlinter``.

Uso, desde la raíz del repositorio y con el entorno del proyecto:

    suficiencia estado
    suficiencia config validar [--archivo RUTA]
    suficiencia escenarios [--configuracion RUTA] [--variables RUTA | --diccionario RUTA]
                           [--detalle]
    suficiencia datos diccionario RUTA
    suficiencia datos importar ARCHIVO --diccionario RUTA [--clave-efimera] [--salida RUTA]
    suficiencia objetivo validar [RUTA]
    suficiencia objetivo construir ARCHIVO --diccionario RUTA [--definicion RUTA]
                                   [--clave-efimera] [--salida RUTA]
    suficiencia objetivo demostracion
    suficiencia poblaciones construir ARCHIVO --diccionario RUTA [--definicion RUTA]
                                      [--configuracion RUTA] [--clave-efimera]
    suficiencia poblaciones leer-prueba CARPETA --motivo TEXTO
    suficiencia experimentos preparar ARCHIVO --diccionario RUTA [--definicion RUTA]
                                      [--poblaciones RUTA] [--escenarios RUTA]
                                      [--experimentos RUTA] [--clave-efimera]
    suficiencia experimentos entrenar ARCHIVO (mismas opciones que preparar)
                                      [--escenario T1|A+F ...] [--familia lr ...]
    suficiencia experimentos metricas [--experimentos RUTA] [--escenario ...] [--familia ...]
    suficiencia entorno
    suficiencia registro decision --codigo DP-xx --decision T --justificacion T --responsable T
    suficiencia registro ver TIPO
    suficiencia registro verificar
    suficiencia registro exportar TIPO --salida RUTA
    suficiencia registro demostracion
    suficiencia decisiones
    suficiencia protocolo borrador ARCHIVO [--version N]
    suficiencia protocolo aprobar VERSION --huella H --responsable T
                                  [--desviacion T --justificacion T]
    suficiencia protocolo ver
    suficiencia protocolo demostracion [--protocolo RUTA]

TIPO es experimentos, decisiones, accesos, protocolos, desviaciones o congelamientos.
    suficiencia ejecutar CU-03

Códigos de salida: 0, correcto; 1, configuración inválida o error del motor;
2, uso incorrecto del comando; 3, caso de uso todavía no implementado.

Los textos de salida se limitan a caracteres representables en la codificación
de la consola de Windows (cp1252) para que puedan redirigirse a un archivo.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn, TextIO

import suficiencia
from suficiencia.application.composicion import Servicios, crear_servicios
from suficiencia.application.contratos import (
    EntornoResumen,
    EstadoProyecto,
    EstimacionResumen,
    RegistroResumen,
    ResultadoConsultaProtocolo,
    ResultadoConsultaRegistro,
    ResultadoDefinicionObjetivo,
    ResultadoDemostracionObjetivo,
    ResultadoDemostracionProtocolo,
    ResultadoDiccionario,
    ResultadoEntrenamiento,
    ResultadoEscenarios,
    ResultadoEstadoDecisiones,
    ResultadoImportacion,
    ResultadoIntegridad,
    ResultadoMetricas,
    ResultadoObjetivo,
    ResultadoPoblaciones,
    ResultadoPreparacionDesarrollo,
    ResultadoValidacionConfiguracion,
    SolicitudAprobarProtocolo,
    SolicitudCasoDeUso,
    SolicitudConstruirObjetivo,
    SolicitudConstruirPoblaciones,
    SolicitudConsultarRegistro,
    SolicitudEntrenar,
    SolicitudExportarRegistro,
    SolicitudGenerarEscenarios,
    SolicitudGuardarBorrador,
    SolicitudImportarDataset,
    SolicitudLeerPrueba,
    SolicitudMetricas,
    SolicitudPrepararDesarrollo,
    SolicitudRegistrarDecision,
    SolicitudValidarConfiguracion,
    SolicitudValidarDiccionario,
    SolicitudValidarObjetivo,
)
from suficiencia.application.errores import CasoDeUsoNoDisponible, ErrorSuficiencia

SALIDA_CORRECTA = 0
SALIDA_ERROR = 1
SALIDA_USO_INCORRECTO = 2
SALIDA_NO_DISPONIBLE = 3


class _Analizador(argparse.ArgumentParser):
    """``ArgumentParser`` con los textos fijos de la ayuda en español."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(add_help=False, **kwargs)
        self._positionals.title = "argumentos"
        self._optionals.title = "opciones"
        self.add_argument("-h", "--help", action="help", help="Muestra esta ayuda y termina.")

    def format_usage(self) -> str:
        return super().format_usage().replace("usage: ", "Uso: ", 1)

    def format_help(self) -> str:
        return super().format_help().replace("usage: ", "Uso: ", 1)

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(SALIDA_USO_INCORRECTO, f"Error: {message}\n")


def _codigo_caso_de_uso(texto: str) -> str:
    codigo = texto.strip().upper()
    if not re.fullmatch(r"CU-\d{2}", codigo):
        raise argparse.ArgumentTypeError(
            f"'{texto}' no es un código de caso de uso; use el formato CU-01."
        )
    return codigo


def _separador(texto: str) -> str:
    if len(texto) != 1:
        raise argparse.ArgumentTypeError("el separador debe ser un solo carácter, por ejemplo ';'.")
    return texto


def _opciones_desarrollo(analizador: argparse.ArgumentParser) -> None:
    """Opciones comunes de `experimentos preparar` y `experimentos entrenar`."""
    analizador.add_argument("archivo", type=Path, help="Archivo .csv o .xlsx.")
    analizador.add_argument(
        "--diccionario", type=Path, required=True, help="Diccionario de datos (YAML)."
    )
    analizador.add_argument(
        "--definicion",
        type=Path,
        help="Definición del objetivo (por omisión, config/objetivo/definicion.yaml; DP-01).",
    )
    analizador.add_argument(
        "--poblaciones",
        type=Path,
        help="Poblaciones y partición (por omisión, config/poblaciones.yaml; DP-04, DP-05).",
    )
    analizador.add_argument(
        "--escenarios",
        type=Path,
        help="Ventanas y conjuntos (por omisión, config/escenarios.yaml; DP-01d).",
    )
    analizador.add_argument(
        "--experimentos",
        type=Path,
        help="Validación, lecturas y preprocesamiento "
        "(por omisión, config/experimentos.yaml; DP-03, DP-07, DP-12).",
    )
    analizador.add_argument(
        "--clave-efimera",
        action="store_true",
        help="Seudonimiza con una clave aleatoria que no se guarda (para datos sintéticos).",
    )
    analizador.add_argument(
        "--separador", type=_separador, default=",", help="Separador del CSV (por omisión, ,)."
    )


def construir_analizador() -> argparse.ArgumentParser:
    analizador = _Analizador(
        prog="suficiencia",
        description=(
            "Motor del método temporal de suficiencia de información. "
            "Ejecuta los servicios sin interfaz gráfica."
        ),
    )
    analizador.add_argument(
        "--version",
        action="version",
        version=f"suficiencia {suficiencia.__version__}",
        help="Muestra la versión y termina.",
    )
    analizador.add_argument(
        "--raiz",
        type=Path,
        default=Path.cwd(),
        help="Carpeta raíz del proyecto (por omisión, la carpeta actual).",
    )
    comandos = analizador.add_subparsers(dest="comando", required=True, title="comandos")
    comandos.add_parser("estado", help="Lista los servicios, sus casos de uso y su disponibilidad.")
    config = comandos.add_parser("config", help="Operaciones sobre la configuración.")
    acciones_config = config.add_subparsers(dest="accion", required=True, title="acciones")
    validar = acciones_config.add_parser("validar", help="Valida config/proyecto.yaml.")
    validar.add_argument("--archivo", type=Path, help="Otro archivo de configuración que validar.")
    escenarios = comandos.add_parser(
        "escenarios",
        help="Genera los 32 escenarios y verifica que no haya fuga temporal (CU-04, H2.2).",
    )
    escenarios.add_argument(
        "--configuracion",
        type=Path,
        help="Archivo de ventanas (por omisión, config/escenarios.yaml).",
    )
    escenarios.add_argument(
        "--variables",
        type=Path,
        help="Archivo de variables (por omisión, config/diccionario/variables.yaml; DP-03).",
    )
    escenarios.add_argument(
        "--diccionario",
        type=Path,
        help="Toma las variables de los rasgos de un diccionario de datos (H2.3).",
    )
    escenarios.add_argument(
        "--detalle", action="store_true", help="Muestra las variables de cada escenario."
    )
    datos = comandos.add_parser(
        "datos", help="Diccionario, importación y auditoría de datos sintéticos (H2.3)."
    )
    acciones_datos = datos.add_subparsers(dest="accion", required=True, title="acciones")
    diccionario = acciones_datos.add_parser(
        "diccionario", help="Valida un diccionario de datos (CU-02)."
    )
    diccionario.add_argument("archivo", type=Path, help="Archivo YAML del diccionario.")
    importar = acciones_datos.add_parser(
        "importar",
        help="Importa, seudonimiza y audita un archivo CSV o Excel sintético (CU-01).",
    )
    importar.add_argument("archivo", type=Path, help="Archivo .csv o .xlsx.")
    importar.add_argument(
        "--diccionario", type=Path, required=True, help="Diccionario de datos (YAML)."
    )
    importar.add_argument(
        "--clave-efimera",
        action="store_true",
        help="Seudonimiza con una clave aleatoria que no se guarda (para datos sintéticos).",
    )
    importar.add_argument(
        "--salida", type=Path, help="Guarda el dataset procesado (CSV) dentro de data/."
    )
    importar.add_argument(
        "--separador",
        type=_separador,
        default=",",
        help="Separador del CSV (por omisión, la coma).",
    )
    objetivo = comandos.add_parser(
        "objetivo", help="Objetivo y estados de etiqueta con datos sintéticos (H2.4)."
    )
    acciones_objetivo = objetivo.add_subparsers(dest="accion", required=True, title="acciones")
    validar_objetivo = acciones_objetivo.add_parser(
        "validar", help="Valida una definición del objetivo (desglose de DP-01)."
    )
    validar_objetivo.add_argument(
        "archivo",
        type=Path,
        nargs="?",
        help="Definición YAML (por omisión, config/objetivo/definicion.yaml; DP-01).",
    )
    construir = acciones_objetivo.add_parser(
        "construir",
        help="Importa y audita un archivo sintético y etiqueta cada estudiante (CU-03).",
    )
    construir.add_argument("archivo", type=Path, help="Archivo .csv o .xlsx.")
    construir.add_argument(
        "--diccionario", type=Path, required=True, help="Diccionario de datos (YAML)."
    )
    construir.add_argument(
        "--definicion",
        type=Path,
        help="Definición del objetivo (por omisión, config/objetivo/definicion.yaml; DP-01).",
    )
    construir.add_argument(
        "--clave-efimera",
        action="store_true",
        help="Seudonimiza con una clave aleatoria que no se guarda (para datos sintéticos).",
    )
    construir.add_argument(
        "--salida", type=Path, help="Guarda los estados de etiqueta (CSV) dentro de data/."
    )
    construir.add_argument(
        "--separador", type=_separador, default=",", help="Separador del CSV (por omisión, ,)."
    )
    acciones_objetivo.add_parser(
        "demostracion",
        help="Muestra cómo se etiquetan historiales ficticios escritos a mano.",
    )
    poblaciones = comandos.add_parser(
        "poblaciones", help="Poblaciones D1 a D3, partición y sello con datos sintéticos (H2.5)."
    )
    acciones_poblaciones = poblaciones.add_subparsers(
        dest="accion", required=True, title="acciones"
    )
    construir_p = acciones_poblaciones.add_parser(
        "construir",
        help="Etiqueta, construye las poblaciones, particiona y sella la prueba (CU-04, CU-11).",
    )
    construir_p.add_argument("archivo", type=Path, help="Archivo .csv o .xlsx.")
    construir_p.add_argument(
        "--diccionario", type=Path, required=True, help="Diccionario de datos (YAML)."
    )
    construir_p.add_argument(
        "--definicion",
        type=Path,
        help="Definición del objetivo (por omisión, config/objetivo/definicion.yaml; DP-01).",
    )
    construir_p.add_argument(
        "--configuracion",
        type=Path,
        help="Poblaciones y partición (por omisión, config/poblaciones.yaml; DP-04, DP-05).",
    )
    construir_p.add_argument(
        "--clave-efimera",
        action="store_true",
        help="Seudonimiza con una clave aleatoria que no se guarda (para datos sintéticos).",
    )
    construir_p.add_argument(
        "--separador", type=_separador, default=",", help="Separador del CSV (por omisión, ,)."
    )
    leer_prueba = acciones_poblaciones.add_parser(
        "leer-prueba",
        help="Intenta leer la prueba sellada: se rechaza y queda registrado (PI-02).",
    )
    leer_prueba.add_argument("particion", type=Path, help="Carpeta de la partición guardada.")
    leer_prueba.add_argument("--motivo", required=True, help="Por qué se intenta leer.")
    experimentos = comandos.add_parser(
        "experimentos", help="Desarrollo con datos sintéticos: matrices, folds (Fase 3)."
    )
    acciones_experimentos = experimentos.add_subparsers(
        dest="accion", required=True, title="acciones"
    )
    preparar_p = acciones_experimentos.add_parser(
        "preparar",
        help="Matrices por escenario, folds cronológicos y preprocesamiento por fold (F3.1).",
    )
    _opciones_desarrollo(preparar_p)
    entrenar_p = acciones_experimentos.add_parser(
        "entrenar",
        help="Entrena las cinco familias en los folds, en modo exploratorio (F3.2).",
    )
    _opciones_desarrollo(entrenar_p)
    entrenar_p.add_argument(
        "--escenario",
        action="append",
        default=[],
        help="Solo ese escenario (por ejemplo, 'T1|A+F'); se puede repetir.",
    )
    entrenar_p.add_argument(
        "--familia",
        action="append",
        default=[],
        choices=["lr", "rf", "xgboost", "lightgbm", "svm"],
        help="Solo esa familia; se puede repetir.",
    )
    metricas_p = acciones_experimentos.add_parser(
        "metricas",
        help="Métricas con prevalencia e intervalos de las corridas registradas (F3.3).",
    )
    metricas_p.add_argument(
        "--experimentos",
        type=Path,
        help="Configuración de experimentos con la que se entrenó "
        "(por omisión, config/experimentos.yaml; DP-08a, DP-08e, DP-08i).",
    )
    metricas_p.add_argument(
        "--escenario", action="append", default=[], help="Solo ese escenario; se puede repetir."
    )
    metricas_p.add_argument(
        "--familia",
        action="append",
        default=[],
        choices=["lr", "rf", "xgboost", "lightgbm", "svm"],
        help="Solo esa familia; se puede repetir.",
    )
    comandos.add_parser("entorno", help="Muestra el entorno que se registra con cada corrida.")
    registro = comandos.add_parser(
        "registro", help="Registro de trazabilidad: decisiones, corridas y accesos (H2.7)."
    )
    acciones_registro = registro.add_subparsers(dest="accion", required=True, title="acciones")
    decision = acciones_registro.add_parser(
        "decision", help="Registra una decisión metodológica DP-xx (RF-M6-05)."
    )
    decision.add_argument("--codigo", required=True, help="Por ejemplo, DP-16.")
    decision.add_argument("--decision", required=True, help="Qué se decidió.")
    decision.add_argument("--justificacion", required=True, help="Por qué.")
    decision.add_argument("--responsable", required=True, help="Quién decide o comunica.")
    decision.add_argument("--observaciones", help="Notas, por ejemplo confirmaciones pendientes.")
    tipos = (
        "experimentos",
        "decisiones",
        "accesos",
        "protocolos",
        "desviaciones",
        "congelamientos",
    )
    ver = acciones_registro.add_parser("ver", help="Muestra los registros de un tipo.")
    ver.add_argument("tipo", choices=tipos)
    acciones_registro.add_parser(
        "verificar", help="Comprueba que ningún registro fue modificado ni borrado."
    )
    exportar = acciones_registro.add_parser(
        "exportar", help="Exporta un tipo de registro a CSV o Excel (RF-M6-03)."
    )
    exportar.add_argument("tipo", choices=tipos)
    exportar.add_argument(
        "--salida", type=Path, required=True, help="Archivo .csv o .xlsx dentro de reports/."
    )
    acciones_registro.add_parser(
        "demostracion",
        help="Registra una corrida simulada exitosa y otra fallida en un registro aparte.",
    )
    comandos.add_parser(
        "decisiones",
        help="Estado de las decisiones DP-01 a DP-20: registradas o abiertas (H2.8).",
    )
    protocolo = comandos.add_parser(
        "protocolo", help="Protocolo confirmatorio: borradores, aprobación y desviaciones (H2.6)."
    )
    acciones_protocolo = protocolo.add_subparsers(dest="accion", required=True, title="acciones")
    borrador = acciones_protocolo.add_parser(
        "borrador", help="Guarda un borrador del protocolo leído de un YAML (CU-05)."
    )
    borrador.add_argument("archivo", type=Path, help="Protocolo en YAML.")
    borrador.add_argument(
        "--version",
        type=int,
        help="Edita esa versión si sigue en borrador; sin ella, crea una versión nueva.",
    )
    aprobar_p = acciones_protocolo.add_parser(
        "aprobar", help="Aprueba una versión en borrador; desde entonces no se puede editar."
    )
    aprobar_p.add_argument("version", type=int, help="Número de versión.")
    aprobar_p.add_argument(
        "--huella", required=True, help="Huella del borrador revisado (`protocolo ver`)."
    )
    aprobar_p.add_argument("--responsable", required=True, help="Quién aprueba.")
    aprobar_p.add_argument(
        "--desviacion", help="Qué cambia respecto de la versión vigente (RF-M4-13)."
    )
    aprobar_p.add_argument("--justificacion", help="Por qué cambia (obligatoria con --desviacion).")
    acciones_protocolo.add_parser("ver", help="Muestra las versiones y las desviaciones.")
    demostracion_p = acciones_protocolo.add_parser(
        "demostracion",
        help="Recorre el ciclo con un protocolo FICTICIO en un registro temporal.",
    )
    demostracion_p.add_argument(
        "--protocolo",
        type=Path,
        default=Path("config/ejemplos/protocolo_ficticio.yaml"),
        help="Protocolo marcado como ficticio (por omisión, el ejemplo del repositorio).",
    )
    ejecutar = comandos.add_parser("ejecutar", help="Ejecuta un caso de uso (CU-01 a CU-12).")
    ejecutar.add_argument("caso", type=_codigo_caso_de_uso, help="Código, por ejemplo CU-03.")
    return analizador


def _mostrar_estado(estado: EstadoProyecto, salida: TextIO) -> None:
    print(f"suficiencia {estado.version_paquete}", file=salida)
    for servicio in estado.servicios:
        print(f"\nServicio {servicio.servicio}: {servicio.descripcion}", file=salida)
        for caso in servicio.casos_de_uso:
            situacion = (
                "disponible" if caso.disponible else f"pendiente; se construye en {caso.hito}"
            )
            print(f"  {caso.codigo}  {caso.nombre}: {situacion}", file=salida)
            if caso.avance:
                print(f"         Ya disponible: {caso.avance}", file=salida)


def _mostrar_validacion(resultado: ResultadoValidacionConfiguracion, salida: TextIO) -> None:
    if not resultado.valida:
        print(f"Configuración NO válida: {resultado.archivo}", file=salida)
        print(resultado.error, file=salida)
        return
    print(f"Configuración válida: {resultado.archivo}", file=salida)
    print(f"  Proyecto: {resultado.nombre_proyecto}", file=salida)
    print(f"  Versión de la especificación: {resultado.version_especificacion}", file=salida)
    semilla = "definida" if resultado.semilla_global_definida else "pendiente (RF-M3-06)"
    tolerancia = "definida" if resultado.tolerancia_metricas_definida else "pendiente (RNF-03)"
    print(f"  Semilla global: {semilla}", file=salida)
    print(f"  Tolerancia de métricas: {tolerancia}", file=salida)


def _mostrar_escenarios(resultado: ResultadoEscenarios, detalle: bool, salida: TextIO) -> None:
    if resultado.ficticio:
        print(
            "EJEMPLO FICTICIO: las fechas índice o las variables no son decisiones ni datos "
            "reales. No usar como resultado.",
            file=salida,
        )
    print("\nVentanas:", file=salida)
    for ventana in resultado.ventanas:
        print(f"  {ventana.codigo}  fecha índice: {ventana.fecha_indice}", file=salida)
    factibles = sum(e.factible for e in resultado.escenarios)
    print(
        f"\nEscenarios: {len(resultado.escenarios)} "
        f"(factibles: {factibles}; no factibles: {len(resultado.escenarios) - factibles}), "
        f"con {resultado.variables_evaluadas} variables evaluadas",
        file=salida,
    )
    for escenario in resultado.escenarios:
        if escenario.factible:
            situacion = f"factible     {len(escenario.variables):>2} variables"
        else:
            situacion = (
                f"NO factible  sin variables en {', '.join(escenario.bloques_sin_variables)}"
            )
        print(f"  {escenario.ventana}  {escenario.conjunto:<9} {situacion}", file=salida)
        if detalle and escenario.variables:
            print(f"        {', '.join(escenario.variables)}", file=salida)
    if resultado.sin_fuga:
        print(
            "\nVerificación anti-fuga: correcta. Ninguna variable aparece en una ventana "
            "anterior a su ventana mínima.",
            file=salida,
        )


def _mostrar_diccionario(resultado: ResultadoDiccionario, salida: TextIO) -> None:
    if resultado.ficticio:
        print("EJEMPLO FICTICIO: no es el diccionario del proyecto (DP-03).", file=salida)
    print(f"Diccionario válido: {resultado.nombre}", file=salida)
    roles = ", ".join(f"{rol}: {n}" for rol, n in sorted(resultado.variables_por_rol.items()))
    print(f"  Variables por rol: {roles}", file=salida)
    print(f"  Clave de cada fila: {', '.join(resultado.clave)}", file=salida)
    print(f"  Rasgos ({len(resultado.rasgos)}), con bloque y ventana mínima:", file=salida)
    for rasgo in resultado.rasgos:
        print(
            f"    {rasgo.bloque}  {rasgo.ventana_minima}  {rasgo.nombre}",
            file=salida,
        )


def _mostrar_importacion(resultado: ResultadoImportacion, salida: TextIO) -> None:
    informe = resultado.informe
    if resultado.sintetico:
        print(
            "DATOS SINTÉTICOS: no provienen de ninguna institución. No usar como resultado.",
            file=salida,
        )
    print(f"\nArchivo: {resultado.archivo}", file=salida)
    print(f"  Huella SHA-256 del archivo: {resultado.huella_fuente}", file=salida)
    print(
        f"  Seudonimizado: {', '.join(resultado.columnas_seudonimizadas) or 'ninguna columna'}"
        " (reemplazado por 'seudonimo'; seudonimizar no es anonimizar)",
        file=salida,
    )
    print(f"  Filas: {informe.n_filas}; columnas: {informe.n_columnas}", file=salida)
    print("\nAuditoría por columna:", file=salida)
    for c in informe.columnas:
        detalle = f"vacíos {c.nulos}, tipo inválido {c.tipo_invalido}, "
        detalle += f"fuera de dominio {c.fuera_de_dominio}"
        if c.cardinalidad is None:
            detalle += "; distribución omitida (columna del objetivo)"
        else:
            detalle += f"; valores distintos {c.cardinalidad}"
        if c.minimo is not None:
            detalle += f"; rango {c.minimo:g} a {c.maximo:g}"
        if c.filas_con_problemas:
            detalle += f"; filas {', '.join(str(f) for f in c.filas_con_problemas)}"
        print(f"  {c.nombre} ({c.rol}, {c.tipo}): {detalle}", file=salida)
    print(
        f"\nFilas que repiten la clave: {informe.duplicados_clave}; "
        f"copias exactas: {informe.filas_duplicadas}",
        file=salida,
    )
    for alerta in informe.alertas:
        print(f"  Alerta: {alerta}", file=salida)
    for error in informe.errores_criticos:
        print(f"  ERROR CRÍTICO: {error}", file=salida)
    if informe.apto_para_m2:
        print(
            f"\nResultado: APTO para M2. Huella del dataset: {resultado.huella_procesado}",
            file=salida,
        )
        if resultado.archivo_salida:
            print(f"Dataset procesado guardado en {resultado.archivo_salida}", file=salida)
    else:
        print(
            "\nResultado: NO APTO. Los errores críticos impiden pasar a M2 (RF-M1-08); "
            "no se guardó ningún dataset.",
            file=salida,
        )


def _mostrar_definicion_objetivo(resultado: ResultadoDefinicionObjetivo, salida: TextIO) -> None:
    if resultado.ficticio:
        print(
            "EJEMPLO FICTICIO: no es la definición de deserción del proyecto (DP-01, DP-18).",
            file=salida,
        )
    print(f"Definición del objetivo válida: {resultado.nombre}", file=salida)
    print(f"  Archivo: {resultado.archivo}", file=salida)
    for parametro in resultado.parametros:
        print(f"  {parametro.decision:<7} {parametro.parametro}: {parametro.valor}", file=salida)
    print("  Catálogo de estados de matrícula:", file=salida)
    for codigo, categoria in resultado.catalogo.items():
        print(f"    {codigo} -> {categoria}", file=salida)
    print(
        "  DP-01d (fecha índice de cada ventana) se declara en config/escenarios.yaml.",
        file=salida,
    )


def _mostrar_objetivo(resultado: ResultadoObjetivo, salida: TextIO) -> None:
    if resultado.sintetico:
        print(
            "DATOS SINTÉTICOS: no provienen de ninguna institución. No usar como resultado.",
            file=salida,
        )
    if resultado.definicion_ficticia:
        print(
            "DEFINICIÓN FICTICIA: no es la definición de deserción del proyecto (DP-01).",
            file=salida,
        )
    print(f"\nArchivo: {resultado.archivo}", file=salida)
    print(f"  Huella SHA-256 del archivo: {resultado.huella_fuente}", file=salida)
    print(f"  Auditoría: APTA. Huella del dataset: {resultado.huella_dataset}", file=salida)
    print(f"  Definición del objetivo: {resultado.definicion}", file=salida)
    print(f"\nUnidades etiquetadas: {resultado.unidades}", file=salida)
    print(f"  Fuera de la población inicial (DP-01c): {resultado.fuera_de_poblacion}", file=salida)
    print(f"  Fuera de las cohortes elegidas (DP-01c): {resultado.fuera_de_cohortes}", file=salida)
    print(
        "  Distribución de los estados de etiqueta: omitida hasta el sellado de la prueba "
        "(RF-M1-03). Los no etiquetables por cohorte y motivo se reportan solo en "
        "desarrollo (RF-M2-09, CP-08).",
        file=salida,
    )
    print(f"  Huella de los estados de etiqueta: {resultado.huella_registros}", file=salida)
    if resultado.archivo_salida:
        print(f"Estados de etiqueta guardados en {resultado.archivo_salida}", file=salida)


def _mostrar_demostracion_objetivo(
    resultado: ResultadoDemostracionObjetivo, salida: TextIO
) -> None:
    print(
        "DEMOSTRACIÓN: historiales FICTICIOS escritos a mano y definición ficticia. "
        "No son datos ni decisiones.",
        file=salida,
    )
    print(
        f"Definición: {resultado.definicion} (horizonte de {resultado.horizonte_periodos} "
        "periodos desde el ingreso)",
        file=salida,
    )
    print(
        "Historial: M matriculado, A no matriculado, P reserva, R retiro total, "
        "T traslado, - sin registro.",
        file=salida,
    )
    letras = {
        "matriculado": "M",
        "no_matriculado": "A",
        "reserva": "P",
        "retiro_total": "R",
        "traslado": "T",
        "-": "-",
    }
    for caso in resultado.casos:
        historial = "".join(letras[codigo] for codigo in caso.historial)
        estado = caso.estado
        if caso.motivo:
            estado += f" ({caso.motivo})"
        if caso.periodo_evento is not None:
            estado += f", evento en el periodo {caso.periodo_evento}"
        print(f"\n  {caso.nombre}", file=salida)
        print(
            f"    {historial:<8}  observable hasta el periodo {caso.periodos_observables}"
            f"  ->  {estado}",
            file=salida,
        )


def _mostrar_poblaciones(resultado: ResultadoPoblaciones, salida: TextIO) -> None:
    if resultado.sintetico:
        print(
            "DATOS SINTÉTICOS: no provienen de ninguna institución. No usar como resultado.",
            file=salida,
        )
    if resultado.definicion_ficticia or resultado.configuracion_ficticia:
        print(
            "CONFIGURACIÓN FICTICIA: el objetivo, las ventanas, los diseños y la partición son "
            "ejemplos, no decisiones (DP-01, DP-04, DP-05, DP-17).",
            file=salida,
        )
    print(f"\nArchivo: {resultado.archivo}", file=salida)
    print(f"  Huella del dataset: {resultado.huella_dataset}", file=salida)
    indices = ", ".join(f"{v}={p}" for v, p in resultado.periodos_indice.items())
    print(f"  Periodos índice (DP-01d): {indices}", file=salida)
    complementarios = ", ".join(resultado.complementarios) or "ninguno"
    print(
        f"  Diseño principal (DP-04): {resultado.diseno_principal}; "
        f"complementarios (DP-17): {complementarios}",
        file=salida,
    )

    print(
        "\nSeguimiento por cohorte, todas las cohortes y sin el resultado (CU-11, parte A):",
        file=salida,
    )
    for s in resultado.seguimiento:
        estado = "completo" if s.completo else "INCOMPLETO"
        print(
            f"  {s.cohorte:<8} {s.particion:<10} {s.unidades:>4} unidades; observable hasta el "
            f"periodo {s.ultimo_periodo_observable} de {s.periodo_necesario} necesarios: {estado}",
            file=salida,
        )

    print("\nPartición cronológica (DP-05):", file=salida)
    print(f"  Desarrollo: {resultado.unidades_desarrollo} unidades", file=salida)
    print(
        f"  Prueba: {resultado.tamano_prueba} unidades. SELLADA: solo se informa el tamaño "
        "(RF-M2-07, RF-M2-09).",
        file=salida,
    )
    print(f"  Piloto (DP-08h): {resultado.unidades_piloto} unidades", file=salida)
    print(f"  Excluidas: {resultado.unidades_excluidas} unidades", file=salida)

    print(
        "\nPoblaciones por ventana, SOLO en desarrollo (CU-11, parte B; RF-M2-12):",
        file=salida,
    )
    print("  Diseño Ventana  Tamaño  Eventos  Prevalencia  Eventos detectables", file=salida)
    for d in resultado.descripciones_desarrollo:
        prevalencia = f"{d.prevalencia:.3f}" if d.prevalencia is not None else "-"
        detectables = str(d.eventos_detectables) if d.eventos_detectables is not None else ""
        print(
            f"  {d.diseno:<6} {d.ventana:<7} {d.tamano:>7} {d.eventos:>8}  {prevalencia:>11}"
            f"  {detectables:>19}",
            file=salida,
        )
    print("  Fuera de D1 por ventana y motivo (desarrollo):", file=salida)
    for ventana, motivos in resultado.exclusiones_desarrollo.items():
        detalle = ", ".join(f"{m}: {n}" for m, n in motivos.items()) or "ninguna"
        print(f"    {ventana}: {detalle}", file=salida)
    print(
        f"  No etiquetables por cohorte de desarrollo (nivel de DP-18: "
        f"{resultado.nivel_sensibilidad:g}; CP-08):",
        file=salida,
    )
    for n in resultado.no_etiquetables_desarrollo:
        por_motivo = ", ".join(f"{m}: {c}" for m, c in n.por_motivo.items()) or "ninguno"
        aviso = "  -> EXIGE ANÁLISIS DE SENSIBILIDAD" if n.requiere_analisis_sensibilidad else ""
        print(
            f"    {n.cohorte}: {n.no_etiquetables} de {n.unidades} ({n.proporcion:.1%}); "
            f"{por_motivo}{aviso}",
            file=salida,
        )
    print(f"\nPartición guardada en {resultado.carpeta_particion}", file=salida)
    for nombre, huella in resultado.huellas.items():
        print(f"  Huella de {nombre}: {huella}", file=salida)
    print(
        "La prueba solo puede leerla la evaluación final (CU-08); cada intento queda en el "
        "registro de accesos.",
        file=salida,
    )


def _mostrar_preparacion(resultado: ResultadoPreparacionDesarrollo, salida: TextIO) -> None:
    if resultado.sintetico:
        print(
            "DATOS SINTÉTICOS: no provienen de ninguna institución. No usar como resultado.",
            file=salida,
        )
    if resultado.configuraciones_ficticias:
        print(
            "CONFIGURACIÓN FICTICIA: la validación, las lecturas, el preprocesamiento, las "
            "ventanas y la partición son ejemplos, no decisiones (DP-03, DP-05, DP-07, DP-12).",
            file=salida,
        )
    print(f"\nArchivo: {resultado.archivo}", file=salida)
    print(f"  Huella del dataset: {resultado.huella_dataset}", file=salida)
    print(
        f"  Diseño principal: {resultado.diseno}. Solo cohortes de desarrollo: "
        f"{', '.join(resultado.cohortes_desarrollo)}. La prueba no se lee.",
        file=salida,
    )
    print(f"\nFolds cronológicos (DP-07): {len(resultado.folds)}", file=salida)
    for f in resultado.folds:
        calibracion = ", ".join(f.calibracion) or "ninguna"
        print(
            f"  Fold {f.numero}: ajuste {', '.join(f.ajuste)} | calibración {calibracion} | "
            f"validación {f.validacion}",
            file=salida,
        )
    print("\nFilas y eventos por ventana y fold (ajuste / calibración / validación):", file=salida)
    for v in resultado.ventanas:
        print(
            f"  {v.ventana} (periodo índice {v.periodo_indice}): {v.filas} filas, "
            f"{v.eventos} eventos",
            file=salida,
        )
        for c in v.folds:
            print(
                f"    Fold {c.numero}: {c.ajuste} ({c.eventos_ajuste}) / "
                f"{c.calibracion} ({c.eventos_calibracion}) / "
                f"{c.validacion} ({c.eventos_validacion})",
                file=salida,
            )
    perfiles = ", ".join(resultado.perfiles)
    print(
        f"\nEscenarios preparados: {len(resultado.escenarios)}; no factibles (no se "
        f"entrenan): {len(resultado.no_factibles)}",
        file=salida,
    )
    print(f"  Columnas tras el preprocesamiento por perfil ({perfiles}):", file=salida)
    for e in resultado.escenarios:
        columnas = "; ".join(
            f"{p} {a}" if a == b else f"{p} {a}-{b}"
            for p, (a, b) in e.columnas_preprocesadas.items()
        )
        print(
            f"  {e.escenario:<12} {e.filas:>5} filas, {len(e.variables)} variables; {columnas}",
            file=salida,
        )
    for codigo in resultado.no_factibles:
        print(f"  {codigo:<12} no factible", file=salida)
    print(
        "\nEl preprocesamiento se ajustó solo con el ajuste de cada fold (PI-01). "
        "Todavía no se entrena ningún modelo (F3.2).",
        file=salida,
    )


def _mostrar_entrenamiento(resultado: ResultadoEntrenamiento, salida: TextIO) -> None:
    if resultado.sintetico:
        print(
            "DATOS SINTÉTICOS: no provienen de ninguna institución. No usar como resultado.",
            file=salida,
        )
    if resultado.configuraciones_ficticias:
        print(
            "CONFIGURACIÓN FICTICIA: modelos, búsqueda, desbalance, calibración y validación son "
            "ejemplos, no decisiones (DP-06, DP-07, DP-09, DP-12).",
            file=salida,
        )
    print(f"\nArchivo: {resultado.archivo}", file=salida)
    print(f"  Huella del dataset: {resultado.huella_dataset}", file=salida)
    print(
        f"  Modo: {resultado.modo.upper()} (no hay protocolo aprobado). "
        f"Semilla: {resultado.semilla}",
        file=salida,
    )
    print("\nCorridas (escenario, familia, estado, combinaciones evaluadas):", file=salida)
    for c in resultado.corridas:
        detalle = {
            "exitosa": f"{c.configuraciones_evaluadas} evaluadas; {c.carpeta}",
            "omitida": f"ya estaba completa ({c.identificador})",
            "fallida": f"FALLIDA: {c.error}",
        }[c.estado]
        print(f"  {c.escenario:<12} {c.familia:<9} {detalle}", file=salida)
    estados = ("exitosa", "omitida", "fallida")
    cuenta = {e: sum(c.estado == e for c in resultado.corridas) for e in estados}
    total = sum(c.configuraciones_evaluadas for c in resultado.corridas)
    print(
        f"\nExitosas: {cuenta['exitosa']}; omitidas: {cuenta['omitida']}; "
        f"fallidas: {cuenta['fallida']}. Configuraciones evaluadas: {total} (RF-M3-11).",
        file=salida,
    )
    print(
        "Todas las corridas quedaron en el registro (`registro ver experimentos`). Las "
        "probabilidades de validación no son una estimación final del desempeño.",
        file=salida,
    )


def _formato_estimacion(e: EstimacionResumen) -> str:
    if e.puntual is None:
        return "no definida"
    if e.limite_inferior is None or e.limite_superior is None:
        return f"{e.puntual:.3f}"
    return f"{e.puntual:.3f} [{e.limite_inferior:.3f}; {e.limite_superior:.3f}]"


def _mostrar_metricas(resultado: ResultadoMetricas, salida: TextIO) -> None:
    print(
        "DATOS SINTÉTICOS: las predicciones vienen de corridas con datos inventados. "
        "No usar como resultado.",
        file=salida,
    )
    if resultado.configuraciones_ficticias:
        print(
            "CONFIGURACIÓN FICTICIA: las métricas, q y el método de intervalo son ejemplos, no "
            "decisiones (DP-08a, DP-08e, DP-08i).",
            file=salida,
        )
    print(f"\nConfiguración: {resultado.configuracion_experimentos}", file=salida)
    q = f"; q = {resultado.q:g}" if resultado.q is not None else ""
    print(
        f"  Intervalos {resultado.metodo} al {resultado.nivel:.0%} con {resultado.replicas} "
        f"réplicas, estratificadas por {resultado.estratificacion}{q} (DP-08e)",
        file=salida,
    )
    print(
        "\nMétricas sobre las probabilidades de validación fuera de fold, con la prevalencia "
        "de la población evaluada (RF-M4-01):",
        file=salida,
    )
    for c in resultado.corridas:
        print(
            f"  {c.escenario:<12} {c.familia:<9} n={c.filas} eventos={c.eventos} "
            f"prevalencia={c.prevalencia:.3f}",
            file=salida,
        )
        for nombre, estimacion in c.metricas.items():
            print(f"      {nombre:<15} {_formato_estimacion(estimacion)}", file=salida)
    print(
        f"\nCálculo registrado como {resultado.identificador_registro} (exploratorio). Son "
        "puntuaciones de validación: el máximo de muchas es optimista y no es una estimación "
        "final del desempeño.",
        file=salida,
    )


def _mostrar_entorno(entorno: EntornoResumen, salida: TextIO) -> None:
    print("Entorno de ejecución (se guarda con cada corrida):", file=salida)
    print(f"  Python: {entorno.python}", file=salida)
    print(f"  Sistema: {entorno.sistema}", file=salida)
    print(
        f"  Huella de requirements.lock: {entorno.huella_bloqueo or 'no encontrado'}", file=salida
    )
    commit = entorno.commit or "sin repositorio git"
    if entorno.cambios_sin_commit:
        commit += " (con cambios sin guardar en git)"
    print(f"  Commit: {commit}", file=salida)
    print(f"  Núcleos: {entorno.nucleos}", file=salida)
    for variable, valor in entorno.hilos.items():
        print(f"  {variable}: {valor}", file=salida)
    paquetes = ", ".join(f"{p} {v}" for p, v in entorno.paquetes.items())
    print(f"  Paquetes: {paquetes}", file=salida)


def _resumen_registro(registro: RegistroResumen) -> str:
    c = registro.contenido
    if registro.tipo == "decisiones":
        texto = f"{c['codigo']}: {c['decision']} (responsable: {c['responsable']})"
        if c.get("observaciones"):
            texto += f". {c['observaciones']}"
        return texto
    if registro.tipo == "experimentos":
        texto = f"{c['identificador']} {c['modo']} {c['estado']}"
        return texto + (f" - {c['error']}" if c.get("error") else "")
    if registro.tipo == "protocolos":
        if c["accion"] == "borrador":
            return f"borrador de la versión {c['version']}, huella {c['huella'][:12]}..."
        return f"aprobación de la versión {c['version']} (responsable: {c['responsable']})"
    if registro.tipo == "desviaciones":
        return (
            f"versión {c['version_anterior']} -> {c['version_nueva']}: {c['descripcion']} "
            f"({len(c['resultados_afectados'])} resultado(s) afectado(s))"
        )
    if registro.tipo == "congelamientos":
        configuracion = c["configuracion"]
        return (
            f"{configuracion['identificador']} ({configuracion['rol']}, "
            f"{configuracion['escenario']}), huella {c['huella'][:12]}..."
        )
    permitido = "permitido" if c["permitido"] else "RECHAZADO"
    return f"{c['operacion']} ({permitido}): {c['motivo']}"


def _mostrar_consulta(resultado: ResultadoConsultaRegistro, salida: TextIO) -> None:
    print(f"Registro: {resultado.archivo}", file=salida)
    print(f"{resultado.tipo.capitalize()}: {len(resultado.registros)}", file=salida)
    for registro in resultado.registros:
        print(
            f"  n.º {registro.numero}  {registro.fecha}  {_resumen_registro(registro)}", file=salida
        )


def _mostrar_integridad(resultado: ResultadoIntegridad, salida: TextIO) -> None:
    print(f"Registro: {resultado.archivo}", file=salida)
    conteos = ", ".join(f"{t}: {n}" for t, n in resultado.registros_por_tipo.items())
    print(f"  Registros: {conteos}", file=salida)
    if resultado.correcto:
        print("Integridad correcta: ningún registro fue modificado ni borrado.", file=salida)
    else:
        for problema in resultado.problemas:
            print(f"  PROBLEMA: {problema}", file=salida)
        print("Integridad ROTA: no use este registro como evidencia.", file=salida)


def _ejecutar(argumentos: argparse.Namespace, servicios: Servicios) -> int:
    if argumentos.comando == "estado":
        _mostrar_estado(servicios.proyecto.estado(), sys.stdout)
        return SALIDA_CORRECTA
    if argumentos.comando == "config":
        resultado = servicios.proyecto.validar_configuracion(
            SolicitudValidarConfiguracion(archivo=argumentos.archivo)
        )
        _mostrar_validacion(resultado, sys.stdout if resultado.valida else sys.stderr)
        return SALIDA_CORRECTA if resultado.valida else SALIDA_ERROR
    if argumentos.comando == "escenarios":
        escenarios = servicios.escenarios.generar_escenarios(
            SolicitudGenerarEscenarios(
                configuracion=argumentos.configuracion,
                variables=argumentos.variables,
                diccionario=argumentos.diccionario,
            )
        )
        _mostrar_escenarios(escenarios, argumentos.detalle, sys.stdout)
        return SALIDA_CORRECTA
    if argumentos.comando == "datos" and argumentos.accion == "diccionario":
        _mostrar_diccionario(
            servicios.datos.validar_diccionario(
                SolicitudValidarDiccionario(archivo=argumentos.archivo)
            ),
            sys.stdout,
        )
        return SALIDA_CORRECTA
    if argumentos.comando == "datos":
        importacion = servicios.datos.importar_dataset(
            SolicitudImportarDataset(
                archivo=argumentos.archivo,
                diccionario=argumentos.diccionario,
                clave_efimera=argumentos.clave_efimera,
                salida=argumentos.salida,
                separador=argumentos.separador,
            )
        )
        _mostrar_importacion(importacion, sys.stdout)
        return SALIDA_CORRECTA if importacion.informe.apto_para_m2 else SALIDA_ERROR
    if argumentos.comando == "objetivo":
        return _ejecutar_objetivo(argumentos, servicios)
    if argumentos.comando == "poblaciones":
        return _ejecutar_poblaciones(argumentos, servicios)
    if argumentos.comando == "experimentos" and argumentos.accion == "metricas":
        _mostrar_metricas(
            servicios.experimentos.metricas(
                SolicitudMetricas(
                    experimentos=argumentos.experimentos,
                    seleccion_escenarios=tuple(argumentos.escenario),
                    seleccion_familias=tuple(argumentos.familia),
                )
            ),
            sys.stdout,
        )
        return SALIDA_CORRECTA
    if argumentos.comando == "experimentos" and argumentos.accion == "entrenar":
        entrenamiento = servicios.experimentos.entrenar(
            SolicitudEntrenar(
                archivo=argumentos.archivo,
                diccionario=argumentos.diccionario,
                definicion=argumentos.definicion,
                poblaciones=argumentos.poblaciones,
                escenarios=argumentos.escenarios,
                experimentos=argumentos.experimentos,
                clave_efimera=argumentos.clave_efimera,
                separador=argumentos.separador,
                seleccion_escenarios=tuple(argumentos.escenario),
                seleccion_familias=tuple(argumentos.familia),
            )
        )
        _mostrar_entrenamiento(entrenamiento, sys.stdout)
        fallidas = any(c.estado == "fallida" for c in entrenamiento.corridas)
        return SALIDA_ERROR if fallidas else SALIDA_CORRECTA
    if argumentos.comando == "experimentos":
        _mostrar_preparacion(
            servicios.experimentos.preparar_desarrollo(
                SolicitudPrepararDesarrollo(
                    archivo=argumentos.archivo,
                    diccionario=argumentos.diccionario,
                    definicion=argumentos.definicion,
                    poblaciones=argumentos.poblaciones,
                    escenarios=argumentos.escenarios,
                    experimentos=argumentos.experimentos,
                    clave_efimera=argumentos.clave_efimera,
                    separador=argumentos.separador,
                )
            ),
            sys.stdout,
        )
        return SALIDA_CORRECTA
    if argumentos.comando == "entorno":
        _mostrar_entorno(servicios.reportes.entorno(), sys.stdout)
        return SALIDA_CORRECTA
    if argumentos.comando == "registro":
        return _ejecutar_registro(argumentos, servicios)
    if argumentos.comando == "protocolo":
        return _ejecutar_protocolo(argumentos, servicios)
    if argumentos.comando == "decisiones":
        _mostrar_decisiones(servicios.reportes.estado_decisiones(), sys.stdout)
        return SALIDA_CORRECTA
    solicitud = SolicitudCasoDeUso(codigo=argumentos.caso)
    servicios.servicio_de(solicitud.codigo).ejecutar(solicitud)


def _ejecutar_objetivo(argumentos: argparse.Namespace, servicios: Servicios) -> int:
    if argumentos.accion == "validar":
        _mostrar_definicion_objetivo(
            servicios.datos.validar_objetivo(SolicitudValidarObjetivo(archivo=argumentos.archivo)),
            sys.stdout,
        )
    elif argumentos.accion == "construir":
        _mostrar_objetivo(
            servicios.datos.construir_objetivo(
                SolicitudConstruirObjetivo(
                    archivo=argumentos.archivo,
                    diccionario=argumentos.diccionario,
                    definicion=argumentos.definicion,
                    clave_efimera=argumentos.clave_efimera,
                    salida=argumentos.salida,
                    separador=argumentos.separador,
                )
            ),
            sys.stdout,
        )
    else:
        _mostrar_demostracion_objetivo(servicios.datos.demostracion_objetivo(), sys.stdout)
    return SALIDA_CORRECTA


def _ejecutar_poblaciones(argumentos: argparse.Namespace, servicios: Servicios) -> int:
    if argumentos.accion == "construir":
        _mostrar_poblaciones(
            servicios.escenarios.construir_poblaciones(
                SolicitudConstruirPoblaciones(
                    archivo=argumentos.archivo,
                    diccionario=argumentos.diccionario,
                    definicion=argumentos.definicion,
                    configuracion=argumentos.configuracion,
                    clave_efimera=argumentos.clave_efimera,
                    separador=argumentos.separador,
                )
            ),
            sys.stdout,
        )
        return SALIDA_CORRECTA
    servicios.escenarios.leer_prueba(
        SolicitudLeerPrueba(particion=argumentos.particion, motivo=argumentos.motivo)
    )
    return SALIDA_CORRECTA


def _ejecutar_registro(argumentos: argparse.Namespace, servicios: Servicios) -> int:
    reportes = servicios.reportes
    if argumentos.accion == "decision":
        registro = reportes.registrar_decision(
            SolicitudRegistrarDecision(
                codigo=argumentos.codigo,
                decision=argumentos.decision,
                justificacion=argumentos.justificacion,
                responsable=argumentos.responsable,
                observaciones=argumentos.observaciones,
            )
        )
        print(f"Decisión registrada: n.º {registro.numero}, {_resumen_registro(registro)}")
        print(f"  Huella: {registro.huella}")
        return SALIDA_CORRECTA
    if argumentos.accion == "ver":
        _mostrar_consulta(
            reportes.consultar(SolicitudConsultarRegistro(tipo=argumentos.tipo)), sys.stdout
        )
        return SALIDA_CORRECTA
    if argumentos.accion == "verificar":
        integridad = reportes.verificar()
        _mostrar_integridad(integridad, sys.stdout)
        return SALIDA_CORRECTA if integridad.correcto else SALIDA_ERROR
    if argumentos.accion == "exportar":
        exportacion = reportes.exportar(
            SolicitudExportarRegistro(tipo=argumentos.tipo, salida=argumentos.salida)
        )
        print(f"Exportado: {exportacion.archivo} ({exportacion.filas} fila(s))")
        print(f"  Huella: {exportacion.huella}")
        return SALIDA_CORRECTA
    demostracion = reportes.demostracion()
    print("DEMOSTRACIÓN: corridas simuladas, sin modelo, en un registro aparte.")
    print(f"Registro: {demostracion.archivo}")
    for registro in demostracion.registros:
        print(f"  n.º {registro.numero}  {_resumen_registro(registro)}")
    return SALIDA_CORRECTA


def _mostrar_decisiones(resultado: ResultadoEstadoDecisiones, salida: TextIO) -> None:
    print(f"Registro: {resultado.archivo_registro}", file=salida)
    print(
        f"Decisiones registradas: {resultado.registradas} de {len(resultado.decisiones)}; "
        f"abiertas: {resultado.abiertas}.",
        file=salida,
    )
    for decision in resultado.decisiones:
        estado = "REGISTRADA" if decision.registrada else "abierta   "
        print(f"\n  {decision.codigo}  {estado}  {decision.nombre}", file=salida)
        print(
            f"      Decide: {decision.decide}. Resolver antes de: {decision.resolver_antes_de}",
            file=salida,
        )
        for registro in decision.registros:
            tipo = (
                "Registro" if registro.codigo == decision.codigo else f"Subcódigo {registro.codigo}"
            )
            texto = (
                f"      {tipo} ({registro.fecha[:10]}, {registro.responsable}): {registro.decision}"
            )
            if registro.observaciones:
                texto += f" [{registro.observaciones}]"
            print(texto, file=salida)
        if decision.ficha:
            print(f"      Ficha: {decision.ficha}", file=salida)
            if not decision.registrada:
                print(
                    "      Hay ficha pero no está en el registro: regístrela con "
                    "`suficiencia registro decision`.",
                    file=salida,
                )
    print(
        "\nUna decisión con subcódigos registrados sigue abierta mientras su código completo "
        "no esté registrado.",
        file=salida,
    )


def _mostrar_protocolo(resultado: ResultadoConsultaProtocolo, salida: TextIO) -> None:
    print(f"Registro: {resultado.archivo_registro}", file=salida)
    if not resultado.versiones:
        print("No hay ninguna versión del protocolo. Ningún criterio está aprobado.", file=salida)
        return
    vigente = resultado.vigente if resultado.vigente is not None else "ninguna"
    print(f"Versión vigente: {vigente}", file=salida)
    for version in resultado.versiones:
        marca = "  [EJEMPLO FICTICIO]" if version.ficticio else ""
        print(f"\n  Versión {version.numero}: {version.estado}{marca}", file=salida)
        print(f"    Huella: {version.huella}", file=salida)
        print(
            f"    Criterio: {version.condiciones} condición(es); multiplicidad: "
            f"{version.multiplicidad}",
            file=salida,
        )
        if version.responsable_aprobacion:
            print(f"    Aprobada por: {version.responsable_aprobacion}", file=salida)
        if version.decisiones_faltantes:
            print(
                "    Decisiones que faltan para aprobar: "
                f"{', '.join(version.decisiones_faltantes)}",
                file=salida,
            )
    if resultado.desviaciones:
        print("\nDesviaciones:", file=salida)
        for desviacion in resultado.desviaciones:
            afectados = ", ".join(desviacion.resultados_afectados) or "ninguno"
            print(
                f"  Versión {desviacion.version_anterior} -> {desviacion.version_nueva}: "
                f"{desviacion.descripcion}",
                file=salida,
            )
            print(f"    Justificación: {desviacion.justificacion}", file=salida)
            print(f"    Resultados afectados: {afectados}", file=salida)


def _mostrar_demostracion_protocolo(
    resultado: ResultadoDemostracionProtocolo, salida: TextIO
) -> None:
    print(
        "DEMOSTRACIÓN: protocolo FICTICIO y resultados fabricados a partir de sus límites, "
        "en un registro temporal que se borra al terminar. No son criterios, métricas "
        "ni decisiones del proyecto.",
        file=salida,
    )
    print(f"Protocolo: {resultado.archivo_protocolo}", file=salida)
    print("\nCiclo del protocolo:", file=salida)
    for numero, paso in enumerate(resultado.pasos, start=1):
        print(f"  {numero}. {paso.titulo}", file=salida)
        print(f"     {paso.resultado}", file=salida)
    print("\nRegla de suficiencia (modo confirmatorio):", file=salida)
    for caso in resultado.casos:
        print(f"\n  {caso.titulo}", file=salida)
        for escenario in caso.escenarios:
            print(f"    {escenario.escenario}: {escenario.estado}", file=salida)
            for condicion in escenario.condiciones:
                marca = {True: "cumple", False: "no cumple", None: "sin dato"}[condicion.cumple]
                print(f"      - {condicion.descripcion} ({marca})", file=salida)
        if caso.escenario:
            print(f"    Resultado: {caso.estado}: {caso.escenario}", file=salida)
        elif caso.empatados:
            print(
                f"    Resultado: {caso.estado}: {', '.join(caso.empatados)}. "
                "El programa no elige: lo decide el protocolo (DP-08g).",
                file=salida,
            )
        else:
            print(f"    Resultado: {caso.estado}", file=salida)


def _ejecutar_protocolo(argumentos: argparse.Namespace, servicios: Servicios) -> int:
    protocolo = servicios.protocolo
    if argumentos.accion == "borrador":
        borrador = protocolo.guardar_borrador(
            SolicitudGuardarBorrador(archivo=argumentos.archivo, version=argumentos.version)
        )
        marca = " [EJEMPLO FICTICIO: no podrá aprobarse]" if borrador.ficticio else ""
        print(f"Borrador guardado: versión {borrador.version}{marca}")
        print(f"  Huella: {borrador.huella}")
        if borrador.decisiones_faltantes:
            print(f"  Faltan para aprobar: {', '.join(borrador.decisiones_faltantes)}")
        return SALIDA_CORRECTA
    if argumentos.accion == "aprobar":
        aprobacion = protocolo.aprobar(
            SolicitudAprobarProtocolo(
                version=argumentos.version,
                huella=argumentos.huella,
                responsable=argumentos.responsable,
                desviacion=argumentos.desviacion,
                justificacion=argumentos.justificacion,
            )
        )
        print(f"Versión {aprobacion.version} aprobada y vigente. Ya no puede modificarse.")
        if aprobacion.version_reemplazada is not None:
            print(f"  Reemplaza a la versión {aprobacion.version_reemplazada}.")
        if aprobacion.desviacion_registrada:
            afectados = ", ".join(aprobacion.resultados_afectados) or "ninguno"
            print(f"  Desviación registrada. Resultados afectados: {afectados}")
        return SALIDA_CORRECTA
    if argumentos.accion == "ver":
        _mostrar_protocolo(protocolo.consultar(), sys.stdout)
        return SALIDA_CORRECTA
    _mostrar_demostracion_protocolo(protocolo.demostracion(argumentos.protocolo), sys.stdout)
    return SALIDA_CORRECTA


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada del comando ``suficiencia``."""
    argumentos = construir_analizador().parse_args(argv)
    try:
        return _ejecutar(argumentos, crear_servicios(argumentos.raiz.resolve()))
    except CasoDeUsoNoDisponible as error:
        print(str(error), file=sys.stderr)
        return SALIDA_NO_DISPONIBLE
    except ErrorSuficiencia as error:
        print(str(error), file=sys.stderr)
        return SALIDA_ERROR


if __name__ == "__main__":
    sys.exit(main())
