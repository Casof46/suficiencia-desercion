"""Errores del dominio (RNF-15) y huella SHA-256 (RNF-16). Hito H2.1."""

from __future__ import annotations

import pytest

from suficiencia.domain.errores import (
    CasoDeUsoNoDisponible,
    ConfiguracionInvalida,
    DecisionPendiente,
    ErrorSuficiencia,
    HuellaInvalida,
)
from suficiencia.domain.huella import Huella


def test_todo_error_lleva_causa_y_accion_sugerida() -> None:
    error = ConfiguracionInvalida("Falta la sección 'rutas'.", "Añádala al archivo.")
    assert str(error) == "Falta la sección 'rutas'. Acción sugerida: Añádala al archivo."
    assert isinstance(error, ErrorSuficiencia)


@pytest.mark.parametrize(("causa", "accion"), [("", "Haga algo."), ("Algo falló.", "  ")])
def test_un_error_sin_causa_o_sin_accion_se_rechaza(causa: str, accion: str) -> None:
    with pytest.raises(ValueError, match="causa y acción"):
        ErrorSuficiencia(causa, accion)


def test_decision_pendiente_nombra_la_decision_y_no_supone_un_valor() -> None:
    error = DecisionPendiente("DP-01d", "la fecha índice de la ventana T1")
    assert error.decision == "DP-01d"
    assert "DP-01d" in error.causa
    assert "la fecha índice de la ventana T1" in error.causa
    assert "DP-01d" in error.accion


@pytest.mark.parametrize("codigo", ["DP-1", "dp-01", "DP-01z", "REC-04", ""])
def test_decision_pendiente_rechaza_codigos_invalidos(codigo: str) -> None:
    with pytest.raises(ValueError, match="decisión"):
        DecisionPendiente(codigo, "algo")


def test_caso_de_uso_no_disponible_indica_el_hito() -> None:
    error = CasoDeUsoNoDisponible("CU-03", "H2.4")
    assert error.caso == "CU-03"
    assert "CU-03" in str(error)
    assert "H2.4" in str(error)


def test_caso_de_uso_no_disponible_rechaza_codigos_invalidos() -> None:
    with pytest.raises(ValueError, match="caso de uso"):
        CasoDeUsoNoDisponible("CU-3", "H2.4")


def test_huella_de_un_vector_conocido() -> None:
    """Vector de prueba de SHA-256 (FIPS 180-2): "abc"."""
    huella = Huella.de_bytes(b"abc")
    assert huella.valor == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert str(huella) == huella.valor


def test_misma_entrada_misma_huella_y_distinta_entrada_distinta_huella() -> None:
    assert Huella.de_bytes(b"datos") == Huella.de_bytes(b"datos")
    assert Huella.de_bytes(b"datos") != Huella.de_bytes(b"datos ")


@pytest.mark.parametrize(
    "valor",
    [
        "",
        "abc",
        "BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD",
        "g" * 64,
        "a" * 63,
        "a" * 65,
    ],
)
def test_huella_rechaza_valores_invalidos(valor: str) -> None:
    with pytest.raises(HuellaInvalida, match="no es una huella SHA-256"):
        Huella(valor)
