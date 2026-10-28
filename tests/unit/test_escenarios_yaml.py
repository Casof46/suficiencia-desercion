"""Lectura de config/escenarios.yaml y de archivos de variables (H2.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.persistence.escenarios_yaml import (
    FuenteVariablesYaml,
    cargar_catalogo,
    cargar_variables,
)

CATALOGO_FICTICIO = """\
version_escenarios: 1
ficticio: true
bloques: {A: Académico, F: Financiero, S: Socioeconómico, B: Conductual}
conjuntos: [A, A+F, A+S, A+B, A+F+S, A+F+B, A+S+B, A+F+S+B]
fechas_indice: {T0: "F0", T1: "F1", T2: "F2", T3: "F3"}
"""

VARIABLES_FICTICIAS = """\
version_variables: 1
ficticio: true
variables:
  - {nombre: a, bloque: A, ventana_minima: T0}
  - {nombre: b, bloque: B, ventana_minima: T1}
"""


def _archivo(tmp_path: Path, contenido: str) -> Path:
    archivo = tmp_path / "archivo.yaml"
    archivo.write_text(contenido, encoding="utf-8")
    return archivo


def test_la_configuracion_del_repositorio_deja_pendientes_las_fechas_indice(raiz: Path) -> None:
    """DP-01d sigue abierta: el repositorio no trae fechas índice."""
    with pytest.raises(DecisionPendiente) as error:
        cargar_catalogo(raiz / "config" / "escenarios.yaml")
    assert error.value.decision == "DP-01d"


def test_los_ejemplos_del_repositorio_se_leen_y_se_declaran_ficticios(raiz: Path) -> None:
    catalogo = cargar_catalogo(raiz / "config" / "ejemplos" / "escenarios_ficticio.yaml")
    variables = cargar_variables(raiz / "config" / "ejemplos" / "variables_ficticias.yaml")
    assert catalogo.ficticio
    assert variables.ficticio
    assert all("FICTICIA" in v.fecha_indice for v in catalogo.catalogo.ventanas)
    assert all("ficticia" in v.nombre for v in variables.variables)


def test_un_catalogo_y_unas_variables_validos_se_leen(tmp_path: Path) -> None:
    catalogo = cargar_catalogo(_archivo(tmp_path, CATALOGO_FICTICIO))
    assert [v.fecha_indice for v in catalogo.catalogo.ventanas] == ["F0", "F1", "F2", "F3"]
    variables = cargar_variables(_archivo(tmp_path, VARIABLES_FICTICIAS))
    assert [(v.nombre, v.bloque.value, v.ventana_minima) for v in variables.variables] == [
        ("a", "A", "T0"),
        ("b", "B", "T1"),
    ]


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        (("ficticio: true", "ficticio: si"), "'ficticio' debe ser true o false"),
        (("version_escenarios: 1", "version_escenarios: 2"), "version_escenarios"),
        (("B: Conductual", "B: Comportamiento"), "los bloques deben ser exactamente"),
        (("A+F+S+B]", "A+F+S+B, F]"), "los conjuntos deben ser exactamente"),
        (('T3: "F3"', 'T4: "F3"'), "T0, T1, T2 y T3 en ese orden"),
        (('{T0: "F0", T1: "F1"', '{T1: "F1", T0: "F0"'), "T0, T1, T2 y T3 en ese orden"),
        (('T2: "F2"', "T2: 5"), "la fecha índice de T2 debe ser un texto o null"),
        (("ficticio: true", "ficticio: true\nextra: 1"), "claves desconocidas"),
    ],
)
def test_un_catalogo_invalido_se_rechaza_en_espanol(
    tmp_path: Path, cambio: tuple[str, str], mensaje: str
) -> None:
    contenido = CATALOGO_FICTICIO.replace(*cambio)
    assert contenido != CATALOGO_FICTICIO
    with pytest.raises(ConfiguracionInvalida, match=mensaje) as error:
        cargar_catalogo(_archivo(tmp_path, contenido))
    assert "Acción sugerida" in str(error.value)


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        (("bloque: B", "bloque: X"), "El bloque 'X' no existe"),
        (("ventana_minima: T1", "ventana_minima: T5"), "La ventana 'T5' no existe"),
        (("nombre: b", "nombre: a"), "Variables repetidas: a"),
        (("nombre: b, ", ""), "exactamente nombre, bloque y ventana_minima"),
        (("ventana_minima: T1}", "ventana_minima: T1, rol: x}"), "exactamente nombre"),
        (("nombre: b", "nombre: 3"), "deben ser textos"),
    ],
)
def test_unas_variables_invalidas_se_rechazan_en_espanol(
    tmp_path: Path, cambio: tuple[str, str], mensaje: str
) -> None:
    contenido = VARIABLES_FICTICIAS.replace(*cambio)
    assert contenido != VARIABLES_FICTICIAS
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        cargar_variables(_archivo(tmp_path, contenido))


def test_sin_archivo_de_variables_del_proyecto_la_causa_es_dp03(tmp_path: Path) -> None:
    with pytest.raises(DecisionPendiente) as error:
        FuenteVariablesYaml(tmp_path / "no_existe.yaml", por_omision=True).cargar()
    assert error.value.decision == "DP-03"


def test_un_archivo_de_variables_indicado_que_no_existe_es_un_error_de_ruta(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfiguracionInvalida, match="No existe el archivo"):
        FuenteVariablesYaml(tmp_path / "no_existe.yaml").cargar()
