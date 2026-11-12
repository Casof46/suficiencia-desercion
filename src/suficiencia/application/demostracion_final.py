"""Demostración de F3.4: selección, congelamiento y evaluación final (EJEMPLO FICTICIO).

Recorre el final del método con datos sintéticos y configuraciones ficticias, en
un **proyecto temporal** que se borra al terminar: nada llega al registro ni a la
carpeta de trabajo del proyecto. Usa los mismos servicios que el proyecto real:

1. Construye las poblaciones, la partición y el sello de la prueba (H2.5).
2. Entrena las cinco familias en los escenarios pedidos (F3.2).
3. Selecciona modelo y umbral por escenario solo con desarrollo (DP-10, DP-06) y
   comprueba que el registro de accesos no tiene ningún acceso a la prueba (PI-10).
4. Intenta la evaluación final sin protocolo: se rechaza (PU-05).
5. Aprueba el protocolo ficticio en el registro temporal y congela cada
   configuración seleccionada con su huella (RF-M4-12).
6. Intenta evaluar una configuración modificada: se rechaza (PI-09).
7. Ejecuta la evaluación final: abre la prueba una sola vez para todas las
   configuraciones y aplica la regla en modo confirmatorio (PI-15).
8. Intenta repetirla sin justificación: se rechaza (RF-M4-09).

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
    SolicitudConstruirPoblaciones,
    SolicitudDemostracionFinal,
    SolicitudEntrenar,
    SolicitudEvaluacionFinal,
    SolicitudSeleccionar,
)
from suficiencia.application.demostracion_protocolo import _SinAjusteFicticio
from suficiencia.application.servicio_experimentos import configuraciones_congeladas
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.errores import ConfiguracionInvalida, ErrorSuficiencia
from suficiencia.domain.escenarios.particion import OPERACION_EVALUACION_FINAL
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
        entrenamiento = servicios.experimentos.entrenar(
            SolicitudEntrenar(**comunes, seleccion_escenarios=escenarios)
        )
        exitosas = sum(c.estado == "exitosa" for c in entrenamiento.corridas)
        pasos.append(
            PasoDemostracion(
                titulo="Entrenar las cinco familias (exploratorio)",
                resultado=f"{exitosas} corridas exitosas de {len(entrenamiento.corridas)}",
            )
        )
        seleccion = servicios.experimentos.seleccionar(
            SolicitudSeleccionar(**comunes, seleccion_escenarios=escenarios)
        )
        repositorio = servicios.reportes.repositorio()
        accesos = repositorio.listar(TipoRegistro.ACCESO)
        pasos.append(
            PasoDemostracion(
                titulo="Seleccionar modelo y umbral solo con desarrollo",
                resultado="; ".join(
                    f"{e.escenario}: {e.familia}, umbral {e.umbral:.3f}"
                    for e in seleccion.escenarios
                )
                + f". Accesos a la prueba hasta aquí: {len(accesos)} (PI-10)",
            )
        )

        identificadores = tuple(f"SEL-{e.escenario}" for e in seleccion.escenarios)

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
        for elegido, identificador in zip(seleccion.escenarios, identificadores, strict=True):
            configuracion = ConfiguracionCongelable(
                identificador=identificador,
                rol=RolConfiguracion.SELECCIONADA,
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
                titulo="Aprobar el protocolo ficticio y congelar las configuraciones",
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
        pasos=tuple(pasos),
    )
