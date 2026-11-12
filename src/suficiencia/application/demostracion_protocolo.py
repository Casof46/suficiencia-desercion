"""Demostración de H2.6 con un protocolo ficticio (EJEMPLO FICTICIO).

Recorre el ciclo completo en un registro temporal que se borra al terminar: nada
llega al registro del proyecto. Muestra que la regla en modo confirmatorio exige
un protocolo aprobado, que una versión aprobada no se edita, tres resultados de
la regla (un escenario suficiente, ninguno cumple y un empate que el desempate no
resuelve), el rechazo de una configuración distinta de la congelada y la
desviación obligatoria al cambiar el protocolo con experimentos confirmatorios.

Los resultados de los escenarios se fabrican a partir de los límites del propio
protocolo ficticio, un poco por encima o por debajo de cada límite. No son
métricas de ningún modelo ni de ningún dato.

El procedimiento de multiplicidad de la demostración (``_SinAjusteFicticio``) no
es una propuesta: deja pasar todos los escenarios que cumplen. Solo se usa aquí,
con un protocolo marcado como ficticio. El proyecto no implementa ninguno
(DP-08f abierta).
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from suficiencia.application.contratos import (
    CasoReglaDemostracion,
    CondicionDemostracion,
    EscenarioDemostracion,
    PasoDemostracion,
    ResultadoDemostracionProtocolo,
)
from suficiencia.domain.errores import ConfiguracionInvalida, ErrorSuficiencia
from suficiencia.domain.evaluacion.congelamiento import (
    ConfiguracionCongelable,
    RolConfiguracion,
    congelar,
    preparar_evaluacion_final,
)
from suficiencia.domain.evaluacion.protocolo import (
    ContenidoProtocolo,
    DatosDesviacion,
    HistorialProtocolo,
    aprobar,
    contenido_desde_datos,
    evaluar_suficiencia,
    guardar_borrador,
)
from suficiencia.domain.evaluacion.suficiencia import (
    PROCEDIMIENTOS_IMPLEMENTADOS,
    CriterioSuficiencia,
    EstadoEscenario,
    Estimacion,
    EvaluacionEscenario,
    ResultadoEscenario,
    ResultadoSuficiencia,
    Sentido,
    TipoCondicion,
    aplicar_regla,
)
from suficiencia.domain.puertos import RepositorioRegistros
from suficiencia.domain.trazabilidad.registros import ModoExperimento, TipoRegistro

RESPONSABLE = "Demostración (EJEMPLO FICTICIO)"
_DISTANCIA = 0.02
_ULTIMA_VENTANA = 2
"""En la demostración, cada escenario se compara con una referencia ficticia de su
ventana y de cada ventana posterior hasta T2: T0 tiene tres comparadores, T2 uno."""


class _SinAjusteFicticio:
    """EJEMPLO FICTICIO: confirma todos los escenarios que cumplen. No es una propuesta."""

    def confirmar(
        self,
        evaluaciones: tuple[EvaluacionEscenario, ...],
        resultados: Mapping[str, ResultadoEscenario],
    ) -> frozenset[str]:
        return frozenset(e.escenario for e in evaluaciones if e.estado is EstadoEscenario.CUMPLE)


def _estimacion(valor: float) -> Estimacion:
    return Estimacion(valor, valor, valor)


def _resultado(
    criterio: CriterioSuficiencia,
    escenario: str,
    orden_ventana: int,
    numero_bloques: int,
    cumple: bool,
) -> ResultadoEscenario:
    """Fabrica estimaciones a una distancia fija del límite de cada condición."""
    metricas: dict[str, Estimacion] = {}
    diferencias: dict[tuple[str, str], dict[str, Estimacion]] = {}
    comparadores = [f"referencia_ficticia_T{v}" for v in range(orden_ventana, _ULTIMA_VENTANA + 1)]
    for condicion in criterio.condiciones:
        mayor = criterio.sentido_de(condicion.metrica) is Sentido.MAYOR_ES_MEJOR
        paso = _DISTANCIA if mayor == cumple else -_DISTANCIA
        if condicion.tipo is TipoCondicion.UMBRAL:
            metricas[condicion.metrica] = _estimacion(condicion.limite + paso)
        else:
            assert condicion.comparador is not None
            base = -condicion.limite if mayor else condicion.limite
            diferencias[(condicion.metrica, condicion.comparador)] = {
                comparador: _estimacion(base + paso) for comparador in comparadores
            }
    for metrica in criterio.metricas:
        metricas.setdefault(metrica.nombre, _estimacion(0.5))
    conjunto = "+".join(escenario.split("-", 1)[1])
    return ResultadoEscenario(
        escenario, conjunto, orden_ventana, numero_bloques, metricas, diferencias
    )


def _caso(titulo: str, resultado: ResultadoSuficiencia) -> CasoReglaDemostracion:
    return CasoReglaDemostracion(
        titulo=titulo,
        estado=resultado.estado.value,
        escenario=resultado.escenario,
        empatados=resultado.empatados,
        escenarios=tuple(
            EscenarioDemostracion(
                escenario=e.escenario,
                estado=e.estado.value,
                condiciones=tuple(
                    CondicionDemostracion(descripcion=c.motivo, cumple=c.cumple)
                    for c in e.condiciones
                ),
            )
            for e in resultado.evaluaciones
        ),
    )


def _rechazo(funcion: Callable[[], object]) -> str:
    try:
        funcion()
    except ErrorSuficiencia as error:
        return f"Rechazado. {error.causa}"
    return "Aceptado (no se esperaba)."


def _historial(repositorio: RepositorioRegistros) -> HistorialProtocolo:
    return HistorialProtocolo.desde_registros(
        [g.contenido for g in repositorio.listar(TipoRegistro.PROTOCOLO)]
    )


def _configuracion(version: int, umbral: float) -> ConfiguracionCongelable:
    return ConfiguracionCongelable(
        identificador="CFG-DEMOSTRACION-1",
        rol=RolConfiguracion.SELECCIONADA,
        escenario="T1-AF",
        algoritmo="algoritmo_ficticio",
        hiperparametros={"parametro_ficticio": 1},
        preprocesamiento={"paso_ficticio": "ninguno"},
        variables=("variable_ficticia_1", "variable_ficticia_2"),
        umbral=umbral,
        calibracion={"metodo": "ninguna (ficticio)"},
        semilla=0,
        datos_reentrenamiento="indices_ficticios",
        version_protocolo=version,
        ficticio=True,
    )


def ejecutar_demostracion(
    archivo: Path,
    leer_yaml: Callable[[Path], Any],
    repositorio: Callable[[Path], RepositorioRegistros],
) -> ResultadoDemostracionProtocolo:
    contenido: ContenidoProtocolo = contenido_desde_datos(leer_yaml(archivo))
    if not contenido.ficticio:
        raise ConfiguracionInvalida(
            f"{archivo} no está marcado como ejemplo ficticio.",
            "La demostración solo usa protocolos ficticios, como "
            "config/ejemplos/protocolo_ficticio.yaml.",
        )
    criterio = contenido.criterio
    procedimientos = {criterio.multiplicidad: _SinAjusteFicticio()}
    pasos: list[PasoDemostracion] = []
    casos: list[CasoReglaDemostracion] = []
    with tempfile.TemporaryDirectory() as carpeta:
        registro = repositorio(Path(carpeta) / "registro_demostracion.sqlite")

        borrador = guardar_borrador(_historial(registro), contenido, None)
        registro.agregar(borrador)
        pasos.append(
            PasoDemostracion(
                titulo="Guardar el borrador",
                resultado=f"Versión {borrador.version} en borrador, huella {borrador.huella[:12]}…",
            )
        )
        uno = [_resultado(criterio, "T1-AF", 1, 2, True)]
        pasos.append(
            PasoDemostracion(
                titulo="Aplicar la regla en modo confirmatorio con el protocolo en borrador",
                resultado=_rechazo(
                    lambda: evaluar_suficiencia(
                        _historial(registro),
                        borrador.version,
                        ModoExperimento.CONFIRMATORIO,
                        uno,
                        procedimientos,
                    )
                ),
            )
        )
        exploratoria = evaluar_suficiencia(
            _historial(registro),
            borrador.version,
            ModoExperimento.EXPLORATORIO,
            uno,
            procedimientos,
        )
        pasos.append(
            PasoDemostracion(
                titulo="La misma regla en modo exploratorio",
                resultado="Permitido y marcado como exploratorio: "
                f"{exploratoria.resultado.estado.value}",
            )
        )
        aprobacion = aprobar(
            _historial(registro), borrador.version, borrador.huella, RESPONSABLE, [], None
        )
        registro.agregar(aprobacion.aprobacion)
        pasos.append(
            PasoDemostracion(
                titulo="Aprobar la versión revisada (huella coincidente)",
                resultado=f"Versión {borrador.version} aprobada y vigente",
            )
        )
        pasos.append(
            PasoDemostracion(
                titulo="Editar la versión aprobada",
                resultado=_rechazo(
                    lambda: guardar_borrador(_historial(registro), contenido, borrador.version)
                ),
            )
        )
        pasos.append(
            PasoDemostracion(
                titulo="Aplicar la regla con los procedimientos de multiplicidad del proyecto",
                resultado=_rechazo(
                    lambda: aplicar_regla(criterio, uno, PROCEDIMIENTOS_IMPLEMENTADOS)
                ),
            )
        )

        familias = (
            (
                "Un escenario suficiente: cumplen T1-AF y T2-A; decide el desempate del protocolo",
                [
                    _resultado(criterio, "T0-A", 0, 1, False),
                    _resultado(criterio, "T1-AF", 1, 2, True),
                    _resultado(criterio, "T2-A", 2, 1, True),
                ],
            ),
            (
                "Ningún escenario cumple",
                [
                    _resultado(criterio, "T0-A", 0, 1, False),
                    _resultado(criterio, "T1-AF", 1, 2, False),
                    _resultado(criterio, "T2-A", 2, 1, False),
                ],
            ),
            (
                "Empate: dos escenarios iguales en todas las claves de desempate",
                [
                    _resultado(criterio, "T1-AF", 1, 2, True),
                    _resultado(criterio, "T1-AS", 1, 2, True),
                ],
            ),
        )
        for titulo, resultados in familias:
            evaluacion = evaluar_suficiencia(
                _historial(registro),
                borrador.version,
                ModoExperimento.CONFIRMATORIO,
                resultados,
                procedimientos,
            )
            casos.append(_caso(titulo, evaluacion.resultado))

        configuracion = _configuracion(borrador.version, 0.5)
        congelada = congelar(configuracion, _historial(registro), {})
        registro.agregar(congelada)
        congeladas = {configuracion.identificador: congelada.huella}
        pasos.append(
            PasoDemostracion(
                titulo="Congelar una configuración ficticia",
                resultado=f"Congelada con huella {congelada.huella[:12]}…",
            )
        )
        verificada = preparar_evaluacion_final(_historial(registro), [configuracion], congeladas)
        pasos.append(
            PasoDemostracion(
                titulo="Verificar la configuración congelada antes de la evaluación final",
                resultado="Coincide con su huella; protocolo vigente: "
                f"versión {verificada.version_protocolo}",
            )
        )
        alterada = _configuracion(borrador.version, 0.4)
        pasos.append(
            PasoDemostracion(
                titulo="Verificar la misma configuración con otro umbral",
                resultado=_rechazo(
                    lambda: preparar_evaluacion_final(_historial(registro), [alterada], congeladas)
                ),
            )
        )

        confirmatorios = ["EXP-DEMOSTRACION-1"]
        nueva = guardar_borrador(_historial(registro), contenido, None)
        registro.agregar(nueva)
        pasos.append(
            PasoDemostracion(
                titulo="Proponer un cambio: borrador de una versión nueva",
                resultado=f"Versión {nueva.version} en borrador; "
                f"la {borrador.version} sigue vigente",
            )
        )
        pasos.append(
            PasoDemostracion(
                titulo="Aprobarla sin desviación, con un experimento confirmatorio ficticio",
                resultado=_rechazo(
                    lambda: aprobar(
                        _historial(registro),
                        nueva.version,
                        nueva.huella,
                        RESPONSABLE,
                        confirmatorios,
                        None,
                    )
                ),
            )
        )
        cambio = aprobar(
            _historial(registro),
            nueva.version,
            nueva.huella,
            RESPONSABLE,
            confirmatorios,
            DatosDesviacion("Cambio ficticio de la demostración", "Justificación ficticia"),
        )
        assert cambio.desviacion is not None
        registro.agregar(cambio.desviacion)
        registro.agregar(cambio.aprobacion)
        estados = ", ".join(f"v{v.numero} {v.estado.value}" for v in _historial(registro).versiones)
        pasos.append(
            PasoDemostracion(
                titulo="Aprobarla registrando la desviación",
                resultado=f"{estados}; resultados marcados: "
                f"{', '.join(cambio.desviacion.resultados_afectados)}",
            )
        )
    return ResultadoDemostracionProtocolo(
        archivo_protocolo=str(archivo),
        huella_protocolo=borrador.huella,
        casos=tuple(casos),
        pasos=tuple(pasos),
    )
