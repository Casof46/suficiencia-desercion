"""Pruebas de aceptación de la Fase 2 (H2.8): CU-03, CU-04 y CU-05 de punta a punta.

Recorren cada caso de uso desde la línea de comandos, como lo usará el equipo, con
datos SINTÉTICOS y configuraciones FICTICIAS en un proyecto temporal. Comprueban las
poscondiciones de la sección 3 de la especificación. No prueban el método: sus
resultados no dicen nada sobre estudiantes reales.

PI-11 se comprueba aquí solo en su parte determinista: dos ejecuciones con la misma
clave de seudonimización producen exactamente los mismos archivos. La comparación
de métricas dentro de una tolerancia llega cuando existan métricas.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

from fixtures.generador_sintetico import generar_historial
from fixtures.protocolo_de_prueba import ARCHIVO_PROTOCOLO_FICTICIO, datos_protocolo_ficticio
from suficiencia.cli import SALIDA_CORRECTA, SALIDA_ERROR, main
from suficiencia.domain.evaluacion.protocolo import DECISIONES_DEL_PROTOCOLO

EJEMPLOS = "config/ejemplos"
CLAVE_DE_PRUEBA = "clave-solo-para-pruebas-automaticas-de-h2-8-no-es-de-nadie"


@pytest.fixture
def proyecto(tmp_path: Path, raiz: Path) -> Path:
    """Copia de la configuración y los ejemplos del repositorio, con un historial sintético."""
    shutil.copytree(raiz / "config", tmp_path / "config")
    shutil.copy(raiz / "requirements.lock", tmp_path / "requirements.lock")
    archivo = tmp_path / "data" / "sintetico" / "historial.csv"
    archivo.parent.mkdir(parents=True)
    generar_historial(200, semilla=3).to_csv(archivo, index=False)
    return tmp_path


def _correr(
    proyecto: Path, capsys: pytest.CaptureFixture[str], *argumentos: str
) -> tuple[int, str, str]:
    codigo = main(["--raiz", str(proyecto), *argumentos])
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def _datos(proyecto: Path) -> list[str]:
    return [
        str(proyecto / "data" / "sintetico" / "historial.csv"),
        "--diccionario",
        f"{EJEMPLOS}/diccionario_sintetico.yaml",
        "--definicion",
        f"{EJEMPLOS}/objetivo_ficticio.yaml",
    ]


# CU-03 -----------------------------------------------------------------------------


def test_cu03_cada_estudiante_tiene_evento_ultimo_periodo_y_estado_con_motivo(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo, salida, _ = _correr(
        proyecto,
        capsys,
        "objetivo",
        "construir",
        *_datos(proyecto),
        "--clave-efimera",
        "--salida",
        "data/procesado/objetivo.csv",
    )
    assert codigo == SALIDA_CORRECTA, salida
    tabla = pd.read_csv(proyecto / "data" / "procesado" / "objetivo.csv")
    for columna in ("estado_etiqueta", "motivo", "periodo_evento", "ultimo_periodo_observado"):
        assert columna in tabla.columns
    assert "codigo_estudiante" not in tabla.columns  # solo seudónimos (RF-M1-04)
    assert set(tabla["estado_etiqueta"]) <= {"positivo", "negativo", "no_etiquetable"}
    no_etiquetables = tabla[tabla["estado_etiqueta"] == "no_etiquetable"]
    assert no_etiquetables["motivo"].notna().all()  # todo no etiquetable dice por qué
    etiquetables = tabla[tabla["estado_etiqueta"] != "no_etiquetable"]
    assert etiquetables["motivo"].isna().all()
    positivos = tabla[tabla["estado_etiqueta"] == "positivo"]
    assert positivos["periodo_evento"].notna().all()
    assert tabla["ultimo_periodo_observado"].notna().all()


def test_cu03_sin_definicion_aprobada_se_detiene_por_dp01(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argumentos = _datos(proyecto)[:3]  # sin --definicion: usaría la del proyecto, que no existe
    codigo, _, error = _correr(
        proyecto, capsys, "objetivo", "construir", *argumentos, "--clave-efimera"
    )
    assert codigo == SALIDA_ERROR
    assert "DP-01" in error


# CU-04 -----------------------------------------------------------------------------


def test_cu04_32_escenarios_poblaciones_por_ventana_y_prueba_sellada(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo, salida, _ = _correr(
        proyecto,
        capsys,
        "escenarios",
        "--configuracion",
        f"{EJEMPLOS}/escenarios_ficticio.yaml",
        "--variables",
        f"{EJEMPLOS}/variables_ficticias.yaml",
    )
    assert codigo == SALIDA_CORRECTA
    assert "Escenarios: 32 (factibles: 28; no factibles: 4)" in salida
    assert "Verificación anti-fuga: correcta" in salida

    codigo, salida, _ = _correr(
        proyecto,
        capsys,
        "poblaciones",
        "construir",
        *_datos(proyecto),
        "--configuracion",
        f"{EJEMPLOS}/poblaciones_ficticio.yaml",
        "--clave-efimera",
    )
    assert codigo == SALIDA_CORRECTA, salida
    assert "SELLADA: solo se informa el tamaño" in salida
    carpeta = next((proyecto / "workspace" / "particiones").iterdir())
    manifiesto = json.loads((carpeta / "particion.json").read_text(encoding="utf-8"))
    assert set(manifiesto["huellas"]) == {"desarrollo", "prueba", "piloto", "excluidas"}

    codigo, _, error = _correr(
        proyecto, capsys, "poblaciones", "leer-prueba", str(carpeta), "--motivo", "aceptación"
    )
    assert codigo == SALIDA_ERROR
    assert "sellada" in error
    codigo, salida, _ = _correr(proyecto, capsys, "registro", "ver", "accesos")
    assert "RECHAZADO" in salida


# CU-05 -----------------------------------------------------------------------------


def test_cu05_protocolo_aprobado_con_huella_inmutable_y_con_r0_y_comparativo(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Protocolo de prueba marcado como no ficticio, solo en esta carpeta temporal, para
    # recorrer el camino real. Sus valores son inventados.
    datos = datos_protocolo_ficticio()
    datos["ficticio"] = False
    archivo = proyecto / "protocolo_prueba.yaml"
    archivo.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")

    codigo, salida, _ = _correr(proyecto, capsys, "protocolo", "borrador", str(archivo))
    assert codigo == SALIDA_CORRECTA
    huella = salida.split("Huella: ")[1].split()[0]
    aprobar = ("protocolo", "aprobar", "1", "--huella", huella, "--responsable", "Equipo")

    codigo, _, error = _correr(proyecto, capsys, *aprobar)
    assert codigo == SALIDA_ERROR
    assert "DP-06" in error  # sin las decisiones registradas no se aprueba

    for codigo_dp in DECISIONES_DEL_PROTOCOLO:
        _correr(
            proyecto,
            capsys,
            "registro",
            "decision",
            "--codigo",
            codigo_dp,
            "--decision",
            "Valor de prueba (EJEMPLO FICTICIO)",
            "--justificacion",
            "Prueba de aceptación en carpeta temporal",
            "--responsable",
            "pruebas",
        )
    codigo, salida, _ = _correr(proyecto, capsys, *aprobar)
    assert codigo == SALIDA_CORRECTA
    assert "Versión 1 aprobada y vigente" in salida

    codigo, salida, _ = _correr(proyecto, capsys, "protocolo", "ver")
    assert "Versión 1: aprobado" in salida
    assert f"Huella: {huella}" in salida
    # El protocolo incluye la regla de R0 y el protocolo comparativo (DP-19 y DP-20).
    assert {"DP-19", "DP-20"} <= set(datos["decisiones"])

    codigo, _, error = _correr(
        proyecto, capsys, "protocolo", "borrador", str(archivo), "--version", "1"
    )
    assert codigo == SALIDA_ERROR
    assert "no puede" in error  # inmutable desde la aprobación

    codigo, salida, _ = _correr(proyecto, capsys, "decisiones")
    assert codigo == SALIDA_CORRECTA
    assert "Decisiones registradas: 9 de 20; abiertas: 11." in salida


def test_cu05_el_ejemplo_ficticio_nunca_se_aprueba(
    proyecto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo, salida, _ = _correr(
        proyecto, capsys, "protocolo", "borrador", str(ARCHIVO_PROTOCOLO_FICTICIO)
    )
    huella = salida.split("Huella: ")[1].split()[0]
    codigo, _, error = _correr(
        proyecto, capsys, "protocolo", "aprobar", "1", "--huella", huella, "--responsable", "E"
    )
    assert codigo == SALIDA_ERROR
    assert "ejemplo ficticio" in error


# PI-11, parte determinista ---------------------------------------------------------


def _ejecucion_completa(
    proyecto: Path, capsys: pytest.CaptureFixture[str], salida: str
) -> tuple[bytes, dict[str, str]]:
    codigo, texto, _ = _correr(
        proyecto, capsys, "objetivo", "construir", *_datos(proyecto), "--salida", salida
    )
    assert codigo == SALIDA_CORRECTA, texto
    codigo, texto, _ = _correr(
        proyecto,
        capsys,
        "poblaciones",
        "construir",
        *_datos(proyecto),
        "--configuracion",
        f"{EJEMPLOS}/poblaciones_ficticio.yaml",
    )
    assert codigo == SALIDA_CORRECTA, texto
    carpetas = sorted((proyecto / "workspace" / "particiones").iterdir())
    manifiesto = json.loads((carpetas[-1] / "particion.json").read_text(encoding="utf-8"))
    return (proyecto / salida).read_bytes(), manifiesto["huellas"]


def test_pi11_dos_ejecuciones_con_la_misma_clave_dan_los_mismos_archivos(
    proyecto: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUFICIENCIA_CLAVE_SEUDONIMO", CLAVE_DE_PRUEBA)
    objetivo_1, huellas_1 = _ejecucion_completa(proyecto, capsys, "data/procesado/uno.csv")
    objetivo_2, huellas_2 = _ejecucion_completa(proyecto, capsys, "data/procesado/dos.csv")
    assert objetivo_1 == objetivo_2
    assert huellas_1 == huellas_2
    assert len(list((proyecto / "workspace" / "particiones").iterdir())) == 2
