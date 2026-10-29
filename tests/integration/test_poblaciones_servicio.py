"""CU-04 y CU-11 con datos sintéticos (H2.5): servicio, archivos, sello y línea de comandos.

PI-02: leer la prueba fuera de la evaluación final falla y queda registrado, y
antes de E4 de la prueba solo se informa el tamaño. PU-17: una auditoría no apta
impide construir poblaciones y particiones.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from fixtures.generador_sintetico import generar_historial, sembrar_problemas
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    SolicitudConstruirPoblaciones,
    SolicitudConsultarRegistro,
    SolicitudLeerPrueba,
)
from suficiencia.application.errores import AuditoriaConErrores, ErrorSuficiencia
from suficiencia.cli import SALIDA_CORRECTA, SALIDA_ERROR, main
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.persistence.particion_archivos import cargador_de_prueba

EJEMPLOS = Path("config/ejemplos")
ARCHIVOS = ("diccionario_sintetico.yaml", "objetivo_ficticio.yaml", "poblaciones_ficticio.yaml")


def _proyecto(tmp_path: Path, raiz: Path, tabla: pd.DataFrame) -> Path:
    (tmp_path / EJEMPLOS).mkdir(parents=True)
    for nombre in ARCHIVOS:
        (tmp_path / EJEMPLOS / nombre).write_bytes((raiz / EJEMPLOS / nombre).read_bytes())
    (tmp_path / "config" / "proyecto.yaml").write_bytes(
        (raiz / "config/proyecto.yaml").read_bytes()
    )
    archivo = tmp_path / "data" / "sintetico" / "historial.csv"
    archivo.parent.mkdir(parents=True)
    tabla.to_csv(archivo, index=False)
    return archivo


def _solicitud(tmp_path: Path, archivo: Path, **extra: object) -> SolicitudConstruirPoblaciones:
    datos: dict[str, object] = {
        "archivo": archivo,
        "diccionario": tmp_path / EJEMPLOS / "diccionario_sintetico.yaml",
        "definicion": EJEMPLOS / "objetivo_ficticio.yaml",
        "configuracion": EJEMPLOS / "poblaciones_ficticio.yaml",
        "clave_efimera": True,
    }
    datos.update(extra)
    return SolicitudConstruirPoblaciones.model_validate(datos)


@pytest.fixture
def historial() -> pd.DataFrame:
    return generar_historial(300, semilla=1)


def test_construye_particiona_sella_y_solo_describe_desarrollo(
    tmp_path: Path, raiz: Path, historial: pd.DataFrame
) -> None:
    archivo = _proyecto(tmp_path, raiz, historial)
    resultado = crear_servicios(tmp_path).escenarios.construir_poblaciones(
        _solicitud(tmp_path, archivo)
    )
    unidades = historial.groupby("cohorte")["codigo_estudiante"].nunique()
    assert resultado.tamano_prueba == unidades["2015-2"]
    assert resultado.unidades_desarrollo == unidades[["2014-2", "2015-1"]].sum()
    total = (
        resultado.unidades_desarrollo
        + resultado.tamano_prueba
        + resultado.unidades_piloto
        + resultado.unidades_excluidas
    )
    assert total == historial["codigo_estudiante"].nunique()
    assert {n.cohorte for n in resultado.no_etiquetables_desarrollo} == {"2014-2", "2015-1"}
    assert len(resultado.descripciones_desarrollo) == 12  # D1, D2 y D3 en las 4 ventanas
    assert all(
        d.tamano <= resultado.unidades_desarrollo for d in resultado.descripciones_desarrollo
    )
    completos = {s.cohorte for s in resultado.seguimiento if s.completo}
    assert completos == {"2014-1", "2014-2", "2015-1", "2015-2"}

    carpeta = Path(resultado.carpeta_particion)
    assert carpeta.is_relative_to(tmp_path / "workspace" / "particiones")
    manifiesto = json.loads((carpeta / "particion.json").read_text(encoding="utf-8"))
    assert manifiesto["cohortes"]["prueba"] == ["2015-2"]
    assert manifiesto["huellas"] == resultado.huellas
    prueba = pd.read_csv(carpeta / "prueba.csv", dtype=str)
    assert list(prueba.columns) == ["cohorte", "seudonimo"]
    texto = (carpeta / "desarrollo.csv").read_text(encoding="utf-8") + prueba.to_csv()
    for codigo in historial["codigo_estudiante"]:
        assert codigo not in texto


def test_pi02_leer_la_prueba_fuera_de_la_evaluacion_final_falla_y_queda_registrado(
    tmp_path: Path, raiz: Path, historial: pd.DataFrame
) -> None:
    archivo = _proyecto(tmp_path, raiz, historial)
    servicios = crear_servicios(tmp_path)
    resultado = servicios.escenarios.construir_poblaciones(_solicitud(tmp_path, archivo))
    with pytest.raises(ErrorSuficiencia, match="sellada"):
        servicios.escenarios.leer_prueba(
            SolicitudLeerPrueba(particion=Path(resultado.carpeta_particion), motivo="curiosidad")
        )
    accesos = servicios.reportes.consultar(SolicitudConsultarRegistro(tipo="accesos")).registros
    assert [(a.contenido["permitido"], a.contenido["motivo"]) for a in accesos] == [
        (False, "curiosidad")
    ]
    assert servicios.reportes.verificar().correcto


def test_una_prueba_modificada_fuera_del_programa_se_detecta(
    tmp_path: Path, raiz: Path, historial: pd.DataFrame
) -> None:
    archivo = _proyecto(tmp_path, raiz, historial)
    resultado = crear_servicios(tmp_path).escenarios.construir_poblaciones(
        _solicitud(tmp_path, archivo)
    )
    carpeta = Path(resultado.carpeta_particion)
    cargar = cargador_de_prueba(carpeta)
    assert len(cargar()) == resultado.tamano_prueba
    with (carpeta / "prueba.csv").open("a", encoding="utf-8") as prueba:
        prueba.write("2015-2,intruso\n")
    with pytest.raises(ConfiguracionInvalida, match="no coinciden con su huella"):
        cargar()


def test_pu17_una_auditoria_no_apta_impide_construir_poblaciones(
    tmp_path: Path, raiz: Path, historial: pd.DataFrame
) -> None:
    con_problemas, _ = sembrar_problemas(historial)
    archivo = _proyecto(tmp_path, raiz, con_problemas)
    with pytest.raises(AuditoriaConErrores):
        crear_servicios(tmp_path).escenarios.construir_poblaciones(_solicitud(tmp_path, archivo))
    assert not (tmp_path / "workspace" / "particiones").exists()


def test_sin_configuracion_se_detiene_por_dp04(
    tmp_path: Path, raiz: Path, historial: pd.DataFrame
) -> None:
    archivo = _proyecto(tmp_path, raiz, historial)
    with pytest.raises(DecisionPendiente) as error:
        crear_servicios(tmp_path).escenarios.construir_poblaciones(
            _solicitud(tmp_path, archivo, configuracion=None)
        )
    assert error.value.decision == "DP-04"


def test_linea_de_comandos(
    tmp_path: Path, raiz: Path, historial: pd.DataFrame, capsys: pytest.CaptureFixture[str]
) -> None:
    archivo = _proyecto(tmp_path, raiz, historial)
    base = ["--raiz", str(tmp_path), "poblaciones"]
    construir = [*base, "construir", str(archivo)]
    construir += ["--diccionario", str(tmp_path / EJEMPLOS / "diccionario_sintetico.yaml")]
    construir += ["--definicion", str(EJEMPLOS / "objetivo_ficticio.yaml")]
    construir += ["--configuracion", str(EJEMPLOS / "poblaciones_ficticio.yaml")]
    assert main([*construir, "--clave-efimera"]) == SALIDA_CORRECTA
    salida = capsys.readouterr().out
    assert salida.startswith("DATOS SINTÉTICOS")
    assert "SELLADA: solo se informa el tamaño" in salida
    assert "SOLO en desarrollo" in salida
    carpeta = next((tmp_path / "workspace" / "particiones").iterdir())

    assert main([*base, "leer-prueba", str(carpeta), "--motivo", "mirar"]) == SALIDA_ERROR
    assert "sellada" in capsys.readouterr().err
