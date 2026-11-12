"""Servicio de evaluación final y comparación con la referencia (M4): CU-08 y CU-12.

Desde H2.6: las comprobaciones que CU-08 hace antes de abrir la prueba (pasos 2
y 3): protocolo aprobado vigente y configuraciones idénticas a las congeladas
(RF-M4-05, RF-M4-09, RF-M4-12; PI-09). Desde F3.4: la evaluación final misma, que
abre la prueba una sola vez para todas las configuraciones congeladas (PI-15),
calcula sus métricas y aplica la regla de suficiencia en modo confirmatorio. Una
repetición sobre la misma partición exige justificación (RF-M4-09). La comparación
con R0 (CU-12) llega en F3.5.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    EstimacionResumen,
    MetricasPruebaResumen,
    ResultadoDemostracionFinal,
    ResultadoEvaluacionFinal,
    ResultadoVerificacionEvaluacionFinal,
    SolicitudDemostracionFinal,
    SolicitudEvaluacionFinal,
    SolicitudVerificarEvaluacionFinal,
)
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.application.servicio_datos import HistorialPreparado
from suficiencia.application.servicio_experimentos import configuraciones_congeladas
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.errores import ConfiguracionInvalida, ErrorSuficiencia
from suficiencia.domain.escenarios.construccion import construir_escenarios
from suficiencia.domain.escenarios.matrices import construir_matriz
from suficiencia.domain.escenarios.modelo import orden_ventana
from suficiencia.domain.escenarios.particion import OPERACION_EVALUACION_FINAL, SelloPrueba
from suficiencia.domain.escenarios.poblaciones import (
    ConfiguracionPoblaciones,
    construir_poblaciones,
)
from suficiencia.domain.evaluacion.congelamiento import (
    configuracion_desde_datos,
    preparar_evaluacion_final,
)
from suficiencia.domain.evaluacion.metricas import (
    MatrizConfusion,
    estimar,
    prevalencia,
    remuestras,
)
from suficiencia.domain.evaluacion.protocolo import evaluar_suficiencia, exigir_vigente
from suficiencia.domain.evaluacion.suficiencia import (
    PROCEDIMIENTOS_IMPLEMENTADOS,
    Estimacion,
    ProcedimientoMultiplicidad,
    ResultadoEscenario,
)
from suficiencia.domain.experimentos import ConfiguracionExperimentos
from suficiencia.domain.puertos import (
    CapturadorEntorno,
    FuenteCatalogoVentanas,
    FuenteVariables,
    RepositorioRegistros,
)
from suficiencia.domain.trazabilidad.registros import (
    ModoExperimento,
    TipoRegistro,
)

ARCHIVO_EXPERIMENTOS = Path("config") / "experimentos.yaml"
ARCHIVO_POBLACIONES = Path("config") / "poblaciones.yaml"
ARCHIVO_ESCENARIOS = Path("config") / "escenarios.yaml"


class EvaluacionFinalRepetida(ErrorSuficiencia):
    """La prueba de esta partición ya se abrió para una evaluación final (RF-M4-09)."""

    def __init__(self) -> None:
        super().__init__(
            "La evaluación final de esta partición ya se ejecutó: la prueba se abre una sola vez.",
            "Si debe repetirse, indique la justificación (--justificacion); queda registrada "
            "junto con el nuevo acceso (RF-M4-09).",
        )


class ServicioEvaluacionFinal(ServicioCasosDeUso):
    """Evaluación final, regla de suficiencia y comparación con la referencia (M4)."""

    NOMBRE: ClassVar[str] = "evaluacion_final"
    DESCRIPCION: ClassVar[str] = (
        "Evaluación final, regla de suficiencia y comparación con la referencia (M4)."
    )
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-08",
            "Ejecutar evaluación final y regla de suficiencia",
            "aprobación de un protocolo real (CU-05)",
            avance="comprobaciones previas (H2.6); apertura única de la prueba, métricas y "
            "regla en modo confirmatorio; demostración con protocolo ficticio (F3.4)",
        ),
        DefinicionCasoDeUso(
            "CU-12",
            "Ejecutar la evaluación comparativa frente a la referencia",
            "una fase posterior a la Fase 2",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        repositorio: Callable[[Path], RepositorioRegistros],
        archivo_registro: Callable[[], Path],
        leer_yaml: Callable[[Path], Any],
        *,
        preparar_historial: Callable[[Path, Path, Path | None, bool, str], HistorialPreparado],
        cargar_poblaciones: Callable[[Path], ConfiguracionPoblaciones],
        fuente_catalogo: Callable[[Path], FuenteCatalogoVentanas],
        fuente_diccionario: Callable[[Path], FuenteVariables],
        cargar_experimentos: Callable[[Path], ConfiguracionExperimentos],
        cargador_de_prueba: Callable[[Path], Callable[[], pd.DataFrame]],
        leer_manifiesto: Callable[[Path], dict[str, Any]],
        leer_modelo: Callable[[Path, str], object],
        predecir: Callable[[object, pd.DataFrame], np.ndarray],
        capturador: CapturadorEntorno,
        demostrar: Callable[[SolicitudDemostracionFinal], ResultadoDemostracionFinal],
    ) -> None:
        self._raiz = raiz
        self._repositorio = repositorio
        self._archivo_registro = archivo_registro
        self._leer_yaml = leer_yaml
        self._preparar_historial = preparar_historial
        self._cargar_poblaciones = cargar_poblaciones
        self._fuente_catalogo = fuente_catalogo
        self._fuente_diccionario = fuente_diccionario
        self._cargar_experimentos = cargar_experimentos
        self._cargador_de_prueba = cargador_de_prueba
        self._leer_manifiesto = leer_manifiesto
        self._leer_modelo = leer_modelo
        self._predecir = predecir
        self._capturador = capturador
        self._demostrar = demostrar

    def demostracion(self, solicitud: SolicitudDemostracionFinal) -> ResultadoDemostracionFinal:
        """Selección, congelamiento y evaluación final en un proyecto temporal (F3.4).

        Solo con un protocolo y una configuración ficticios; ver
        ``demostracion_final``.
        """
        return self._demostrar(solicitud)

    def _ruta(self, archivo: Path | None, por_omision: Path) -> Path:
        if archivo is None:
            return self._raiz / por_omision
        return archivo if archivo.is_absolute() else self._raiz / archivo

    def evaluar(
        self,
        solicitud: SolicitudEvaluacionFinal,
        procedimientos: Mapping[str, ProcedimientoMultiplicidad] = PROCEDIMIENTOS_IMPLEMENTADOS,
    ) -> ResultadoEvaluacionFinal:
        """Evaluación final (CU-08; RF-M4-06, RF-M4-09; PI-09, PI-15).

        1. Exige el protocolo aprobado vigente y comprueba que cada configuración sea
           la congelada (huella) y que su modelo no haya cambiado.
        2. Abre la prueba **una sola vez** para todas las configuraciones; queda en el
           registro de accesos. Repetir sobre la misma partición exige justificación.
        3. Arma la matriz de prueba de cada escenario, predice con el modelo congelado
           y calcula las métricas con sus intervalos y, con el umbral congelado, las
           métricas de clasificación.
        4. Aplica la regla de suficiencia en modo confirmatorio y registra todo.

        ``procedimientos`` son los de multiplicidad del proyecto (ninguno mientras
        DP-08f esté abierta); solo la demostración entrega uno ficticio.

        Raises:
            SinProtocoloVigente: sin protocolo aprobado vigente (PU-05).
            HuellaNoCoincide: si una configuración no es la congelada (PI-09).
            EvaluacionFinalRepetida: si ya se evaluó y no hay justificación (RF-M4-09).
            ConfiguracionInvalida: si un modelo cambió o los datos no son los de la partición.
        """
        repositorio = self._repositorio(self._archivo_registro())
        historial_p = historial_protocolo(repositorio)
        vigente = exigir_vigente(
            historial_p, str(solicitud.version_protocolo), "La evaluación final"
        )
        congeladas = {
            g.contenido["configuracion"]["identificador"]: g.contenido
            for g in repositorio.listar(TipoRegistro.CONGELAMIENTO)
        }
        faltan = [i for i in solicitud.configuraciones if i not in congeladas]
        if faltan:
            raise ConfiguracionInvalida(
                f"Las configuraciones {', '.join(faltan)} no están congeladas.",
                "Congélelas antes de la evaluación final (CU-07).",
            )
        configuraciones = [
            configuracion_desde_datos(congeladas[i]["configuracion"])
            for i in solicitud.configuraciones
        ]
        preparar_evaluacion_final(
            historial_p, configuraciones, configuraciones_congeladas(repositorio)
        )
        reentrenamientos = {
            c.identificador: json.loads(c.datos_reentrenamiento) for c in configuraciones
        }
        modelos = {
            i: self._leer_modelo(self._raiz / datos["modelo"], datos["huella_modelo"])
            for i, datos in reentrenamientos.items()
        }

        carpeta = self._ruta(solicitud.particion, solicitud.particion)
        manifiesto = self._leer_manifiesto(carpeta)
        huella_prueba = manifiesto["huellas"]["prueba"]
        previas = [
            g
            for g in repositorio.listar(TipoRegistro.ACCESO)
            if g.contenido["operacion"] == OPERACION_EVALUACION_FINAL
            and g.contenido["permitido"]
            and huella_prueba in g.contenido["motivo"]
        ]
        if previas and not solicitud.justificacion_repeticion:
            raise EvaluacionFinalRepetida()
        motivo = (
            f"Evaluación final con el protocolo v{vigente.numero} de "
            f"{', '.join(solicitud.configuraciones)}; partición {huella_prueba}"
        )
        if previas:
            motivo += f"; REPETICIÓN justificada: {solicitud.justificacion_repeticion}"

        experimentos = self._cargar_experimentos(
            self._ruta(solicitud.experimentos, ARCHIVO_EXPERIMENTOS)
        )
        poblaciones = self._cargar_poblaciones(
            self._ruta(solicitud.poblaciones, ARCHIVO_POBLACIONES)
        )
        catalogo = self._fuente_catalogo(
            self._ruta(solicitud.escenarios, ARCHIVO_ESCENARIOS)
        ).cargar()
        variables = self._fuente_diccionario(solicitud.diccionario).cargar()
        historial = self._preparar_historial(
            solicitud.archivo,
            solicitud.diccionario,
            solicitud.definicion,
            solicitud.clave_efimera,
            solicitud.separador,
        )
        if historial.huella_dataset.valor != manifiesto.get("huella_dataset"):
            raise ConfiguracionInvalida(
                "Los datos no son los de la partición: la huella del dataset no coincide.",
                "Use el mismo archivo y la misma clave de seudonimización con que se construyó "
                "la partición.",
            )

        # Único acceso a la prueba (PI-15).
        sello = SelloPrueba(self._cargador_de_prueba(carpeta), repositorio.agregar)
        prueba = sello.leer(OPERACION_EVALUACION_FINAL, motivo)

        columnas = historial.columnas
        clave = [*columnas.unidad]
        unidades = prueba[clave].astype(str)
        tabla = historial.tabla.merge(unidades, on=clave, how="inner")
        pobl = construir_poblaciones(tabla, columnas, historial.definicion, poblaciones.indices)
        escenarios = {
            e.codigo: e for e in construir_escenarios(catalogo.catalogo, variables.variables)
        }
        definicion = experimentos.metricas
        filas = []
        resultados_regla = []
        for configuracion in configuraciones:
            escenario = escenarios[configuracion.escenario]
            ventana = escenario.ventana.codigo
            matriz = construir_matriz(
                tabla,
                columnas,
                escenario,
                variables.variables,
                pobl.miembros[(poblaciones.diseno_principal, ventana)],
                poblaciones.indices.periodos[ventana],
                experimentos.matrices,
            )
            if tuple(str(c) for c in matriz.predictores.columns) != configuracion.variables:
                raise ConfiguracionInvalida(
                    f"Las variables de {configuracion.escenario} no son las congeladas.",
                    "Use el diccionario y la configuración con que se congeló.",
                )
            y = matriz.objetivo.to_numpy(dtype="int64")
            p = self._predecir(modelos[configuracion.identificador], matriz.predictores)
            indices = remuestras(
                y,
                matriz.cohorte.astype(str).tolist(),
                definicion.estratificacion,
                definicion.replicas,
                experimentos.semilla,
            )
            estimaciones = {
                m.value: estimar(definicion.funcion(m), y, p, indices, definicion.nivel)
                for m in definicion.metricas
            }
            confusion = MatrizConfusion.con_umbral(y, p, configuracion.umbral)
            con_umbral = {
                "accuracy": confusion.accuracy(),
                "precision": confusion.precision(),
                "recall": confusion.recall(),
                "f1": confusion.f1(),
            }
            filas.append(
                MetricasPruebaResumen(
                    identificador=configuracion.identificador,
                    rol=configuracion.rol.value,
                    escenario=configuracion.escenario,
                    algoritmo=configuracion.algoritmo,
                    filas=len(y),
                    eventos=int(y.sum()),
                    prevalencia=prevalencia(y),
                    umbral=configuracion.umbral,
                    metricas={
                        n: EstimacionResumen(
                            puntual=_numero(e.puntual),
                            limite_inferior=_numero(e.limite_inferior),
                            limite_superior=_numero(e.limite_superior),
                            replicas_validas=e.replicas_validas,
                        )
                        for n, e in estimaciones.items()
                    },
                    con_umbral={n: _numero(v) for n, v in con_umbral.items()},
                )
            )
            if configuracion.rol.value == "seleccionada":
                resultados_regla.append(
                    ResultadoEscenario(
                        configuracion.escenario,
                        escenario.conjunto.codigo,
                        orden_ventana(ventana),
                        len(escenario.conjunto.bloques),
                        {
                            n: Estimacion(e.puntual, e.limite_inferior, e.limite_superior)
                            for n, e in estimaciones.items()
                        },
                        {},
                    )
                )
        evaluacion = evaluar_suficiencia(
            historial_p,
            vigente.numero,
            ModoExperimento.CONFIRMATORIO,
            resultados_regla,
            procedimientos,
        )
        resultado = evaluacion.resultado
        detalle = tuple(
            f"{e.escenario}: {e.estado.value}"
            + "".join(f"; {c.condicion.metrica} {c.motivo}" for c in e.condiciones)
            for e in resultado.evaluaciones
        )
        guardado = RegistradorCorridas(repositorio, self._capturador).ejecutar(
            lambda: {
                "configuraciones": [f.model_dump() for f in filas],
                "regla": {
                    "estado": resultado.estado.value,
                    "escenario": resultado.escenario,
                    "detalle": list(detalle),
                },
            },
            modo=ModoExperimento.CONFIRMATORIO,
            configuracion={
                "tipo": "evaluacion_final",
                "configuraciones": list(solicitud.configuraciones),
                "huella_particion_prueba": huella_prueba,
                "repeticion": solicitud.justificacion_repeticion,
                "ficticio": evaluacion.ficticio,
            },
            semillas={"bootstrap": experimentos.semilla},
            huella_datos=historial.huella_dataset.valor,
            version_protocolo=str(vigente.numero),
        )
        accesos = sum(
            1
            for g in repositorio.listar(TipoRegistro.ACCESO)
            if g.contenido["operacion"] == OPERACION_EVALUACION_FINAL and g.contenido["permitido"]
        )
        return ResultadoEvaluacionFinal(
            version_protocolo=vigente.numero,
            ficticio=evaluacion.ficticio or any(c.ficticio for c in configuraciones),
            configuraciones=tuple(filas),
            estado_regla=resultado.estado.value,
            escenario_suficiente=resultado.escenario,
            detalle_regla=detalle,
            identificador_registro=guardado.contenido["identificador"],
            accesos_a_la_prueba=accesos,
        )

    def verificar_precondiciones(
        self, solicitud: SolicitudVerificarEvaluacionFinal
    ) -> ResultadoVerificacionEvaluacionFinal:
        """Comprueba protocolo vigente y huellas sin abrir la prueba (CU-08, pasos 2 y 3).

        Raises:
            SinProtocoloVigente: sin protocolo aprobado vigente (PU-05).
            HuellaNoCoincide: si una configuración no es la congelada (PI-09).
        """
        configuraciones = [
            configuracion_desde_datos(
                self._leer_yaml(archivo if archivo.is_absolute() else self._raiz / archivo)
            )
            for archivo in solicitud.archivos
        ]
        repositorio = self._repositorio(self._archivo_registro())
        preparacion = preparar_evaluacion_final(
            historial_protocolo(repositorio),
            configuraciones,
            configuraciones_congeladas(repositorio),
        )
        return ResultadoVerificacionEvaluacionFinal(
            version_protocolo=preparacion.version_protocolo,
            huella_protocolo=preparacion.huella_protocolo,
            configuraciones=dict(preparacion.configuraciones),
            ficticio=preparacion.ficticio,
        )


def _numero(valor: float) -> float | None:
    return None if valor != valor else float(valor)  # NaN no se guarda en el registro
