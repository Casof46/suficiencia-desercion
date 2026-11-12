"""Protocolo, desviaciones y congelamiento a través de los servicios y la línea de comandos (H2.6).

Todo ocurre en un proyecto temporal. Los protocolos y configuraciones son EJEMPLOS
FICTICIOS; donde una prueba necesita un protocolo "no ficticio" para recorrer el
camino real de aprobación, sus decisiones se registran como valores de prueba en
el registro temporal.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from fixtures.protocolo_de_prueba import (
    ARCHIVO_PROTOCOLO_FICTICIO,
    aprobar_protocolo_ficticio,
    datos_protocolo_ficticio,
)
from suficiencia.application.composicion import Servicios, crear_servicios
from suficiencia.application.contratos import (
    SolicitudAprobarProtocolo,
    SolicitudCongelar,
    SolicitudGuardarBorrador,
    SolicitudRegistrarDecision,
    SolicitudVerificarEvaluacionFinal,
)
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.application.servicio_protocolo import ProtocoloFicticioNoAprobable
from suficiencia.cli import SALIDA_CORRECTA, SALIDA_ERROR, main
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.evaluacion.congelamiento import HuellaNoCoincide
from suficiencia.domain.evaluacion.protocolo import (
    DECISIONES_DEL_PROTOCOLO,
    DesviacionRequerida,
    ProtocoloInmutable,
    SinProtocoloVigente,
)
from suficiencia.domain.trazabilidad.registros import ModoExperimento, TipoRegistro
from suficiencia.persistence.entorno import CapturadorEntornoLocal
from suficiencia.persistence.repositorio_sqlite import RepositorioSqlite


@pytest.fixture
def proyecto(tmp_path: Path, raiz: Path) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(raiz / "config" / "proyecto.yaml", tmp_path / "config" / "proyecto.yaml")
    shutil.copy(raiz / "requirements.lock", tmp_path / "requirements.lock")
    return tmp_path


def _registro(proyecto: Path) -> RepositorioSqlite:
    return RepositorioSqlite(proyecto / "workspace" / "registro.sqlite")


def _escribir(carpeta: Path, nombre: str, datos: dict[str, Any]) -> Path:
    archivo = carpeta / nombre
    archivo.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return archivo


def _protocolo_de_prueba(proyecto: Path, limite: float = 0.7) -> Path:
    """Protocolo marcado como no ficticio para recorrer el camino real, solo en la carpeta
    temporal. Sus valores siguen siendo inventados."""
    datos = datos_protocolo_ficticio()
    datos["ficticio"] = False
    datos["criterio_suficiencia"]["condiciones"][0]["limite"] = limite
    return _escribir(proyecto, f"protocolo_prueba_{limite}.yaml", datos)


def _registrar_decisiones(servicios: Servicios) -> None:
    for codigo in DECISIONES_DEL_PROTOCOLO:
        servicios.reportes.registrar_decision(
            SolicitudRegistrarDecision(
                codigo=codigo,
                decision="Valor de prueba (EJEMPLO FICTICIO) en una carpeta temporal",
                justificacion="Prueba automática de H2.6",
                responsable="pruebas",
            )
        )


def _configuracion(version: int, umbral: float = 0.5) -> dict[str, Any]:
    return {
        "identificador": "CFG-1",
        "rol": "seleccionada",
        "escenario": "T1-A",
        "algoritmo": "algoritmo_ficticio",
        "hiperparametros": {"parametro_ficticio": 1},
        "preprocesamiento": {"paso_ficticio": "ninguno"},
        "variables": ["v1", "v2"],
        "umbral": umbral,
        "calibracion": {"metodo": "ninguna (ficticio)"},
        "semilla": 3,
        "datos_reentrenamiento": "indices_ficticios",
        "version_protocolo": version,
        "ficticio": True,
    }


def test_un_protocolo_ficticio_se_guarda_pero_nunca_se_aprueba(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    borrador = servicios.protocolo.guardar_borrador(
        SolicitudGuardarBorrador(archivo=ARCHIVO_PROTOCOLO_FICTICIO)
    )
    assert borrador.version == 1
    assert borrador.ficticio
    assert borrador.decisiones_faltantes == ()
    with pytest.raises(ProtocoloFicticioNoAprobable):
        servicios.protocolo.aprobar(
            SolicitudAprobarProtocolo(version=1, huella=borrador.huella, responsable="Equipo")
        )
    consulta = servicios.protocolo.consultar()
    assert consulta.vigente is None
    assert [v.estado for v in consulta.versiones] == ["borrador"]


def test_aprobar_un_protocolo_real_exige_las_decisiones_registradas(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    borrador = servicios.protocolo.guardar_borrador(
        SolicitudGuardarBorrador(archivo=_protocolo_de_prueba(proyecto))
    )
    solicitud = SolicitudAprobarProtocolo(version=1, huella=borrador.huella, responsable="Equipo")
    with pytest.raises(DecisionPendiente) as error:
        servicios.protocolo.aprobar(solicitud)
    assert error.value.decision == "DP-06"
    _registrar_decisiones(servicios)
    aprobacion = servicios.protocolo.aprobar(solicitud)
    assert aprobacion.version == 1
    assert aprobacion.version_reemplazada is None
    assert not aprobacion.desviacion_registrada
    assert servicios.protocolo.consultar().vigente == 1


def test_pu05_y_pu06_por_el_servicio_con_experimentos_confirmatorios(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    registrador = RegistradorCorridas(_registro(proyecto), CapturadorEntornoLocal(proyecto))
    comunes: dict[str, Any] = {
        "configuracion": {"simulacion": True},
        "semillas": {"global": 1},
        "huella_datos": None,
    }
    ejecutadas: list[str] = []

    def corrida() -> dict[str, Any]:
        ejecutadas.append("si")
        return {}

    # PU-05: sin protocolo aprobado, la corrida confirmatoria se rechaza y no se ejecuta.
    with pytest.raises(SinProtocoloVigente):
        registrador.ejecutar(
            corrida, modo=ModoExperimento.CONFIRMATORIO, version_protocolo="1", **comunes
        )
    assert ejecutadas == []
    assert _registro(proyecto).listar(TipoRegistro.EXPERIMENTO) == []
    # El modo exploratorio no lo necesita.
    registrador.ejecutar(
        corrida, modo=ModoExperimento.EXPLORATORIO, version_protocolo=None, **comunes
    )

    _registrar_decisiones(servicios)
    primera = servicios.protocolo.guardar_borrador(
        SolicitudGuardarBorrador(archivo=_protocolo_de_prueba(proyecto))
    )
    servicios.protocolo.aprobar(
        SolicitudAprobarProtocolo(version=1, huella=primera.huella, responsable="Equipo")
    )
    confirmatoria = registrador.ejecutar(
        corrida, modo=ModoExperimento.CONFIRMATORIO, version_protocolo="1", **comunes
    )
    identificador = confirmatoria.contenido["identificador"]

    # PU-06: la versión aprobada no se edita; el cambio es una versión nueva.
    with pytest.raises(ProtocoloInmutable):
        servicios.protocolo.guardar_borrador(
            SolicitudGuardarBorrador(archivo=_protocolo_de_prueba(proyecto, 0.6), version=1)
        )
    segunda = servicios.protocolo.guardar_borrador(
        SolicitudGuardarBorrador(archivo=_protocolo_de_prueba(proyecto, 0.6))
    )
    assert segunda.version == 2
    with pytest.raises(DesviacionRequerida):
        servicios.protocolo.aprobar(
            SolicitudAprobarProtocolo(version=2, huella=segunda.huella, responsable="Equipo")
        )
    aprobacion = servicios.protocolo.aprobar(
        SolicitudAprobarProtocolo(
            version=2,
            huella=segunda.huella,
            responsable="Equipo",
            desviacion="Se cambia el límite (prueba)",
            justificacion="Prueba automática",
        )
    )
    assert aprobacion.version_reemplazada == 1
    assert aprobacion.resultados_afectados == (identificador,)
    consulta = servicios.protocolo.consultar()
    assert [(v.numero, v.estado) for v in consulta.versiones] == [
        (1, "reemplazado"),
        (2, "aprobado"),
    ]
    assert consulta.desviaciones[0].resultados_afectados == (identificador,)
    # La versión reemplazada ya no vale para corridas confirmatorias.
    with pytest.raises(SinProtocoloVigente):
        registrador.ejecutar(
            corrida, modo=ModoExperimento.CONFIRMATORIO, version_protocolo="1", **comunes
        )
    assert servicios.reportes.verificar().correcto


def test_pi09_congelar_y_verificar_por_los_servicios(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    original = _escribir(proyecto, "configuracion.yaml", _configuracion(1))
    # PU-05: sin protocolo no se congela ni se prepara la evaluación final.
    with pytest.raises(SinProtocoloVigente):
        servicios.experimentos.congelar(SolicitudCongelar(archivo=original))
    with pytest.raises(SinProtocoloVigente):
        servicios.evaluacion_final.verificar_precondiciones(
            SolicitudVerificarEvaluacionFinal(archivos=(original,))
        )
    aprobar_protocolo_ficticio(_registro(proyecto))
    congelada = servicios.experimentos.congelar(
        SolicitudCongelar(archivo=Path("configuracion.yaml"))
    )
    assert congelada.version_protocolo == 1
    assert congelada.ficticio
    verificacion = servicios.evaluacion_final.verificar_precondiciones(
        SolicitudVerificarEvaluacionFinal(archivos=(original,))
    )
    assert verificacion.configuraciones == {"CFG-1": congelada.huella}
    assert verificacion.ficticio
    alterada = _escribir(proyecto, "alterada.yaml", _configuracion(1, umbral=0.45))
    with pytest.raises(HuellaNoCoincide):
        servicios.evaluacion_final.verificar_precondiciones(
            SolicitudVerificarEvaluacionFinal(archivos=(alterada,))
        )
    # Verificar no abre la prueba: no hay ningún acceso registrado.
    assert _registro(proyecto).listar(TipoRegistro.ACCESO) == []


def test_la_demostracion_no_escribe_en_el_registro_del_proyecto(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    resultado = servicios.protocolo.demostracion(ARCHIVO_PROTOCOLO_FICTICIO)
    assert [c.estado for c in resultado.casos] == [
        "escenario_suficiente",
        "ningun_escenario_cumple",
        "empate_sin_resolver",
    ]
    assert resultado.casos[0].escenario == "T1-AF"
    assert all("no se esperaba" not in p.resultado for p in resultado.pasos)
    assert sum(p.resultado.startswith("Rechazado") for p in resultado.pasos) == 5
    assert not (proyecto / "workspace" / "registro.sqlite").exists()


def test_la_demostracion_solo_acepta_protocolos_ficticios(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    with pytest.raises(ConfiguracionInvalida, match="no está marcado como ejemplo ficticio"):
        servicios.protocolo.demostracion(_protocolo_de_prueba(proyecto))


def test_linea_de_comandos_del_protocolo(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def correr(*argumentos: str) -> tuple[int, str, str]:
        codigo = main(["--raiz", str(proyecto), *argumentos])
        salida = capsys.readouterr()
        return codigo, salida.out, salida.err

    codigo, salida, _ = correr("protocolo", "ver")
    assert codigo == SALIDA_CORRECTA
    assert "No hay ninguna versión del protocolo" in salida
    codigo, salida, _ = correr("protocolo", "borrador", str(ARCHIVO_PROTOCOLO_FICTICIO))
    assert codigo == SALIDA_CORRECTA
    assert "versión 1 [EJEMPLO FICTICIO" in salida
    huella = salida.split("Huella: ")[1].split()[0]
    codigo, _, error = correr(
        "protocolo", "aprobar", "1", "--huella", huella, "--responsable", "Equipo"
    )
    assert codigo == SALIDA_ERROR
    assert "ejemplo ficticio" in error
    codigo, salida, _ = correr("protocolo", "ver")
    assert "Versión 1: borrador  [EJEMPLO FICTICIO]" in salida
    assert "Versión vigente: ninguna" in salida
    codigo, salida, _ = correr("registro", "ver", "protocolos")
    assert codigo == SALIDA_CORRECTA
    assert "borrador de la versión 1" in salida
    codigo, _, error = correr(
        "protocolo",
        "aprobar",
        "1",
        "--huella",
        huella,
        "--responsable",
        "Equipo",
        "--desviacion",
        "solo descripción",
    )
    assert codigo == SALIDA_ERROR
    assert "descripción y justificación" in error
    codigo, salida, _ = correr(
        "protocolo", "demostracion", "--protocolo", str(ARCHIVO_PROTOCOLO_FICTICIO)
    )
    assert codigo == SALIDA_CORRECTA
    assert "DEMOSTRACIÓN: protocolo FICTICIO" in salida
    assert "ningun_escenario_cumple" in salida
