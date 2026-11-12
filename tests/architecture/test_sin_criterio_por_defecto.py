"""Criterio de aceptación de H2.6: ningún criterio, umbral ni procedimiento de
multiplicidad tiene valor por defecto, ni en el código ni en ``config/``.

El único protocolo del repositorio es el ejemplo ficticio de ``config/ejemplos/``,
que lo declara y que el programa no aprueba en el registro del proyecto.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest
import yaml

from suficiencia.application.contratos import (
    SolicitudCongelar,
    SolicitudGuardarBorrador,
    SolicitudVerificarEvaluacionFinal,
)
from suficiencia.domain.evaluacion.congelamiento import ConfiguracionCongelable
from suficiencia.domain.evaluacion.protocolo import ContenidoProtocolo
from suficiencia.domain.evaluacion.suficiencia import (
    PROCEDIMIENTOS_IMPLEMENTADOS,
    Condicion,
    CriterioSuficiencia,
    Estimacion,
    Metrica,
    ResultadoEscenario,
)


def test_no_hay_procedimientos_de_multiplicidad_implementados() -> None:
    assert dict(PROCEDIMIENTOS_IMPLEMENTADOS) == {}


@pytest.mark.parametrize(
    "clase",
    [
        Metrica,
        Condicion,
        CriterioSuficiencia,
        ContenidoProtocolo,
        ConfiguracionCongelable,
        Estimacion,
        ResultadoEscenario,
    ],
)
def test_ningun_campo_del_criterio_ni_de_la_configuracion_tiene_valor_por_omision(
    clase: type,
) -> None:
    con_valor = [
        campo.name
        for campo in dataclasses.fields(clase)
        if campo.default is not dataclasses.MISSING
        or campo.default_factory is not dataclasses.MISSING
    ]
    assert con_valor == []


@pytest.mark.parametrize(
    ("contrato", "campo"),
    [
        (SolicitudGuardarBorrador, "archivo"),
        (SolicitudCongelar, "archivo"),
        (SolicitudVerificarEvaluacionFinal, "archivos"),
    ],
)
def test_no_hay_archivo_de_protocolo_ni_de_configuracion_por_omision(
    contrato: type[SolicitudGuardarBorrador], campo: str
) -> None:
    assert contrato.model_fields[campo].is_required()


def test_el_dominio_de_evaluacion_no_contiene_numeros_decimales(raiz: Path) -> None:
    """Un umbral escrito en el código sería un número decimal; el dominio no tiene ninguno."""
    encontrados = []
    for archivo in sorted((raiz / "src" / "suficiencia" / "domain" / "evaluacion").glob("*.py")):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Constant) and isinstance(nodo.value, float):
                encontrados.append(f"{archivo.name}:{nodo.lineno} = {nodo.value}")
    assert encontrados == []


def test_los_unicos_protocolos_en_config_son_los_ejemplos_ficticios(raiz: Path) -> None:
    protocolos = []
    for archivo in sorted((raiz / "config").rglob("*.yaml")):
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
        if isinstance(datos, dict) and "criterio_suficiencia" in datos:
            protocolos.append(archivo.relative_to(raiz).as_posix())
            assert datos["ficticio"] is True, archivo
            assert "EJEMPLO FICTICIO" in archivo.read_text(encoding="utf-8"), archivo
    assert protocolos == [
        "config/ejemplos/protocolo_evaluacion_final_ficticio.yaml",  # demostración de F3.4
        "config/ejemplos/protocolo_ficticio.yaml",
    ]
