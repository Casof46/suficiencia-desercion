"""Registros de trazabilidad y filtro de identificadores, sin base de datos (H2.7)."""

from __future__ import annotations

import pytest

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.trazabilidad.filtro import (
    IdentificadorEnExportacion,
    columnas_identificadoras,
    exigir_sin_identificadores,
)
from suficiencia.domain.trazabilidad.registros import (
    HUELLA_INICIAL,
    Entorno,
    EstadoCorrida,
    ModoExperimento,
    RegistroAcceso,
    RegistroDecision,
    RegistroExperimento,
    RegistroGuardado,
    TipoRegistro,
    huella_encadenada,
    json_canonico,
    verificar_cadena,
)

ENTORNO = Entorno(
    python="3.12.0",
    sistema="Prueba",
    huella_bloqueo=None,
    commit=None,
    cambios_sin_commit=None,
    nucleos=1,
    hilos={},
    paquetes={},
)


def _experimento(**cambios: object) -> RegistroExperimento:
    campos: dict[str, object] = {
        "identificador": "EXP-1",
        "modo": ModoExperimento.EXPLORATORIO,
        "estado": EstadoCorrida.EXITOSA,
        "version_protocolo": None,
        "configuracion": {},
        "semillas": {"global": 1},
        "huella_datos": None,
        "entorno": ENTORNO,
    }
    campos.update(cambios)
    return RegistroExperimento(**campos)  # type: ignore[arg-type]


@pytest.mark.parametrize("codigo", ["DP16", "DP-1", "dp-16", "DP-16z", "REC-04"])
def test_una_decision_con_codigo_invalido_se_rechaza(codigo: str) -> None:
    with pytest.raises(ConfiguracionInvalida, match="no es un código de decisión"):
        RegistroDecision(codigo, "d", "j", "r")


@pytest.mark.parametrize("campo", ["decision", "justificacion", "responsable"])
def test_una_decision_sin_decision_justificacion_o_responsable_se_rechaza(campo: str) -> None:
    datos = {"decision": "d", "justificacion": "j", "responsable": "r", campo: "  "}
    with pytest.raises(ConfiguracionInvalida, match=campo):
        RegistroDecision("DP-16", **datos)


def test_un_experimento_confirmatorio_necesita_protocolo() -> None:
    with pytest.raises(ConfiguracionInvalida, match="versión del protocolo"):
        _experimento(modo=ModoExperimento.CONFIRMATORIO)
    assert _experimento(modo=ModoExperimento.CONFIRMATORIO, version_protocolo="v1")


def test_una_corrida_fallida_necesita_su_error() -> None:
    with pytest.raises(ConfiguracionInvalida, match="error"):
        _experimento(estado=EstadoCorrida.FALLIDA)


def test_las_semillas_son_enteros() -> None:
    with pytest.raises(ConfiguracionInvalida, match="semilla"):
        _experimento(semillas={"global": "1"})


def test_un_acceso_necesita_operacion_y_motivo() -> None:
    with pytest.raises(ConfiguracionInvalida, match="operacion"):
        RegistroAcceso(" ", "motivo", True)


def test_el_json_canonico_no_depende_del_orden_de_las_claves() -> None:
    assert (
        json_canonico({"b": 1, "a": "á"})
        == json_canonico({"a": "á", "b": 1})
        == ('{"a":"á","b":1}')
    )


def _cadena(n: int) -> list[RegistroGuardado]:
    registros = []
    anterior = HUELLA_INICIAL
    for numero in range(1, n + 1):
        contenido = {"n": numero}
        huella = huella_encadenada(anterior, "2026-01-01", json_canonico(contenido))
        registros.append(
            RegistroGuardado(
                TipoRegistro.DECISION, numero, "2026-01-01", contenido, anterior, huella
            )
        )
        anterior = huella
    return registros


def test_una_cadena_intacta_no_tiene_problemas() -> None:
    assert verificar_cadena(TipoRegistro.DECISION, _cadena(3)) == ()


def test_la_cadena_detecta_contenido_modificado_y_registros_faltantes() -> None:
    cadena = _cadena(4)
    modificado = cadena[1]
    cadena[1] = RegistroGuardado(
        modificado.tipo,
        modificado.numero,
        modificado.fecha,
        {"n": 99},
        modificado.huella_anterior,
        modificado.huella,
    )
    problemas = verificar_cadena(TipoRegistro.DECISION, cadena)
    assert [(p.numero, p.descripcion) for p in problemas] == [(2, "su contenido fue modificado")]

    sin_el_tercero = [r for r in _cadena(4) if r.numero != 3]
    descripciones = [p.descripcion for p in verificar_cadena(TipoRegistro.DECISION, sin_el_tercero)]
    assert "falta el registro n.º 3" in descripciones
    assert "no continúa la cadena de huellas" in descripciones


# Filtro de identificadores (PI-04) --------------------------------------------------


@pytest.mark.parametrize(
    "columna", ["codigo_estudiante", "DNI", "Nombre Completo", "correo", "e-mail", "telefono"]
)
def test_el_filtro_detecta_identificadores_conocidos(columna: str) -> None:
    if columna == "e-mail":
        assert columnas_identificadoras([columna]) == ()
        assert columnas_identificadoras([columna], ["e_mail"]) == (columna,)
        return
    assert columnas_identificadoras(["ciclo", columna]) == (columna,)


def test_el_filtro_usa_tambien_los_identificadores_del_diccionario() -> None:
    assert columnas_identificadoras(["matricula_id", "ciclo"], ["matricula_id"]) == (
        "matricula_id",
    )
    with pytest.raises(IdentificadorEnExportacion, match="matricula_id"):
        exigir_sin_identificadores(["matricula_id"], ["matricula_id"])
    exigir_sin_identificadores(["seudonimo", "ciclo", "fecha"])
