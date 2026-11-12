"""Protocolo versionado, desviaciones y congelamiento (H2.6): PU-05, PU-06 y PI-09.

El protocolo y las configuraciones de este archivo son EJEMPLOS FICTICIOS.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from fixtures.protocolo_de_prueba import (
    PROCEDIMIENTOS_FICTICIOS,
    contenido_ficticio,
    datos_protocolo_ficticio,
)
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.congelamiento import (
    ConfiguracionCongelable,
    HuellaNoCoincide,
    RolConfiguracion,
    configuracion_desde_datos,
    congelar,
    preparar_evaluacion_final,
)
from suficiencia.domain.evaluacion.protocolo import (
    DECISIONES_DEL_PROTOCOLO,
    ContenidoProtocolo,
    DatosDesviacion,
    DesviacionRequerida,
    EstadoProtocolo,
    HistorialProtocolo,
    ProtocoloInmutable,
    SinProtocoloVigente,
    aprobar,
    contenido_desde_datos,
    evaluar_suficiencia,
    exigir_vigente,
    guardar_borrador,
    resultados_afectados,
)
from suficiencia.domain.evaluacion.suficiencia import Estimacion, ResultadoEscenario
from suficiencia.domain.trazabilidad.registros import ModoExperimento


class _Registro:
    """Registro en memoria: guarda el contenido de cada registro de protocolo, en orden."""

    def __init__(self) -> None:
        self.protocolo: list[dict[str, Any]] = []
        self.desviaciones: list[dict[str, Any]] = []

    def historial(self) -> HistorialProtocolo:
        return HistorialProtocolo.desde_registros(self.protocolo)

    def borrador(self, contenido: ContenidoProtocolo, version: int | None = None) -> int:
        registro = guardar_borrador(self.historial(), contenido, version)
        self.protocolo.append(registro.contenido())
        return registro.version

    def aprobar(
        self,
        version: int,
        confirmatorios: tuple[str, ...] = (),
        desviacion: DatosDesviacion | None = None,
        huella: str | None = None,
    ) -> None:
        historial = self.historial()
        resultado = aprobar(
            historial,
            version,
            huella or historial.version(version).huella.valor,
            "Equipo (prueba)",
            confirmatorios,
            desviacion,
        )
        if resultado.desviacion:
            self.desviaciones.append(resultado.desviacion.contenido())
        self.protocolo.append(resultado.aprobacion.contenido())


def _otro_contenido() -> ContenidoProtocolo:
    datos = datos_protocolo_ficticio()
    datos["criterio_suficiencia"]["condiciones"][0]["limite"] = 0.6
    return contenido_desde_datos(datos)


# PU-06: un protocolo aprobado no se modifica ----------------------------------------


def test_pu06_una_version_aprobada_no_puede_editarse() -> None:
    registro = _Registro()
    version = registro.borrador(contenido_ficticio())
    registro.aprobar(version)
    with pytest.raises(ProtocoloInmutable, match="no puede"):
        guardar_borrador(registro.historial(), _otro_contenido(), version)
    with pytest.raises(ProtocoloInmutable):
        registro.aprobar(version)


def test_pu06_un_cambio_crea_una_version_nueva_y_una_desviacion() -> None:
    registro = _Registro()
    registro.aprobar(registro.borrador(contenido_ficticio()))
    nueva = registro.borrador(_otro_contenido())
    assert nueva == 2
    # Mientras la nueva está en borrador, la vigente sigue siendo la 1.
    vigente = registro.historial().vigente()
    assert vigente is not None
    assert vigente.numero == 1
    with pytest.raises(DesviacionRequerida):
        registro.aprobar(nueva, confirmatorios=("EXP-1", "EXP-2"))
    registro.aprobar(
        nueva,
        confirmatorios=("EXP-2", "EXP-1"),
        desviacion=DatosDesviacion("Se baja el límite (ficticio)", "Justificación ficticia"),
    )
    estados = [(v.numero, v.estado) for v in registro.historial().versiones]
    assert estados == [(1, EstadoProtocolo.REEMPLAZADO), (2, EstadoProtocolo.APROBADO)]
    assert registro.desviaciones == [
        {
            "version_anterior": 1,
            "version_nueva": 2,
            "descripcion": "Se baja el límite (ficticio)",
            "justificacion": "Justificación ficticia",
            "responsable": "Equipo (prueba)",
            "resultados_afectados": ["EXP-1", "EXP-2"],
        }
    ]
    assert resultados_afectados(registro.desviaciones) == {"EXP-1", "EXP-2"}


def test_un_borrador_si_puede_editarse_y_cambia_su_huella() -> None:
    registro = _Registro()
    version = registro.borrador(contenido_ficticio())
    huella_inicial = registro.historial().version(version).huella
    assert registro.borrador(_otro_contenido(), version) == version
    assert registro.borrador(contenido_ficticio()) == version  # sin número: la última en borrador
    assert len(registro.historial().versiones) == 1
    assert registro.historial().version(version).huella == huella_inicial


def test_solo_se_aprueba_lo_revisado() -> None:
    registro = _Registro()
    version = registro.borrador(contenido_ficticio())
    revisada = registro.historial().version(version).huella.valor
    registro.borrador(_otro_contenido(), version)  # el borrador cambia después de revisarlo
    with pytest.raises(ConfiguracionInvalida, match="huella revisada"):
        registro.aprobar(version, huella=revisada)


def test_aprobar_exige_lo_decidido_en_cada_decision_previa_a_cu05() -> None:
    datos = datos_protocolo_ficticio()
    del datos["decisiones"]["DP-10"]
    registro = _Registro()
    version = registro.borrador(contenido_desde_datos(datos))
    with pytest.raises(DecisionPendiente) as error:
        registro.aprobar(version)
    assert error.value.decision == "DP-10"
    assert DECISIONES_DEL_PROTOCOLO == (
        "DP-06",
        "DP-07",
        "DP-08",
        "DP-09",
        "DP-10",
        "DP-12",
        "DP-17",
        "DP-19",
        "DP-20",
    )


def test_solo_se_aprueba_la_ultima_version() -> None:
    registro = _Registro()
    registro.aprobar(registro.borrador(contenido_ficticio()))
    registro.borrador(_otro_contenido())
    with pytest.raises(ProtocoloInmutable):
        registro.aprobar(1)


def test_la_huella_no_depende_del_orden_de_las_decisiones() -> None:
    datos = datos_protocolo_ficticio()
    invertido = dict(datos)
    invertido["decisiones"] = dict(reversed(list(datos["decisiones"].items())))
    assert contenido_desde_datos(datos).huella() == contenido_desde_datos(invertido).huella()
    assert contenido_desde_datos(datos).huella() != _otro_contenido().huella()


# Reconstrucción desde el registro ------------------------------------------------


def test_una_secuencia_alterada_se_detecta() -> None:
    registro = _Registro()
    registro.aprobar(registro.borrador(contenido_ficticio()))
    borrador_tardio = dict(registro.protocolo[0])
    with pytest.raises(ConfiguracionInvalida, match="después de aprobarla"):
        HistorialProtocolo.desde_registros([*registro.protocolo, borrador_tardio])
    alterado = dict(registro.protocolo[0])
    alterado["protocolo"] = _otro_contenido().a_datos()
    with pytest.raises(ConfiguracionInvalida, match="no coincide"):
        HistorialProtocolo.desde_registros([alterado])
    with pytest.raises(ConfiguracionInvalida, match="no tiene borrador"):
        HistorialProtocolo.desde_registros([registro.protocolo[1]])


def test_el_contenido_ficticio_se_declara() -> None:
    assert contenido_ficticio().ficticio is True
    with pytest.raises(ConfiguracionInvalida, match="faltan"):
        contenido_desde_datos({"criterio_suficiencia": {}, "decisiones": {}})
    datos = datos_protocolo_ficticio()
    datos["criterio_suficiencia"] = None
    with pytest.raises(DecisionPendiente) as error:
        contenido_desde_datos(datos)
    assert error.value.decision == "DP-08"
    datos = datos_protocolo_ficticio()
    datos["decisiones"] = {"DP-6": "x"}
    with pytest.raises(ConfiguracionInvalida, match="código de decisión"):
        contenido_desde_datos(datos)


# PU-05: sin protocolo aprobado vigente no hay operación confirmatoria ----------------


def _uno() -> list[ResultadoEscenario]:
    estimacion = Estimacion(0.8, 0.75, 0.85)
    diferencia = Estimacion(0.0, -0.01, 0.01)
    return [
        ResultadoEscenario(
            "T1-A",
            "A",
            1,
            1,
            {"metrica_a": estimacion},
            {("metrica_a", "comparador_ficticio"): {"referencia": diferencia}},
        )
    ]


def test_pu05_sin_protocolo_aprobado_se_rechaza_lo_confirmatorio() -> None:
    registro = _Registro()
    with pytest.raises(SinProtocoloVigente, match="ninguna versión aprobada"):
        exigir_vigente(registro.historial(), None, "Un experimento confirmatorio")
    version = registro.borrador(contenido_ficticio())
    with pytest.raises(SinProtocoloVigente):
        exigir_vigente(registro.historial(), str(version), "Un experimento confirmatorio")
    with pytest.raises(SinProtocoloVigente):
        evaluar_suficiencia(
            registro.historial(),
            version,
            ModoExperimento.CONFIRMATORIO,
            _uno(),
            PROCEDIMIENTOS_FICTICIOS,
        )
    with pytest.raises(SinProtocoloVigente):
        preparar_evaluacion_final(registro.historial(), [_configuracion(version)], {})


def test_pu05_una_version_reemplazada_ya_no_vale_para_lo_confirmatorio() -> None:
    registro = _Registro()
    registro.aprobar(registro.borrador(contenido_ficticio()))
    registro.aprobar(registro.borrador(_otro_contenido()))
    with pytest.raises(SinProtocoloVigente, match="la vigente es la 2"):
        exigir_vigente(registro.historial(), "1", "Un experimento confirmatorio")
    assert exigir_vigente(registro.historial(), "2", "Un experimento confirmatorio").numero == 2


def test_en_modo_exploratorio_un_borrador_basta_y_queda_marcado() -> None:
    registro = _Registro()
    version = registro.borrador(contenido_ficticio())
    exploratoria = evaluar_suficiencia(
        registro.historial(),
        version,
        ModoExperimento.EXPLORATORIO,
        _uno(),
        PROCEDIMIENTOS_FICTICIOS,
    )
    assert exploratoria.modo is ModoExperimento.EXPLORATORIO
    assert exploratoria.estado_protocolo is EstadoProtocolo.BORRADOR
    assert exploratoria.ficticio is True
    registro.aprobar(version)
    confirmatoria = evaluar_suficiencia(
        registro.historial(),
        version,
        ModoExperimento.CONFIRMATORIO,
        _uno(),
        PROCEDIMIENTOS_FICTICIOS,
    )
    assert confirmatoria.estado_protocolo is EstadoProtocolo.APROBADO
    assert confirmatoria.resultado.escenario == "T1-A"


# Congelamiento y PI-09 ------------------------------------------------------------


def _configuracion(version: int, **cambios: Any) -> ConfiguracionCongelable:
    base = ConfiguracionCongelable(
        identificador="CFG-1",
        rol=RolConfiguracion.SELECCIONADA,
        escenario="T1-A",
        algoritmo="algoritmo_ficticio",
        hiperparametros={"profundidad_ficticia": 3},
        preprocesamiento={"escalado": "ninguno"},
        variables=("v1", "v2"),
        umbral=0.5,
        calibracion={"metodo": "ninguna (ficticio)"},
        semilla=7,
        datos_reentrenamiento="indices_ficticios",
        version_protocolo=version,
        ficticio=True,
    )
    return dataclasses.replace(base, **cambios)


def _aprobado() -> tuple[_Registro, int]:
    registro = _Registro()
    version = registro.borrador(contenido_ficticio())
    registro.aprobar(version)
    return registro, version


def test_congelar_exige_protocolo_vigente_y_no_repite_identificadores() -> None:
    registro = _Registro()
    with pytest.raises(SinProtocoloVigente):
        congelar(_configuracion(1), registro.historial(), {})
    registro, version = _aprobado()
    congelada = congelar(_configuracion(version), registro.historial(), {})
    assert congelada.huella == _configuracion(version).huella().valor
    with pytest.raises(ConfiguracionInvalida, match="ya está congelada"):
        congelar(_configuracion(version), registro.historial(), {"CFG-1": congelada.huella})
    with pytest.raises(SinProtocoloVigente):
        congelar(_configuracion(version + 1), registro.historial(), {})


@pytest.mark.parametrize(
    "cambio",
    [
        {"algoritmo": "otro_algoritmo"},
        {"hiperparametros": {"profundidad_ficticia": 4}},
        {"preprocesamiento": {"escalado": "estandar"}},
        {"variables": ("v1", "v2", "v3")},
        {"umbral": 0.4},
        {"calibracion": {"metodo": "otra"}},
        {"semilla": 8},
        {"datos_reentrenamiento": "otros_indices"},
        {"escenario": "T2-A"},
        {"rol": RolConfiguracion.CONTROL},
    ],
)
def test_pi09_la_evaluacion_final_rechaza_una_huella_distinta(cambio: dict[str, Any]) -> None:
    registro, version = _aprobado()
    original = _configuracion(version)
    congeladas = {"CFG-1": congelar(original, registro.historial(), {}).huella}
    preparacion = preparar_evaluacion_final(registro.historial(), [original], congeladas)
    assert preparacion.configuraciones == (("CFG-1", original.huella().valor),)
    assert preparacion.ficticio is True
    with pytest.raises(HuellaNoCoincide, match="CFG-1"):
        preparar_evaluacion_final(
            registro.historial(), [_configuracion(version, **cambio)], congeladas
        )


def test_la_evaluacion_final_rechaza_lo_no_congelado_y_las_listas_vacias() -> None:
    registro, version = _aprobado()
    with pytest.raises(ConfiguracionInvalida, match="no está congelada"):
        preparar_evaluacion_final(registro.historial(), [_configuracion(version)], {})
    with pytest.raises(ConfiguracionInvalida, match="no recibió"):
        preparar_evaluacion_final(registro.historial(), [], {})


def test_una_configuracion_sin_todos_sus_campos_no_se_congela() -> None:
    datos = _configuracion(1).a_datos()
    assert configuracion_desde_datos(datos) == _configuracion(1)
    for campo in ("umbral", "calibracion", "semilla", "datos_reentrenamiento"):
        incompleta = dict(datos)
        del incompleta[campo]
        with pytest.raises(ConfiguracionInvalida, match=campo):
            configuracion_desde_datos(incompleta)
        nula = dict(datos)
        nula[campo] = None
        with pytest.raises(ConfiguracionInvalida, match="no tienen valor"):
            configuracion_desde_datos(nula)
    with pytest.raises(ConfiguracionInvalida, match="repite"):
        _configuracion(1, variables=("v1", "v1"))
    with pytest.raises(ConfiguracionInvalida, match="rol"):
        configuracion_desde_datos({**datos, "rol": "favorita"})
