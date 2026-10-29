"""Diccionario de datos (H2.3): PU-16 y validación del YAML."""

from __future__ import annotations

from pathlib import Path

import pytest

from suficiencia.domain.datos.diccionario import (
    COLUMNA_SEUDONIMO,
    DefinicionVariable,
    Diccionario,
    Rol,
    TipoDato,
)
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.escenarios.modelo import Bloque
from suficiencia.persistence.diccionario_yaml import (
    FuenteVariablesDiccionario,
    cargar_diccionario,
)

EJEMPLO = Path("config") / "ejemplos" / "diccionario_sintetico.yaml"


def _rasgo(**cambios: object) -> DefinicionVariable:
    campos: dict[str, object] = {
        "nombre": "x",
        "tipo": TipoDato.DECIMAL,
        "rol": Rol.RASGO,
        "obligatoria": False,
        "bloque": Bloque.ACADEMICO,
        "ventana_minima": "T1",
    }
    campos.update(cambios)
    return DefinicionVariable(**campos)  # type: ignore[arg-type]


def test_el_diccionario_de_ejemplo_es_valido_y_ficticio(raiz: Path) -> None:
    diccionario = cargar_diccionario(raiz / EJEMPLO)
    assert diccionario.ficticio
    assert diccionario.identificadores == ("codigo_estudiante",)
    assert diccionario.columna_origen == "origen_datos"
    assert diccionario.clave_seudonimizada() == (COLUMNA_SEUDONIMO, "ciclo")
    variables = diccionario.variables_de_escenario()
    assert len(variables) == 8
    assert {v.bloque for v in variables} == set(Bloque)
    assert "estado_matricula" not in {v.nombre for v in variables}


# PU-16 ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cambios",
    [{"bloque": None}, {"ventana_minima": None}, {"bloque": None, "ventana_minima": None}],
)
def test_pu16_un_rasgo_sin_bloque_o_sin_ventana_se_rechaza(cambios: dict[str, object]) -> None:
    with pytest.raises(ConfiguracionInvalida, match="necesita bloque y ventana"):
        _rasgo(**cambios)


def test_pu16_un_bloque_inexistente_se_rechaza(tmp_path: Path, raiz: Path) -> None:
    texto = (raiz / EJEMPLO).read_text(encoding="utf-8").replace("bloque: B,", "bloque: Z,")
    archivo = tmp_path / "d.yaml"
    archivo.write_text(texto, encoding="utf-8")
    with pytest.raises(ConfiguracionInvalida, match="El bloque 'Z' no existe"):
        cargar_diccionario(archivo)


def test_pu16_una_ventana_inexistente_se_rechaza() -> None:
    with pytest.raises(ConfiguracionInvalida, match="T7"):
        _rasgo(ventana_minima="T7")


@pytest.mark.parametrize("rol", [r for r in Rol if r is not Rol.RASGO])
def test_pu16_solo_los_rasgos_llevan_bloque_y_ventana(rol: Rol) -> None:
    """Así el objetivo o un identificador nunca entran en un escenario por error."""
    with pytest.raises(ConfiguracionInvalida, match="solo los rasgos llevan bloque"):
        _rasgo(rol=rol, tipo=TipoDato.TEXTO)


def test_pu16_cada_rasgo_recibe_exactamente_un_bloque_y_una_ventana(raiz: Path) -> None:
    diccionario = cargar_diccionario(raiz / EJEMPLO)
    for variable in diccionario.de_rol(Rol.RASGO):
        assert isinstance(variable.bloque, Bloque)
        assert variable.ventana_minima in {"T0", "T1", "T2", "T3"}


# Otras reglas del diccionario -------------------------------------------------


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"nombre": COLUMNA_SEUDONIMO}, "nombre reservado"),
        ({"minimo": 5.0, "maximo": 1.0}, "mínimo es mayor"),
        ({"tipo": TipoDato.TEXTO, "minimo": 1.0}, "solo las variables numéricas"),
        ({"tipo": TipoDato.CATEGORIA}, "las categorías, y solo ellas"),
        ({"valores": ("a",)}, "las categorías, y solo ellas"),
        ({"tipo": TipoDato.CATEGORIA, "valores": ()}, "no puede estar vacío"),
        ({"tipo": TipoDato.CODIGO, "patron": "[0-9"}, "patrón no es válido"),
        ({"patron": "[0-9]+"}, "solo los textos y códigos"),
    ],
)
def test_reglas_de_cada_variable(cambios: dict[str, object], mensaje: str) -> None:
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        _rasgo(**cambios)


def test_la_columna_de_origen_solo_admite_la_marca_sintetica() -> None:
    with pytest.raises(ConfiguracionInvalida, match="único valor SINTETICO"):
        DefinicionVariable(
            "origen", TipoDato.CATEGORIA, Rol.ORIGEN, True, valores=("SINTETICO", "REAL")
        )


@pytest.mark.parametrize(
    ("clave", "variables", "mensaje"),
    [
        (("x",), (_rasgo(), _rasgo()), "variables repetidas: x"),
        ((), (_rasgo(),), "'clave' debe nombrar"),
        (("y",), (_rasgo(),), "columnas no declaradas: y"),
    ],
)
def test_reglas_del_diccionario(
    clave: tuple[str, ...], variables: tuple[DefinicionVariable, ...], mensaje: str
) -> None:
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        Diccionario(nombre="d", ficticio=True, variables=variables, clave=clave)


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        (("ficticio: true", "ficticio: talvez"), "'ficticio' debe ser true o false"),
        (
            (
                "rol: rasgo, obligatoria: true, bloque: A",
                "rol: predictor, obligatoria: true, bloque: A",
            ),
            "'rol' = 'predictor' no es válido",
        ),
        (
            ("tipo: entero, rol: periodo", "tipo: numero, rol: periodo"),
            "'tipo' = 'numero' no es válido",
        ),
        (('obligatoria: true, patron: "20', 'obligatoria: si, patron: "20'), "'obligatoria'"),
        (("version_diccionario: 1", "version_diccionario: 9"), "version_diccionario"),
        (("minimo: 1, maximo: 8", "minimo: uno, maximo: 8"), "'minimo' debe ser un número"),
    ],
)
def test_un_diccionario_yaml_invalido_se_rechaza_en_espanol(
    tmp_path: Path, raiz: Path, cambio: tuple[str, str], mensaje: str
) -> None:
    original = (raiz / EJEMPLO).read_text(encoding="utf-8")
    texto = original.replace(*cambio, 1)
    assert texto != original
    archivo = tmp_path / "d.yaml"
    archivo.write_text(texto, encoding="utf-8")
    with pytest.raises(ConfiguracionInvalida, match=mensaje) as error:
        cargar_diccionario(archivo)
    assert "Acción sugerida" in str(error.value)


def test_sin_diccionario_del_proyecto_la_causa_es_dp03(tmp_path: Path) -> None:
    with pytest.raises(DecisionPendiente) as error:
        FuenteVariablesDiccionario(tmp_path / "no_existe.yaml", por_omision=True).cargar()
    assert error.value.decision == "DP-03"


def test_el_diccionario_alimenta_los_escenarios(raiz: Path) -> None:
    declaradas = FuenteVariablesDiccionario(raiz / EJEMPLO).cargar()
    assert declaradas.ficticio
    assert {v.nombre for v in declaradas.variables} == {
        "puntaje_admision",
        "promedio_ciclo",
        "creditos_aprobados_ciclo",
        "beca_al_ingreso",
        "deuda_vencida_ciclo",
        "tipo_colegio",
        "rango_ingreso_familiar",
        "horas_plataforma_ciclo",
    }
