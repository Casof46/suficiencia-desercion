"""Preparación del desarrollo con el historial sintético ampliado (F3.1).

- PI-01: el preprocesamiento se ajusta solo con las filas de ajuste de cada fold;
  sus estadísticos (mediana, media) son los del ajuste y no los de todos los datos.
- PI-08 (cohortes por fold): todos los escenarios usan los mismos folds.
- La prueba no se lee: las matrices solo tienen cohortes de desarrollo y cambiar
  las filas de la prueba no cambia nada del desarrollo.
- Servicio y línea de comandos, con las decisiones abiertas como datos ficticios.

Todo es sintético y ficticio: los números no son resultados del método.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml

from fixtures.generador_sintetico import COHORTES_AMPLIADAS, generar_historial
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import SolicitudPrepararDesarrollo
from suficiencia.application.preparacion_desarrollo import filas_de, preparar
from suficiencia.cli import SALIDA_CORRECTA, SALIDA_ERROR, main
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.domain.experimentos import PerfilPreprocesamiento
from suficiencia.experimentation.pipelines import (
    columnas_tras_preprocesar,
    construir_preprocesador,
    tipos_de_columnas,
)
from suficiencia.persistence.diccionario_yaml import FuenteVariablesDiccionario
from suficiencia.persistence.escenarios_yaml import FuenteCatalogoYaml
from suficiencia.persistence.experimentos_yaml import cargar_configuracion_experimentos
from suficiencia.persistence.poblaciones_yaml import cargar_configuracion_poblaciones

EJEMPLOS = Path("config/ejemplos")
DESARROLLO = tuple(f"{a}-{s}" for a in range(2010, 2014) for s in (1, 2))
PRUEBA = ("2014-1", "2014-2")


@pytest.fixture(scope="module")
def proyecto(tmp_path_factory: pytest.TempPathFactory) -> Path:
    raiz = Path(__file__).resolve().parents[2]
    destino = tmp_path_factory.mktemp("proyecto")
    (destino / EJEMPLOS).mkdir(parents=True)
    for archivo in (raiz / EJEMPLOS).glob("*.yaml"):  # sin la subcarpeta oe3/ (F4.3)
        (destino / EJEMPLOS / archivo.name).write_bytes(archivo.read_bytes())
    (destino / "config" / "proyecto.yaml").write_bytes((raiz / "config/proyecto.yaml").read_bytes())
    datos = destino / "data" / "sintetico" / "ampliado.csv"
    datos.parent.mkdir(parents=True)
    generar_historial(900, semilla=3, cohortes=COHORTES_AMPLIADAS).to_csv(datos, index=False)
    return destino


def _solicitud(proyecto: Path, **cambios: Any) -> SolicitudPrepararDesarrollo:
    datos: dict[str, Any] = {
        "archivo": proyecto / "data" / "sintetico" / "ampliado.csv",
        "diccionario": proyecto / EJEMPLOS / "diccionario_sintetico.yaml",
        "definicion": EJEMPLOS / "objetivo_ficticio.yaml",
        "poblaciones": EJEMPLOS / "poblaciones_ampliado_ficticio.yaml",
        "escenarios": EJEMPLOS / "escenarios_ficticio.yaml",
        "experimentos": EJEMPLOS / "experimentos_ficticio.yaml",
        "clave_efimera": True,
    }
    datos.update(cambios)
    return SolicitudPrepararDesarrollo.model_validate(datos)


def _preparacion(proyecto: Path, tabla: pd.DataFrame | None = None) -> Any:
    servicios = crear_servicios(proyecto)
    historial = servicios.datos.preparar_historial(
        proyecto / "data" / "sintetico" / "ampliado.csv",
        proyecto / EJEMPLOS / "diccionario_sintetico.yaml",
        proyecto / EJEMPLOS / "objetivo_ficticio.yaml",
        True,
        ",",
    )
    return historial, preparar(
        historial.tabla if tabla is None else tabla,
        historial.columnas,
        historial.definicion,
        cargar_configuracion_poblaciones(
            proyecto / EJEMPLOS / "poblaciones_ampliado_ficticio.yaml"
        ),
        FuenteCatalogoYaml(proyecto / EJEMPLOS / "escenarios_ficticio.yaml").cargar(),
        FuenteVariablesDiccionario(proyecto / EJEMPLOS / "diccionario_sintetico.yaml").cargar(),
        cargar_configuracion_experimentos(proyecto / EJEMPLOS / "experimentos_ficticio.yaml"),
    )


def test_las_matrices_solo_tienen_desarrollo_y_la_prueba_no_influye(proyecto: Path) -> None:
    historial, preparacion = _preparacion(proyecto)
    assert preparacion.cohortes_desarrollo == DESARROLLO
    assert len(preparacion.matrices) == 28
    for matriz in preparacion.matrices:
        assert set(matriz.cohorte.astype(str)) <= set(DESARROLLO)
    # Alterar todas las filas de la prueba y de las excluidas no cambia nada.
    tabla = historial.tabla.copy()
    fuera = ~tabla["cohorte"].astype(str).isin(DESARROLLO)
    assert fuera.any()
    tabla.loc[fuera, "estado_matricula"] = "retiro_total"
    tabla.loc[fuera, "puntaje_admision"] = 0.0
    _, alterada = _preparacion(proyecto, tabla)
    for original, otra in zip(preparacion.matrices, alterada.matrices, strict=True):
        pd.testing.assert_frame_equal(original.predictores, otra.predictores)
        pd.testing.assert_series_equal(original.objetivo, otra.objetivo)


def test_pi01_imputacion_y_escalado_salen_solo_del_ajuste_del_fold(proyecto: Path) -> None:
    _, preparacion = _preparacion(proyecto)
    configuracion = cargar_configuracion_experimentos(
        proyecto / EJEMPLOS / "experimentos_ficticio.yaml"
    )
    perfil = configuracion.perfiles["lineal"]
    matriz = next(m for m in preparacion.matrices if m.escenario == "T2|A")
    columna = "promedio_ciclo"
    assert matriz.predictores[columna].isna().any(), "el caso necesita faltantes"
    distintos = 0
    for fold in preparacion.folds:
        ajuste = matriz.predictores[filas_de(matriz, fold.ajuste).to_numpy()]
        preprocesador = construir_preprocesador(perfil, tipos_de_columnas(ajuste))
        preprocesador.fit(ajuste)
        numericas = preprocesador.named_steps["columnas"].named_transformers_["numericas"]
        posicion = list(tipos_de_columnas(ajuste).numericas).index(columna)
        valores = ajuste[columna].astype("Float64").to_numpy(dtype="float64", na_value=np.nan)
        mediana = float(np.nanmedian(valores))
        imputados = np.where(np.isnan(valores), mediana, valores)
        assert numericas.named_steps["imputacion"].statistics_[posicion] == pytest.approx(mediana)
        assert numericas.named_steps["escalado"].mean_[posicion] == pytest.approx(imputados.mean())
        completa = matriz.predictores[columna].astype("Float64")
        distintos += int(mediana != pytest.approx(float(completa.median())))
    assert distintos > 0, "el caso debe distinguir el ajuste de todos los datos"


def test_pi01_pi08_el_servicio_ajusta_con_el_ajuste_de_los_mismos_folds(proyecto: Path) -> None:
    servicios = crear_servicios(proyecto)
    llamadas: list[tuple[int, list[int]]] = []
    original = servicios.experimentos._preprocesar

    def espia(
        perfil: PerfilPreprocesamiento, ajuste: pd.DataFrame, otras: Sequence[pd.DataFrame]
    ) -> int:
        llamadas.append((len(ajuste), [len(t) for t in otras]))
        return original(perfil, ajuste, otras)

    servicios.experimentos._preprocesar = espia
    resultado = servicios.experimentos.preparar_desarrollo(_solicitud(proyecto))
    assert resultado.sintetico
    assert resultado.configuraciones_ficticias
    assert len(resultado.escenarios) == 28
    assert len(resultado.no_factibles) == 4
    assert [f.validacion for f in resultado.folds] == list(DESARROLLO[2:])
    conteos = {v.ventana: v.folds for v in resultado.ventanas}
    esperadas = [
        (c.ajuste, [c.calibracion, c.validacion])
        for e in resultado.escenarios
        for _ in resultado.perfiles
        for c in conteos[e.ventana]
    ]
    assert llamadas == esperadas  # cada ajuste usa solo las filas de ajuste de su fold
    for ventana in resultado.ventanas:
        assert [c.numero for c in ventana.folds] == [f.numero for f in resultado.folds]
        assert (
            sum(c.validacion for c in ventana.folds)
            + ventana.folds[0].ajuste
            + (ventana.folds[0].calibracion)
            == ventana.filas
        )


def test_columnas_iguales_en_ajuste_y_fuera_aunque_aparezca_una_categoria_nueva() -> None:
    perfil = cargar_configuracion_experimentos(
        Path(__file__).resolve().parents[2] / EJEMPLOS / "experimentos_ficticio.yaml"
    ).perfiles["lineal"]
    ajuste = pd.DataFrame(
        {
            "x": pd.array([1.0, None, 3.0], dtype="Float64"),
            "c": pd.array(["a", "b", None], dtype="string"),
        }
    )
    otra = pd.DataFrame(
        {"x": pd.array([None, 2.0], dtype="Float64"), "c": pd.array(["z", "a"], dtype="string")}
    )
    # x escalada + indicador de faltante de x + c en {a, b, __faltante__}
    assert columnas_tras_preprocesar(perfil, ajuste, [otra]) == 5
    with pytest.raises(ConfiguracionInvalida):
        columnas_tras_preprocesar(perfil, ajuste.iloc[0:0], [otra])


def test_sin_configuracion_de_experimentos_se_detiene_con_dp07(proyecto: Path) -> None:
    with pytest.raises(DecisionPendiente, match="DP-07"):
        crear_servicios(proyecto).experimentos.preparar_desarrollo(
            _solicitud(proyecto, experimentos=None)
        )


def test_d3_como_diseno_principal_no_permite_preparar(proyecto: Path) -> None:
    datos = yaml.safe_load(
        (proyecto / EJEMPLOS / "poblaciones_ampliado_ficticio.yaml").read_text(encoding="utf-8")
    )
    datos["diseno_principal"] = "D3"
    datos["analisis_complementarios"] = ["D1", "D2"]
    archivo = proyecto / "config" / "poblaciones_d3.yaml"
    archivo.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfiguracionInvalida, match="D3"):
        crear_servicios(proyecto).experimentos.preparar_desarrollo(
            _solicitud(proyecto, poblaciones=archivo)
        )


def test_linea_de_comandos(proyecto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    solicitud = _solicitud(proyecto)
    argumentos = [
        "--raiz",
        str(proyecto),
        "experimentos",
        "preparar",
        str(solicitud.archivo),
        "--diccionario",
        str(solicitud.diccionario),
        "--definicion",
        str(proyecto / EJEMPLOS / "objetivo_ficticio.yaml"),
        "--poblaciones",
        str(proyecto / EJEMPLOS / "poblaciones_ampliado_ficticio.yaml"),
        "--escenarios",
        str(proyecto / EJEMPLOS / "escenarios_ficticio.yaml"),
        "--clave-efimera",
    ]
    assert main(argumentos) == SALIDA_ERROR
    assert "DP-07" in capsys.readouterr().err
    experimentos = str(proyecto / EJEMPLOS / "experimentos_ficticio.yaml")
    assert main([*argumentos, "--experimentos", experimentos]) == SALIDA_CORRECTA
    salida = capsys.readouterr().out
    assert "DATOS SINTÉTICOS" in salida
    assert "CONFIGURACIÓN FICTICIA" in salida
    assert "Folds cronológicos (DP-07): 6" in salida
    assert "Fold 6: ajuste 2010-1, 2010-2, 2011-1, 2011-2, 2012-1, 2012-2" in salida
    assert "Escenarios preparados: 28; no factibles (no se entrenan): 4" in salida
    assert "La prueba no se lee." in salida
    assert all(cohorte not in salida for cohorte in PRUEBA)
