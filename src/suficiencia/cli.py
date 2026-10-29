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
    suficiencia entorno
    suficiencia registro decision --codigo DP-xx --decision T --justificacion T --responsable T
    suficiencia registro ver {experimentos,decisiones,accesos}
    suficiencia registro verificar
    suficiencia registro exportar {experimentos,decisiones,accesos} --salida RUTA
    suficiencia registro demostracion
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
    RegistroResumen,
    ResultadoConsultaRegistro,
    ResultadoDefinicionObjetivo,
    ResultadoDemostracionObjetivo,
    ResultadoDiccionario,
    ResultadoEscenarios,
    ResultadoImportacion,
    ResultadoIntegridad,
    ResultadoObjetivo,
    ResultadoValidacionConfiguracion,
    SolicitudCasoDeUso,
    SolicitudConstruirObjetivo,
    SolicitudConsultarRegistro,
    SolicitudExportarRegistro,
    SolicitudGenerarEscenarios,
    SolicitudImportarDataset,
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
    tipos = ("experimentos", "decisiones", "accesos")
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
    if argumentos.comando == "entorno":
        _mostrar_entorno(servicios.reportes.entorno(), sys.stdout)
        return SALIDA_CORRECTA
    if argumentos.comando == "registro":
        return _ejecutar_registro(argumentos, servicios)
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
