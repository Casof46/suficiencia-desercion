"""Línea de comandos del motor (RNF-02, PA-02).

Ejecuta los servicios de aplicación sin interfaz gráfica. Solo usa la capa de
aplicación, como exige ``.importlinter``.

Uso, desde la raíz del repositorio y con el entorno del proyecto:

    suficiencia estado
    suficiencia config validar [--archivo RUTA]
    suficiencia escenarios [--configuracion RUTA] [--variables RUTA] [--detalle]
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
    EstadoProyecto,
    ResultadoEscenarios,
    ResultadoValidacionConfiguracion,
    SolicitudCasoDeUso,
    SolicitudGenerarEscenarios,
    SolicitudValidarConfiguracion,
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
        "--detalle", action="store_true", help="Muestra las variables de cada escenario."
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
                configuracion=argumentos.configuracion, variables=argumentos.variables
            )
        )
        _mostrar_escenarios(escenarios, argumentos.detalle, sys.stdout)
        return SALIDA_CORRECTA
    solicitud = SolicitudCasoDeUso(codigo=argumentos.caso)
    servicios.servicio_de(solicitud.codigo).ejecutar(solicitud)


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
