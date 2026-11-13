"""Ensayo general con el dataset sintético del OE3 (F4.3).

Prueba la conversión del dataset al formato del motor, la comprobación de sus huellas,
las configuraciones ficticias del ensayo y la corrección del preprocesamiento que el
ensayo puso en evidencia. Los datos de estas pruebas son tablas pequeñas escritas a
mano (EJEMPLO FICTICIO); el dataset completo se genera en la verificación del hito.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from suficiencia.domain.datos.objetivo import EstadoEtiqueta, etiquetar_unidad
from suficiencia.domain.escenarios.construccion import construir_escenarios
from suficiencia.domain.escenarios.matrices import Agregacion
from suficiencia.experimentation.pipelines import construir_preprocesador, tipos_de_columnas
from suficiencia.persistence.diccionario_yaml import (
    FuenteVariablesDiccionario,
    cargar_diccionario,
)
from suficiencia.persistence.escenarios_yaml import cargar_catalogo
from suficiencia.persistence.experimentos_yaml import cargar_configuracion_experimentos
from suficiencia.persistence.objetivo_yaml import cargar_definicion_objetivo
from suficiencia.persistence.poblaciones_yaml import cargar_configuracion_poblaciones

OE3 = Path("config") / "ejemplos" / "oe3"


def _script(raiz: Path) -> ModuleType:
    especificacion = importlib.util.spec_from_file_location(
        "preparar_ensayo_oe3", raiz / "scripts" / "preparar_ensayo_oe3.py"
    )
    assert especificacion is not None
    assert especificacion.loader is not None
    modulo = importlib.util.module_from_spec(especificacion)
    sys.modules[especificacion.name] = modulo  # lo necesitan sus dataclasses
    especificacion.loader.exec_module(modulo)
    return modulo


# --- Preprocesamiento (D-203) ---------------------------------------------------------


@pytest.mark.parametrize("perfil", ["lineal", "arboles"])
def test_el_preprocesamiento_admite_categoricas_entre_numericas(raiz: Path, perfil: str) -> None:
    """Las variables de un escenario van en orden alfabético: una categórica puede
    quedar entre dos numéricas, como 'area_programa' en el dataset del OE3."""
    configuracion = cargar_configuracion_experimentos(
        raiz / "config" / "ejemplos" / "experimentos_ficticio.yaml"
    )
    tabla = pd.DataFrame(
        {
            "a_numerica": pd.array([1.0, None, 3.0, 4.0, 2.0, 5.0], dtype="Float64"),
            "b_categoria": pd.array(["x", "y", None, "x", "y", "x"], dtype="string"),
            "c_entera": pd.array([1, 2, None, 4, 3, 1], dtype="Int64"),
        }
    )
    objetivo = np.array([0, 1, 0, 1, 1, 0])
    preprocesador = construir_preprocesador(
        configuracion.perfiles[perfil], tipos_de_columnas(tabla)
    )
    modelo = Pipeline([("preprocesamiento", preprocesador), ("modelo", LogisticRegression())])
    modelo.fit(tabla, objetivo)
    assert modelo.predict_proba(tabla).shape == (6, 2)
    nombres = list(preprocesador.get_feature_names_out())
    assert "numericas__a_numerica" in nombres
    assert "numericas__c_entera" in nombres
    assert any(n.startswith("categoricas__b_categoria") for n in nombres)


# --- Conversión del dataset -------------------------------------------------------------


def _longitudinal() -> pd.DataFrame:
    """Dos estudiantes inventados (EJEMPLO FICTICIO)."""
    return pd.DataFrame(
        {
            "id_estudiante": ["SYN-AAAAAAAA"] * 4 + ["SYN-BBBBBBBB"] * 2,
            "periodo_ingreso": ["2011-1"] * 4 + ["2011-2"] * 2,
            "ciclo_regular": [1, 2, 3, 4, 1, 2],
            "fecha_registro_estado": [
                "2011-03-10",
                "2011-08-10",
                "2012-03-10",
                "2012-08-10",
                "2011-08-12",
                "2012-03-12",
            ],
            "estado_matricula": [
                "matriculado",
                "matriculado",
                "reserva_aprobada",
                "matriculado",
                "matriculado",
                "no_matriculado",
            ],
            "retiro_total": [0, 1, 0, 0, 0, 0],
        }
    )


def _ancho() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id_estudiante": ["SYN-BBBBBBBB", "SYN-AAAAAAAA"],
            "T0_A_puntaje": [61.5, 70.0],
            "T0_S_colegio": ["publico", "privado"],
            "T1_A_promedio": [12.5, 14.0],
            "T2_A_promedio": [np.nan, 13.0],
            "T3_A_promedio": [np.nan, np.nan],
            "T2_A_variacion": [np.nan, -1.0],
            "T3_A_variacion": [np.nan, np.nan],
            "T1_B_accesos": [10.0, 20.0],
            "T2_B_accesos": [np.nan, 30.0],
            "T3_B_accesos": [np.nan, np.nan],
        }
    )


def test_la_conversion_arma_una_fila_por_estudiante_y_ciclo(raiz: Path) -> None:
    script = _script(raiz)
    variables = [
        script.VariableOE3("puntaje", "A", "T0", False),
        script.VariableOE3("colegio", "S", "T0", False),
        script.VariableOE3("promedio", "A", "T1", False),
        script.VariableOE3("variacion", "A", "T2", False),
        script.VariableOE3("accesos", "B", "T1", True),
    ]
    historial = script.convertir(_longitudinal(), _ancho(), variables)

    assert list(historial.columns) == [*script.COLUMNAS_FIJAS, *(v.nombre for v in variables)]
    assert (historial["origen_datos"] == "SINTETICO").all()
    a = historial[historial["codigo_estudiante"] == "SYN-AAAAAAAA"].set_index("ciclo")
    # Un ciclo matriculado con retiro total se escribe como retiro_total.
    assert a["estado_matricula"].tolist() == [
        "matriculado",
        "retiro_total",
        "reserva_aprobada",
        "matriculado",
    ]
    # Las variables desde T0 llevan su valor a o(T0) en todas las filas.
    assert (a["puntaje"] == 70.0).all()
    assert (a["colegio"] == "privado").all()
    # Las demás, en la fila del ciclo k, su valor a o(Tk); vacías desde el ciclo 4.
    assert a.loc[1, "promedio"] == 14.0
    assert a.loc[2, "promedio"] == 13.0
    assert pd.isna(a.loc[1, "variacion"])
    assert a.loc[2, "variacion"] == -1.0
    assert pd.isna(a.loc[3, "promedio"])
    assert pd.isna(a.loc[4, "promedio"])
    # Las enteras quedan como enteros con faltantes (sin ".0" al escribir el CSV).
    assert str(historial["accesos"].dtype) == "Int64"
    assert a.loc[2, "accesos"] == 30
    b = historial[historial["codigo_estudiante"] == "SYN-BBBBBBBB"].set_index("ciclo")
    assert b.loc[1, "cohorte"] == "2011-2"
    assert pd.isna(b.loc[2, "promedio"])


def test_el_historial_se_escribe_igual_en_cualquier_sistema(raiz: Path, tmp_path: Path) -> None:
    """Fin de línea LF también en Windows: la huella del historial no depende del sistema."""
    script = _script(raiz)
    variables = [script.VariableOE3("accesos", "B", "T1", True)]
    historial = script.convertir(_longitudinal(), _ancho(), variables)
    salida = tmp_path / "historial.csv"
    script.escribir(historial, salida)
    contenido = salida.read_bytes()
    assert b"\r\n" not in contenido
    assert contenido.count(b"\n") == len(historial) + 1


def test_la_conversion_rechaza_datos_incoherentes(raiz: Path) -> None:
    script = _script(raiz)
    variables = [script.VariableOE3("accesos", "B", "T1", True)]
    ancho = _ancho()
    with pytest.raises(ValueError, match="no están en el ancho"):
        script.convertir(_longitudinal(), ancho.iloc[1:], variables)
    with pytest.raises(ValueError, match="repite estudiantes"):
        script.convertir(_longitudinal(), pd.concat([ancho, ancho]), variables)
    ancho.loc[0, "T1_B_accesos"] = 10.5
    with pytest.raises(ValueError, match="decimales"):
        script.convertir(_longitudinal(), ancho, variables)


def test_las_huellas_detectan_archivos_faltantes_o_distintos(raiz: Path, tmp_path: Path) -> None:
    script = _script(raiz)
    assert len(script.huellas_distintas(tmp_path)) == len(script.HUELLAS) == 10
    (tmp_path / "dataset_sintetico_wide.csv").write_text("otro contenido\n", encoding="utf-8")
    distintas = script.huellas_distintas(tmp_path)
    assert any(
        d.startswith("dataset_sintetico_wide.csv:") and "se esperaba 719891af3915f686" in d
        for d in distintas
    )


def test_el_script_no_usa_archivos_con_otras_huellas(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = _script(raiz)
    salida = raiz / "data" / "sintetico" / "prueba_f43_no_debe_existir.csv"
    assert script.main([str(tmp_path), "--salida", str(salida)]) == 1
    assert not salida.exists()
    assert "no se usan" in capsys.readouterr().err


def test_el_script_solo_escribe_dentro_de_data(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = _script(raiz)
    salida = tmp_path / "fuera.csv"
    assert script.main([str(tmp_path), "--salida", str(salida)]) == 1
    assert not salida.exists()
    assert "dentro de la carpeta data/" in capsys.readouterr().err


def test_la_concordancia_solo_mira_las_cohortes_de_desarrollo(raiz: Path) -> None:
    script = _script(raiz)
    definicion = cargar_definicion_objetivo(raiz / OE3 / "objetivo_oe3_ficticio.yaml")
    estados = {"M": "matriculado", "N": "no_matriculado"}
    filas = []
    for codigo, cohorte, trayectoria in (
        ("SYN-DESARR01", "2011-1", "MNNMM"),  # evento en el ciclo 2
        ("SYN-DESARR02", "2011-1", "MMMMM"),  # sin evento
        ("SYN-PRUEBA01", "2015-1", "MNNMM"),  # prueba: no se mira
    ):
        for ciclo, letra in enumerate(trayectoria, start=1):
            filas.append(
                {
                    "codigo_estudiante": codigo,
                    "cohorte": cohorte,
                    "ciclo": ciclo,
                    "estado_matricula": estados[letra],
                }
            )
    ancho = pd.DataFrame(
        {
            "id_estudiante": ["SYN-DESARR01", "SYN-DESARR02", "SYN-PRUEBA01"],
            "rol_particion": ["desarrollo", "desarrollo", "prueba"],
            "OUT_estado_etiqueta": ["conocida", "conocida", "conocida"],
            # La segunda discrepa a propósito, para ver que se cuenta.
            "OUT_y_desercion": [1.0, 1.0, 1.0],
        }
    )
    tabla = script.concordancia(pd.DataFrame(filas), ancho, definicion)
    assert int(tabla.to_numpy().sum()) == 2
    assert tabla.at["positivo", "positivo"] == 1
    assert tabla.at["positivo", "negativo"] == 1


# --- Configuraciones ficticias del ensayo ---------------------------------------------


def test_el_diccionario_del_ensayo_tiene_las_40_variables_del_oe3(raiz: Path) -> None:
    diccionario = cargar_diccionario(raiz / OE3 / "diccionario_oe3_ficticio.yaml")
    assert diccionario.ficticio
    variables = FuenteVariablesDiccionario(raiz / OE3 / "diccionario_oe3_ficticio.yaml").cargar()
    por_bloque = Counter(v.bloque.value for v in variables.variables)
    assert por_bloque == {"A": 15, "F": 9, "S": 9, "B": 7}
    assert [v.nombre for v in _script(raiz).variables_del_diccionario()] == [
        v.nombre for v in variables.variables
    ]


def test_las_configuraciones_del_ensayo_son_ficticias_y_coherentes(raiz: Path) -> None:
    variables = FuenteVariablesDiccionario(raiz / OE3 / "diccionario_oe3_ficticio.yaml").cargar()
    catalogo = cargar_catalogo(raiz / OE3 / "escenarios_oe3_ficticio.yaml")
    experimentos = cargar_configuracion_experimentos(raiz / OE3 / "experimentos_oe3_ficticio.yaml")
    poblaciones = cargar_configuracion_poblaciones(raiz / OE3 / "poblaciones_oe3_ficticio.yaml")
    objetivo = cargar_definicion_objetivo(raiz / OE3 / "objetivo_oe3_ficticio.yaml")
    assert catalogo.ficticio and experimentos.ficticio and poblaciones.ficticio
    assert objetivo.ficticio

    escenarios = construir_escenarios(catalogo.catalogo, variables.variables)
    no_factibles = sorted(e.codigo for e in escenarios if not e.factible)
    assert len(escenarios) - len(no_factibles) == 28
    assert no_factibles == ["T0|A+B", "T0|A+F+B", "T0|A+F+S+B", "T0|A+S+B"]

    lecturas = experimentos.matrices.agregacion
    assert set(lecturas) == {v.nombre for v in variables.variables}
    for v in variables.variables:
        desde_t0 = v.ventana_minima == "T0"
        esperada = Agregacion.PRIMER_REGISTRO if desde_t0 else Agregacion.ULTIMO_CICLO
        assert lecturas[v.nombre] is esperada

    particion = poblaciones.particion
    assert len(particion.desarrollo) == 8
    assert particion.prueba == {"2015-1", "2015-2"}
    assert particion.excluidas == {"2016-1", "2016-2"}


# Casos especiales del generador del OE3 (control V05): trayectoria con M matriculado,
# N sin matrícula y R reserva; el último ciclo es el último observado.
CASOS_GENERADOR = [
    ("MNMMM", EstadoEtiqueta.NEGATIVO, None),
    ("MNN", EstadoEtiqueta.POSITIVO, 2),
    ("MRNN", EstadoEtiqueta.POSITIVO, 3),
    ("MNRN", EstadoEtiqueta.POSITIVO, 2),
    ("MNRMM", EstadoEtiqueta.NEGATIVO, None),
    ("MMMNN", EstadoEtiqueta.POSITIVO, 4),
    ("MMMMNN", EstadoEtiqueta.NEGATIVO, None),
    ("MMMN", EstadoEtiqueta.NO_ETIQUETABLE, None),
    ("MMMNR", EstadoEtiqueta.NO_ETIQUETABLE, None),
    ("MMR", EstadoEtiqueta.NO_ETIQUETABLE, None),
    ("MMMM", EstadoEtiqueta.NEGATIVO, None),
    ("MMMR", EstadoEtiqueta.NEGATIVO, None),
    ("MNNM", EstadoEtiqueta.POSITIVO, 2),
    ("MRRNN", EstadoEtiqueta.POSITIVO, 4),
]
LETRAS = {
    "M": "matriculado",
    "N": "no_matriculado",
    "R": "reserva_aprobada",
    "F": "baja_por_fallecimiento",
}


@pytest.mark.parametrize(("trayectoria", "estado", "evento"), CASOS_GENERADOR)
def test_el_objetivo_del_ensayo_coincide_con_el_generador_en_sus_casos(
    raiz: Path, trayectoria: str, estado: EstadoEtiqueta, evento: int | None
) -> None:
    definicion = cargar_definicion_objetivo(raiz / OE3 / "objetivo_oe3_ficticio.yaml")
    estados = {ciclo: LETRAS[letra] for ciclo, letra in enumerate(trayectoria, start=1)}
    etiqueta = etiquetar_unidad(estados, len(trayectoria), definicion)
    assert (etiqueta.estado, etiqueta.periodo_evento) == (estado, evento)


@pytest.mark.parametrize(
    ("trayectoria", "generador"),
    [
        # El generador salta la reserva del ciclo H+1 y confirma con el ciclo 6 (Y = 1);
        # el motor confirma solo con el ciclo H+1 y deja la etiqueta sin decidir.
        ("MMMNRN", "positivo con e = 4"),
        # El generador excluye el episodio con una baja por fallecimiento en H+1; el
        # motor ya decidió Y = 0 al terminar el horizonte.
        ("MMMMF", "excluido"),
    ],
)
def test_diferencias_conocidas_entre_el_motor_y_el_generador(
    raiz: Path, trayectoria: str, generador: str
) -> None:
    definicion = cargar_definicion_objetivo(raiz / OE3 / "objetivo_oe3_ficticio.yaml")
    estados = {ciclo: LETRAS[letra] for ciclo, letra in enumerate(trayectoria, start=1)}
    etiqueta = etiquetar_unidad(estados, len(trayectoria), definicion)
    esperado = {
        "MMMNRN": EstadoEtiqueta.NO_ETIQUETABLE,
        "MMMMF": EstadoEtiqueta.NEGATIVO,
    }[trayectoria]
    assert etiqueta.estado is esperado, f"el generador da: {generador}"
