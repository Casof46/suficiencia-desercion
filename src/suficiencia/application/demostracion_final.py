"""Demostración de F3.4 a F3.6: selección, evaluación final, comparación y explicaciones
(EJEMPLO FICTICIO).

Recorre el final del método con datos sintéticos y configuraciones ficticias, en
un **proyecto temporal** que se borra al terminar: nada llega al registro ni a la
carpeta de trabajo del proyecto. Usa los mismos servicios que el proyecto real:

1. Construye las poblaciones, la partición y el sello de la prueba (H2.5).
2. Entrena las cinco familias en los escenarios pedidos y en los que necesitan R0 y
   los controles (F3.2).
3. Selecciona modelo y umbral por escenario solo con desarrollo (DP-10, DP-06),
   construye R0 y los controles con su propia regla (DP-19) y comprueba que el
   registro de accesos no tiene ningún acceso a la prueba (PI-10).
4. Intenta la evaluación final sin protocolo: se rechaza (PU-05).
5. Aprueba el protocolo ficticio en el registro temporal y congela cada
   configuración seleccionada, R0 y los controles con su huella (RF-M4-12, RF-M4-17).
6. Intenta evaluar una configuración modificada: se rechaza (PI-09).
7. Ejecuta la evaluación final: abre la prueba una sola vez para todas las
   configuraciones y aplica la regla en modo confirmatorio (PI-15).
8. Intenta repetirla sin justificación: se rechaza (RF-M4-09).
9. Compara la seleccionada con R0 y los controles con las predicciones guardadas,
   sin volver a abrir la prueba (CU-12; PI-15), y clasifica el resultado (C1 a C8).
10. Explica las configuraciones congeladas con el alcance de DP-11 (CU-09; PI-13),
    solo con filas de desarrollo.
11. Si la configuración lo habilita (DP-20g), describe la estabilidad de la selección por
    fold de desarrollo y las métricas de prueba por cohorte, sin volver a abrir la prueba
    (CMP-5; F4.2).

La clave de seudonimización es aleatoria, vive solo durante la demostración y es la
misma para construir la partición y para evaluarla.

El procedimiento de multiplicidad que se entrega a la regla es el de la
demostración de H2.6 (``_SinAjusteFicticio``): no es una propuesta (DP-08f abierta).
Las métricas son de modelos entrenados con datos inventados: no dicen nada sobre
estudiantes reales ni sobre la eficacia del método.
"""

from __future__ import annotations

import dataclasses
import secrets
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from suficiencia.application.contratos import (
    PasoDemostracion,
    ResultadoDemostracionFinal,
    SolicitudComparar,
    SolicitudConstruirPoblaciones,
    SolicitudDemostracionFinal,
    SolicitudEntrenar,
    SolicitudEstabilidad,
    SolicitudEvaluacionFinal,
    SolicitudExplicar,
    SolicitudGenerarEscenarios,
    SolicitudSeleccionar,
)
from suficiencia.application.demostracion_protocolo import _SinAjusteFicticio
from suficiencia.application.servicio_experimentos import configuraciones_congeladas
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.errores import ConfiguracionInvalida, ErrorSuficiencia
from suficiencia.domain.escenarios.particion import OPERACION_EVALUACION_FINAL
from suficiencia.domain.evaluacion.comparacion import referentes_a_construir
from suficiencia.domain.evaluacion.congelamiento import (
    ConfiguracionCongelable,
    RolConfiguracion,
    congelar,
    preparar_evaluacion_final,
)
from suficiencia.domain.evaluacion.protocolo import (
    aprobar,
    contenido_desde_datos,
    guardar_borrador,
)
from suficiencia.domain.experimentos import configuracion_experimentos_desde_datos
from suficiencia.domain.trazabilidad.registros import TipoRegistro

RESPONSABLE = "Demostración de F3.4 (EJEMPLO FICTICIO)"


def _rechazo(accion: Callable[[], object]) -> str:
    try:
        accion()
    except ErrorSuficiencia as error:
        return f"Rechazado: {error.causa}"
    return "Aceptado (no se esperaba)."


