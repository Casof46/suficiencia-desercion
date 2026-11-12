"""Servicio de explicaciones SHAP y LIME (M5): CU-09.

Desde F3.6: explica las configuraciones congeladas de una evaluación final con el
alcance de DP-11 (RF-M5-01 a 05). Solo explica configuraciones congeladas, con su
modelo verificado por huella, y solo con filas de desarrollo: la prueba no se vuelve
a abrir (PI-13, PI-15). Cada explicación queda en el registro con la partición, las
muestras y la semilla. Las explicaciones son asociaciones del modelo, no causas.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from suficiencia.application._base import DefinicionCasoDeUso, ServicioCasosDeUso
from suficiencia.application.contratos import (
    ContribucionResumen,
    ExplicacionConfiguracionResumen,
    ExplicacionLocalResumen,
    ResultadoExplicacion,
    SolicitudExplicar,
)
from suficiencia.application.preparacion_desarrollo import filas_de, preparar
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.application.servicio_datos import HistorialPreparado
from suficiencia.application.servicio_evaluacion_final import evaluacion_final_registrada
from suficiencia.application.servicio_experimentos import (
    configuraciones_congeladas,
    ruta_en_registro,
)
from suficiencia.application.servicio_protocolo import historial_protocolo
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.modelo import Bloque
from suficiencia.domain.escenarios.particion import OPERACION_EVALUACION_FINAL
from suficiencia.domain.escenarios.poblaciones import ConfiguracionPoblaciones
from suficiencia.domain.evaluacion.congelamiento import (
    ConfiguracionCongelable,
    HuellaNoCoincide,
    configuracion_desde_datos,
)
from suficiencia.domain.evaluacion.interpretabilidad import (
    AlcanceInterpretabilidad,
    NivelExplicacion,
    elegir_muestras,
    importancia_global,
    importancia_por_bloque,
    principales,
)
from suficiencia.domain.evaluacion.protocolo import exigir_vigente
from suficiencia.domain.experimentos import ConfiguracionExperimentos
from suficiencia.domain.puertos import (
    CapturadorEntorno,
    FuenteCatalogoVentanas,
    FuenteVariables,
    RepositorioRegistros,
)
from suficiencia.domain.trazabilidad.registros import ModoExperimento, TipoRegistro

ARCHIVO_EXPERIMENTOS = Path("config") / "experimentos.yaml"
ARCHIVO_POBLACIONES = Path("config") / "poblaciones.yaml"
ARCHIVO_ESCENARIOS = Path("config") / "escenarios.yaml"
CARPETA_EXPLICACIONES = "explicaciones"

ExplicarModelo = Callable[..., Any]
"""``explicar_modelo`` de la capa de experimentación (importación diferida)."""


class ServicioInterpretabilidad(ServicioCasosDeUso):
    """Explicaciones SHAP y LIME (M5)."""

    NOMBRE: ClassVar[str] = "interpretabilidad"
    DESCRIPCION: ClassVar[str] = "Explicaciones SHAP y LIME (M5)."
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]] = (
        DefinicionCasoDeUso(
            "CU-09",
            "Generar explicaciones",
            "aprobación de un protocolo real (CU-05) y DP-11",
            avance="SHAP global, por bloque y local, y LIME local sobre configuraciones "
            "congeladas; demostración con protocolo ficticio (F3.6)",
        ),
    )

    def __init__(
        self,
        raiz: Path,
        repositorio: Callable[[Path], RepositorioRegistros],
        archivo_registro: Callable[[], Path],
        *,
        preparar_historial: Callable[[Path, Path, Path | None, bool, str], HistorialPreparado],
        cargar_poblaciones: Callable[[Path], ConfiguracionPoblaciones],
        fuente_catalogo: Callable[[Path], FuenteCatalogoVentanas],
        fuente_diccionario: Callable[[Path], FuenteVariables],
        cargar_experimentos: Callable[[Path], ConfiguracionExperimentos],
        leer_modelo: Callable[[Path, str], object],
        explicar_modelo: ExplicarModelo,
        capturador: CapturadorEntorno,
        carpeta_trabajo: Callable[[], Path],
        guardar_tablas: Callable[[Path, Mapping[str, pd.DataFrame]], dict[str, dict[str, str]]],
    ) -> None:
        self._raiz = raiz
        self._repositorio = repositorio
        self._archivo_registro = archivo_registro
        self._preparar_historial = preparar_historial
        self._cargar_poblaciones = cargar_poblaciones
        self._fuente_catalogo = fuente_catalogo
        self._fuente_diccionario = fuente_diccionario
        self._cargar_experimentos = cargar_experimentos
        self._leer_modelo = leer_modelo
        self._explicar_modelo = explicar_modelo
        self._capturador = capturador
        self._carpeta_trabajo = carpeta_trabajo
        self._guardar_tablas = guardar_tablas

    def _ruta(self, archivo: Path | None, por_omision: Path) -> Path:
        if archivo is None:
            return self._raiz / por_omision
        return archivo if archivo.is_absolute() else self._raiz / archivo

    def explicar(self, solicitud: SolicitudExplicar) -> ResultadoExplicacion:
        """Explicaciones de las configuraciones congeladas de una evaluación final (CU-09).

        1. Exige que la evaluación exista y que su protocolo siga vigente.
        2. Elige las configuraciones según el alcance de DP-11 y comprueba que cada una
           sea la congelada (huella) y que su modelo no haya cambiado (PI-13).
        3. Arma la matriz de desarrollo del escenario con las cohortes con que se
           entrenó el modelo, elige las muestras con la semilla y calcula SHAP con el
           explicador de la familia y, si se pide, LIME para los registros locales.
        4. Agrega por variable y por bloque, guarda las tablas y lo registra todo.

        Raises:
            SinProtocoloVigente: si el protocolo de la evaluación ya no es el vigente.
            HuellaNoCoincide: si una configuración no es la congelada.
            DecisionPendiente: si falta un dato de DP-11 u otra decisión.
            ConfiguracionInvalida: si la evaluación no existe, el alcance no tiene qué
                explicar, los datos no son los del entrenamiento o un archivo cambió.
        """
        repositorio = self._repositorio(self._archivo_registro())
        evaluacion = evaluacion_final_registrada(repositorio, solicitud.evaluacion)
        version = int(evaluacion["version_protocolo"])
        exigir_vigente(historial_protocolo(repositorio), str(version), "Las explicaciones")
        accesos_antes = len(repositorio.listar(TipoRegistro.ACCESO))
        experimentos = self._cargar_experimentos(
            self._ruta(solicitud.experimentos, ARCHIVO_EXPERIMENTOS)
        )
        definicion = experimentos.interpretabilidad
        configuraciones = self._configuraciones(repositorio, evaluacion, definicion.alcance)

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
        preparacion = preparar(
            historial.tabla,
            historial.columnas,
            historial.definicion,
            poblaciones,
            catalogo,
            variables,
            experimentos,
        )
        matrices = {m.escenario: m for m in preparacion.matrices}
        bloque_de = {v.nombre: v.bloque.value for v in variables.variables}
        orden_bloques = [b.value for b in Bloque]
        local = definicion.local
        semilla = experimentos.semilla

        resumenes: list[ExplicacionConfiguracionResumen] = []
        tablas: dict[str, pd.DataFrame] = {}
        muestras_registro: list[dict[str, Any]] = []
        for numero, configuracion in enumerate(configuraciones, start=1):
            datos = json.loads(configuracion.datos_reentrenamiento)
            if datos["huella_fuente"] != historial.huella_fuente.valor:
                raise ConfiguracionInvalida(
                    "Los datos no son los del entrenamiento: la huella del archivo de "
                    "origen no coincide.",
                    "Use el mismo archivo con que se entrenaron las configuraciones congeladas.",
                )
            modelo = self._leer_modelo(self._raiz / datos["modelo"], datos["huella_modelo"])
            matriz = matrices.get(configuracion.escenario)
            if matriz is None or tuple(str(c) for c in matriz.predictores.columns) != tuple(
                configuracion.variables
            ):
                raise ConfiguracionInvalida(
                    f"Las variables de {configuracion.escenario} no son las congeladas.",
                    "Use el diccionario y la configuración con que se congeló.",
                )
            mascara = filas_de(matriz, tuple(str(c) for c in datos["cohortes"]))
            particion = matriz.predictores[mascara.to_numpy()]
            muestras = elegir_muestras(
                len(particion),
                definicion.muestra_fondo,
                definicion.muestra_explicar,
                local.registros if local else 0,
                semilla,
            )
            explicar = particion.iloc[list(muestras.explicar)]
            explicacion = self._explicar_modelo(
                modelo,
                configuracion.algoritmo,
                configuracion.variables,
                particion.iloc[list(muestras.fondo)],
                explicar,
                muestras.locales,
                definicion.kernel_muestras,
                local.lime_muestras if local else 1,
                semilla,
            )
            filas_fondo = len(muestras.fondo)
            nombres = list(configuracion.variables)
            globales = importancia_global(explicacion.shap, nombres)
            por_bloque = importancia_por_bloque(globales, bloque_de, orden_bloques)
            locales = []
            filas_locales: list[dict[str, Any]] = []
            for orden, (posicion, pesos_lime, ajuste) in enumerate(
                zip(muestras.locales, explicacion.lime, explicacion.lime_ajuste, strict=True),
                start=1,
            ):
                shap_registro = dict(zip(nombres, explicacion.shap[posicion], strict=True))
                assert local is not None
                locales.append(
                    ExplicacionLocalResumen(
                        registro=orden,
                        shap=_contribuciones(principales(shap_registro, local.variables)),
                        lime=_contribuciones(principales(pesos_lime, local.variables)),
                        lime_ajuste=ajuste,
                    )
                )
                unidad = str(explicar.index.astype(str)[posicion])
                for metodo, valores in (("shap", shap_registro), ("lime", pesos_lime)):
                    filas_locales.extend(
                        {
                            "registro": orden,
                            "unidad": unidad,
                            "metodo": metodo,
                            "variable": v,
                            "contribucion": float(valores[v]),
                        }
                        for v in nombres
                    )
            con_global = NivelExplicacion.GLOBAL in definicion.niveles
            con_bloque = NivelExplicacion.BLOQUE in definicion.niveles
            tablas[f"configuracion_{numero}_importancias"] = pd.DataFrame(
                [
                    {"nivel": "variable", "nombre": v, "bloque": bloque_de[v], "importancia": i}
                    for v, i in globales.items()
                    if con_global
                ]
                + [
                    {"nivel": "bloque", "nombre": b, "bloque": b, "importancia": i}
                    for b, i in por_bloque.items()
                    if con_bloque
                ],
                columns=["nivel", "nombre", "bloque", "importancia"],
            )
            if local is not None:
                tablas[f"configuracion_{numero}_locales"] = pd.DataFrame(
                    filas_locales,
                    columns=["registro", "unidad", "metodo", "variable", "contribucion"],
                )
            muestras_registro.append(
                {
                    "configuracion": configuracion.identificador,
                    "cohortes": list(datos["cohortes"]),
                    "filas_particion": len(particion),
                    "filas_fondo": filas_fondo,
                    "fondo_en_shap": explicacion.usa_fondo,
                    "filas_explicadas": len(muestras.explicar),
                    "registros_locales": len(muestras.locales),
                    "explicador": explicacion.explicador.value,
                    "escala": explicacion.escala.value,
                }
            )
            resumenes.append(
                ExplicacionConfiguracionResumen(
                    identificador=configuracion.identificador,
                    rol=configuracion.rol.value,
                    escenario=configuracion.escenario,
                    algoritmo=configuracion.algoritmo,
                    explicador=explicacion.explicador.value,
                    escala=explicacion.escala.value,
                    filas_particion=len(particion),
                    filas_fondo=filas_fondo,
                    filas_explicadas=len(muestras.explicar),
                    valor_base=explicacion.valor_base,
                    error_aditividad=explicacion.error_aditividad,
                    importancia_variables=globales if con_global else {},
                    importancia_bloques=por_bloque if con_bloque else {},
                    locales=tuple(locales),
                )
            )

        marca = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%f")
        carpeta = self._carpeta_trabajo() / CARPETA_EXPLICACIONES / marca
        ficticio = any(c.ficticio for c in configuraciones) or bool(
            evaluacion["configuracion"].get("ficticio")
        )

        def registrar() -> dict[str, Any]:
            archivos = self._guardar_tablas(carpeta, tablas)
            return {
                "configuraciones": [r.model_dump() for r in resumenes],
                "archivos": {"carpeta": ruta_en_registro(carpeta, self._raiz), **archivos},
            }

        guardado = RegistradorCorridas(repositorio, self._capturador).ejecutar(
            registrar,
            modo=ModoExperimento.EXPLORATORIO,
            configuracion={
                "tipo": "explicacion",
                "evaluacion_final": solicitud.evaluacion,
                "alcance": definicion.alcance.value,
                "niveles": [n.value for n in definicion.niveles],
                "particion": definicion.particion.value,
                "muestra_fondo": definicion.muestra_fondo,
                "muestra_explicar": definicion.muestra_explicar,
                "kernel_muestras": definicion.kernel_muestras,
                "local": None
                if local is None
                else {
                    "registros": local.registros,
                    "variables": local.variables,
                    "lime_muestras": local.lime_muestras,
                },
                "muestras": muestras_registro,
                "ficticio": ficticio,
            },
            semillas={"explicacion": semilla},
            huella_datos=historial.huella_dataset.valor,
            version_protocolo=str(version),
        )
        if guardado.contenido["estado"] != "exitosa":
            raise ConfiguracionInvalida(
                f"La explicación no se pudo guardar: {guardado.contenido['error']}",
                "Quedó registrada como fallida; revise la carpeta de trabajo.",
            )
        accesos = repositorio.listar(TipoRegistro.ACCESO)
        if len(accesos) != accesos_antes:  # pragma: no cover - protección (PI-15)
            raise ConfiguracionInvalida(
                "La explicación registró un acceso a la prueba.",
                "Es un defecto del programa; informe el caso.",
            )
        return ResultadoExplicacion(
            evaluacion=solicitud.evaluacion,
            version_protocolo=version,
            ficticio=ficticio,
            alcance=definicion.alcance.value,
            niveles=tuple(n.value for n in definicion.niveles),
            particion=definicion.particion.value,
            semilla=semilla,
            configuraciones=tuple(resumenes),
            carpeta=ruta_en_registro(carpeta, self._raiz),
            identificador_registro=guardado.contenido["identificador"],
            accesos_a_la_prueba=sum(
                1
                for g in accesos
                if g.contenido["operacion"] == OPERACION_EVALUACION_FINAL
                and g.contenido["permitido"]
            ),
        )

    @staticmethod
    def _configuraciones(
        repositorio: RepositorioRegistros,
        evaluacion: Mapping[str, Any],
        alcance: AlcanceInterpretabilidad,
    ) -> list[ConfiguracionCongelable]:
        """Las configuraciones a explicar según DP-11, todas congeladas e intactas (PI-13)."""
        congeladas = {
            g.contenido["configuracion"]["identificador"]: configuracion_desde_datos(
                g.contenido["configuracion"]
            )
            for g in repositorio.listar(TipoRegistro.CONGELAMIENTO)
        }
        huellas = configuraciones_congeladas(repositorio)
        evaluadas = list(evaluacion["configuracion"]["configuraciones"])
        no_congeladas = [i for i in evaluadas if i not in congeladas]
        if no_congeladas:
            raise ConfiguracionInvalida(
                f"Las configuraciones {', '.join(no_congeladas)} no están congeladas.",
                "Solo se explican configuraciones congeladas (PI-13).",
            )
        configuraciones = [congeladas[i] for i in evaluadas]
        if alcance is AlcanceInterpretabilidad.ESCENARIO_SUFICIENTE:
            regla = evaluacion["resultados"]["regla"]
            configuraciones = [
                c
                for c in configuraciones
                if c.rol.value == "seleccionada"
                and regla["estado"] == "escenario_suficiente"
                and c.escenario == regla["escenario"]
            ]
            if not configuraciones:
                raise ConfiguracionInvalida(
                    "La regla de suficiencia no eligió un escenario suficiente: con el "
                    "alcance escenario_suficiente no hay ninguna configuración que explicar.",
                    "Es un resultado posible, no un error del programa. El alcance es "
                    "una decisión del equipo (DP-11).",
                )
        for configuracion in configuraciones:
            if configuracion.huella().valor != huellas.get(configuracion.identificador):
                raise HuellaNoCoincide(configuracion.identificador)
        return configuraciones


def _contribuciones(pares: Sequence[tuple[str, float]]) -> tuple[ContribucionResumen, ...]:
    return tuple(ContribucionResumen(variable=v, valor=x) for v, x in pares)