def ejecutar_demostracion_final(
    raiz: Path,
    solicitud: SolicitudDemostracionFinal,
    crear_servicios: Callable[[Path, bytes], Any],
    leer_yaml: Callable[[Path], Any],
) -> ResultadoDemostracionFinal:
    """Ver el docstring del módulo.

    Raises:
        ConfiguracionInvalida: si el protocolo o la configuración de experimentos no
            están marcados como ficticios.
    """

    def ruta(archivo: Path) -> Path:
        return archivo if archivo.is_absolute() else raiz / archivo

    contenido = contenido_desde_datos(leer_yaml(ruta(solicitud.protocolo)))
    if not contenido.ficticio:
        raise ConfiguracionInvalida(
            f"{solicitud.protocolo} no está marcado como ejemplo ficticio.",
            "La demostración solo usa protocolos ficticios, como "
            "config/ejemplos/protocolo_evaluacion_final_ficticio.yaml.",
        )
    datos_experimentos = leer_yaml(ruta(solicitud.experimentos))
    if not (isinstance(datos_experimentos, dict) and datos_experimentos.get("ficticio") is True):
        raise ConfiguracionInvalida(
            f"{solicitud.experimentos} no está marcado como ejemplo ficticio.",
            "La demostración solo usa configuraciones ficticias.",
        )
    pasos: list[PasoDemostracion] = []
    with tempfile.TemporaryDirectory() as temporal:
        proyecto = Path(temporal)
        (proyecto / "config").mkdir()
        shutil.copyfile(raiz / "config" / "proyecto.yaml", proyecto / "config" / "proyecto.yaml")
        servicios = crear_servicios(proyecto, secrets.token_bytes(32))
        comunes: dict[str, Any] = {
            "archivo": ruta(solicitud.archivo),
            "diccionario": ruta(solicitud.diccionario),
            "definicion": ruta(solicitud.definicion),
            "poblaciones": ruta(solicitud.poblaciones),
            "escenarios": ruta(solicitud.escenarios),
            "experimentos": ruta(solicitud.experimentos),
            "clave_efimera": True,
            "separador": solicitud.separador,
        }
        escenarios = solicitud.seleccion_escenarios

        poblaciones = servicios.escenarios.construir_poblaciones(
            SolicitudConstruirPoblaciones(
                archivo=comunes["archivo"],
                diccionario=comunes["diccionario"],
                definicion=comunes["definicion"],
                configuracion=comunes["poblaciones"],
                clave_efimera=True,
                separador=solicitud.separador,
            )
        )
        pasos.append(
            PasoDemostracion(
                titulo="Construir poblaciones, partición y sello",
                resultado=f"Prueba sellada: {poblaciones.tamano_prueba} unidades "
                "(solo se informa el tamaño)",
            )
        )
        factibles = {
            e.codigo: len(e.conjunto.split("+"))
            for e in servicios.escenarios.generar_escenarios(
                SolicitudGenerarEscenarios(
                    configuracion=comunes["escenarios"], diccionario=comunes["diccionario"]
                )
            ).escenarios
            if e.factible
        }
        configuracion_exp = configuracion_experimentos_desde_datos(datos_experimentos)
        referencia = configuracion_exp.referencia
        necesarios = tuple(
            dict.fromkeys(
                [
                    *escenarios,
                    *(
                        r.escenario
                        for r in referentes_a_construir(
                            referencia, dict.fromkeys(escenarios, "-"), factibles
                        )
                    ),
                ]
            )
        )
        entrenamiento = servicios.experimentos.entrenar(
            SolicitudEntrenar(**comunes, seleccion_escenarios=necesarios)
        )
        exitosas = sum(c.estado == "exitosa" for c in entrenamiento.corridas)
        pasos.append(
            PasoDemostracion(
                titulo="Entrenar las cinco familias (exploratorio)",
                resultado=f"{exitosas} corridas exitosas de {len(entrenamiento.corridas)} en "
                f"{', '.join(necesarios)} (los pedidos y los que necesitan R0 y los controles)",
            )
        )
        seleccion = servicios.experimentos.seleccionar(
            SolicitudSeleccionar(**comunes, seleccion_escenarios=escenarios)
        )
        repositorio = servicios.reportes.repositorio()
        accesos = repositorio.listar(TipoRegistro.ACCESO)
        pasos.append(
            PasoDemostracion(
                titulo="Seleccionar modelo y umbral con desarrollo; construir R0 y controles",
                resultado="; ".join(
                    f"{e.escenario}: {e.familia}, umbral {e.umbral:.3f}"
                    for e in seleccion.escenarios
                )
                + ". Referentes: "
                + "; ".join(
                    f"{r.codigo} = {r.seleccion.escenario}, {r.seleccion.familia}"
                    for r in seleccion.referentes
                )
                + f". Accesos a la prueba hasta aquí: {len(accesos)} (PI-10)",
            )
        )

        a_congelar = [
            (f"SEL-{e.escenario}", RolConfiguracion.SELECCIONADA, e) for e in seleccion.escenarios
        ] + [(r.codigo, RolConfiguracion(r.rol), r.seleccion) for r in seleccion.referentes]
        identificadores = tuple(i for i, _, _ in a_congelar)

        def solicitud_final(justificacion: str | None = None) -> SolicitudEvaluacionFinal:
            return SolicitudEvaluacionFinal(
                **comunes,
                particion=Path(poblaciones.carpeta_particion),
                configuraciones=identificadores,
                version_protocolo=1,
                justificacion_repeticion=justificacion,
            )

        procedimientos = {contenido.criterio.multiplicidad: _SinAjusteFicticio()}
        pasos.append(
            PasoDemostracion(
                titulo="Evaluación final sin protocolo aprobado",
                resultado=_rechazo(
                    lambda: servicios.evaluacion_final.evaluar(solicitud_final(), procedimientos)
                ),
            )
        )

        borrador = guardar_borrador(historial_protocolo(repositorio), contenido, None)
        repositorio.agregar(borrador)
        aprobacion = aprobar(
            historial_protocolo(repositorio),
            borrador.version,
            borrador.huella,
            RESPONSABLE,
            [],
            None,
        )
        repositorio.agregar(aprobacion.aprobacion)
        congeladas = []
        for identificador, rol, elegido in a_congelar:
            configuracion = ConfiguracionCongelable(
                identificador=identificador,
                rol=rol,
                version_protocolo=borrador.version,
                ficticio=True,
                **{
                    **elegido.configuracion_candidata,
                    "variables": tuple(elegido.configuracion_candidata["variables"]),
                },
            )
            repositorio.agregar(
                congelar(
                    configuracion,
                    historial_protocolo(repositorio),
                    configuraciones_congeladas(repositorio),
                )
            )
            congeladas.append(configuracion)
        pasos.append(
            PasoDemostracion(
                titulo="Aprobar el protocolo ficticio y congelar selección, R0 y controles",
                resultado=f"Versión {borrador.version} aprobada; congeladas: "
                + ", ".join(f"{c.identificador} ({c.huella().valor[:12]}…)" for c in congeladas),
            )
        )
        modificada = dataclasses.replace(congeladas[0], umbral=congeladas[0].umbral + 0.01)
        pasos.append(
            PasoDemostracion(
                titulo="Evaluar una configuración con el umbral cambiado",
                resultado=_rechazo(
                    lambda: preparar_evaluacion_final(
                        historial_protocolo(repositorio),
                        [modificada],
                        configuraciones_congeladas(repositorio),
                    )
                ),
            )
        )
        evaluacion = servicios.evaluacion_final.evaluar(solicitud_final(), procedimientos)
        pasos.append(
            PasoDemostracion(
                titulo="Evaluación final (apertura única de la prueba)",
                resultado=f"Regla: {evaluacion.estado_regla}"
                + (
                    f" ({evaluacion.escenario_suficiente})"
                    if evaluacion.escenario_suficiente
                    else ""
                )
                + f". Accesos permitidos a la prueba: {evaluacion.accesos_a_la_prueba}",
            )
        )
        pasos.append(
            PasoDemostracion(
                titulo="Repetir la evaluación final sin justificación",
                resultado=_rechazo(
                    lambda: servicios.evaluacion_final.evaluar(solicitud_final(), procedimientos)
                ),
            )
        )
        comparacion = servicios.evaluacion_final.comparar(
            SolicitudComparar(
                evaluacion=evaluacion.identificador_registro,
                experimentos=comunes["experimentos"],
                poblaciones=comunes["poblaciones"],
            )
        )
        pasos.append(
            PasoDemostracion(
                titulo="Comparar con R0 y los controles sin volver a abrir la prueba",
                resultado=f"Estado: {comparacion.estado}"
                + (
                    f" ({'; '.join(comparacion.motivos_no_validez)})"
                    if comparacion.motivos_no_validez
                    else ""
                )
                + f". Accesos permitidos a la prueba: {comparacion.accesos_a_la_prueba}",
            )
        )
        explicacion = servicios.interpretabilidad.explicar(
            SolicitudExplicar(**comunes, evaluacion=evaluacion.identificador_registro)
        )
        pasos.append(
            PasoDemostracion(
                titulo="Explicar las configuraciones congeladas con desarrollo (DP-11)",
                resultado=f"{len(explicacion.configuraciones)} configuraciones explicadas "
                f"({explicacion.alcance}; {', '.join(explicacion.niveles)}); explicadores: "
                + ", ".join(sorted({c.explicador for c in explicacion.configuraciones}))
                + f". Accesos permitidos a la prueba: {explicacion.accesos_a_la_prueba}",
            )
        )
        estabilidad = None
        if configuracion_exp.comparacion.estabilidad:
            estabilidad = servicios.evaluacion_final.estabilidad(
                SolicitudEstabilidad(
                    evaluacion=evaluacion.identificador_registro,
                    experimentos=comunes["experimentos"],
                ),
                procedimientos,
            )
            pasos.append(
                PasoDemostracion(
                    titulo="Estabilidad de la selección por fold y métricas por cohorte (CMP-5)",
                    resultado="; ".join(
                        f"{f.escenario}: cumple en {f.cumple} de {f.folds} folds, elegido en "
                        f"{f.elegido}"
                        for f in estabilidad.frecuencias
                    )
                    + f". Accesos permitidos a la prueba: {estabilidad.accesos_a_la_prueba}",
                )
            )
        permitidos = sum(
            1
            for g in repositorio.listar(TipoRegistro.ACCESO)
            if g.contenido["operacion"] == OPERACION_EVALUACION_FINAL and g.contenido["permitido"]
        )
        pasos.append(
            PasoDemostracion(
                titulo="Registro de accesos al terminar",
                resultado=f"{permitidos} acceso permitido a la prueba, el de la evaluación final",
            )
        )
    return ResultadoDemostracionFinal(
        archivo_protocolo=str(solicitud.protocolo),
        seleccion=seleccion,
        evaluacion=evaluacion,
        comparacion=comparacion,
        explicacion=explicacion,
        estabilidad=estabilidad,
        pasos=tuple(pasos),
    )
