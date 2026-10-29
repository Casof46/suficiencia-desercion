"""CU-03 con datos sintéticos (H2.4): servicio y línea de comandos.

El archivo de entrada pasa por la misma importación que H2.3 (marca sintética,
seudonimización y auditoría apta) antes de etiquetarse. La salida nunca muestra la
distribución de los estados de etiqueta (RF-M1-03).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from fixtures.generador_sintetico import generar_historial, sembrar_problemas
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import SolicitudConstruirObjetivo, SolicitudValidarObjetivo
from suficiencia.application.errores import AuditoriaConErrores
from suficiencia.cli import SALIDA_CORRECTA, SALIDA_ERROR, main
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente

DICCIONARIO = Path("config/ejemplos/diccionario_sintetico.yaml")
DEFINICION = Path("config/ejemplos/objetivo_ficticio.yaml")


def _proyecto(tmp_path: Path, raiz: Path, tabla: pd.DataFrame) -> Path:
    for ejemplo in (DICCIONARIO, DEFINICION):
        destino = tmp_path / ejemplo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes((raiz / ejemplo).read_bytes())
    archivo = tmp_path / "data" / "sintetico" / "historial.csv"
    archivo.parent.mkdir(parents=True)
    tabla.to_csv(archivo, index=False)
    return archivo


def _solicitud(archivo: Path, **extra: object) -> SolicitudConstruirObjetivo:
    return SolicitudConstruirObjetivo(
        archivo=archivo,
        diccionario=archivo.parents[2] / DICCIONARIO,
        definicion=DEFINICION,
        clave_efimera=True,
        **extra,
    )


def test_construye_y_guarda_los_estados_sin_identificadores(tmp_path: Path, raiz: Path) -> None:
    tabla = generar_historial(60, semilla=8)
    archivo = _proyecto(tmp_path, raiz, tabla)
    servicio = crear_servicios(tmp_path).datos
    resultado = servicio.construir_objetivo(
        _solicitud(archivo, salida=Path("data/interim/etiquetas.csv"))
    )
    assert resultado.sintetico and resultado.definicion_ficticia
    assert resultado.unidades + resultado.fuera_de_poblacion == tabla["codigo_estudiante"].nunique()
    guardado = pd.read_csv(tmp_path / "data" / "interim" / "etiquetas.csv", dtype=str)
    assert "codigo_estudiante" not in guardado.columns
    assert "seudonimo" in guardado.columns
    assert set(guardado["estado_etiqueta"]) <= {"positivo", "negativo", "no_etiquetable"}
    texto = guardado.to_csv(index=False)
    for codigo in tabla["codigo_estudiante"]:
        assert codigo not in texto


def test_rechaza_datos_no_sinteticos_y_auditorias_no_aptas(tmp_path: Path, raiz: Path) -> None:
    tabla = generar_historial(20, semilla=8)
    tabla.loc[0, "origen_datos"] = "INSTITUCION"
    archivo = _proyecto(tmp_path, raiz, tabla)
    servicio = crear_servicios(tmp_path).datos
    with pytest.raises(DecisionPendiente) as error:
        servicio.construir_objetivo(_solicitud(archivo))
    assert error.value.decision == "DP-02"

    con_problemas, _ = sembrar_problemas(generar_historial(20, semilla=8))
    con_problemas.to_csv(archivo, index=False)
    with pytest.raises(AuditoriaConErrores):
        servicio.construir_objetivo(_solicitud(archivo, salida=Path("data/interim/e.csv")))
    assert not (tmp_path / "data" / "interim" / "e.csv").exists()


def test_sin_definicion_se_detiene_por_dp01_y_no_escribe_fuera_de_data(
    tmp_path: Path, raiz: Path
) -> None:
    archivo = _proyecto(tmp_path, raiz, generar_historial(20, semilla=8))
    servicio = crear_servicios(tmp_path).datos
    solicitud = _solicitud(archivo).model_copy(update={"definicion": None})
    with pytest.raises(DecisionPendiente) as error:
        servicio.construir_objetivo(solicitud)
    assert error.value.decision == "DP-01"
    with pytest.raises(ConfiguracionInvalida, match="fuera de la carpeta data/"):
        servicio.construir_objetivo(_solicitud(archivo, salida=tmp_path / "fuera.csv"))


def test_un_estado_del_diccionario_sin_categoria_se_rechaza(tmp_path: Path, raiz: Path) -> None:
    archivo = _proyecto(tmp_path, raiz, generar_historial(20, semilla=8))
    definicion = tmp_path / DEFINICION
    datos = yaml.safe_load(definicion.read_text(encoding="utf-8"))
    del datos["catalogo_estados"]["traslado"]
    definicion.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfiguracionInvalida, match="traslado"):
        crear_servicios(tmp_path).datos.construir_objetivo(_solicitud(archivo))


def test_validar_resume_los_parametros_de_cada_decision(raiz: Path) -> None:
    servicio = crear_servicios(raiz).datos
    resultado = servicio.validar_objetivo(SolicitudValidarObjetivo(archivo=DEFINICION))
    assert resultado.ficticio
    decisiones = {p.decision for p in resultado.parametros}
    esperadas = {f"DP-01{letra}" for letra in "abcefghijklm"} | {"DP-18"}
    assert decisiones == esperadas
    with pytest.raises(DecisionPendiente):
        servicio.validar_objetivo(SolicitudValidarObjetivo())


def test_la_demostracion_cubre_los_tres_estados(raiz: Path) -> None:
    resultado = crear_servicios(raiz).datos.demostracion_objetivo()
    estados = {caso.estado for caso in resultado.casos}
    assert estados == {"positivo", "negativo", "no_etiquetable"}
    motivos = {caso.motivo for caso in resultado.casos if caso.motivo}
    assert motivos == {"seguimiento_incompleto", "resultado_no_observable"}


def test_linea_de_comandos(tmp_path: Path, raiz: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tabla = generar_historial(40, semilla=8)
    archivo = _proyecto(tmp_path, raiz, tabla)
    base = ["--raiz", str(tmp_path), "objetivo"]

    assert main([*base, "validar"]) == SALIDA_ERROR
    assert "DP-01" in capsys.readouterr().err
    assert main([*base, "validar", str(DEFINICION)]) == SALIDA_CORRECTA
    assert capsys.readouterr().out.startswith("EJEMPLO FICTICIO")

    construir = [*base, "construir", str(archivo), "--diccionario", str(tmp_path / DICCIONARIO)]
    construir += ["--definicion", str(DEFINICION), "--clave-efimera"]
    codigo = main([*construir, "--salida", "data/interim/etiquetas.csv"])
    salida = capsys.readouterr().out
    assert codigo == SALIDA_CORRECTA
    assert salida.startswith("DATOS SINTÉTICOS")
    assert "DEFINICIÓN FICTICIA" in salida
    assert "omitida hasta el sellado" in salida
    for estado in ("positivo", "negativo", "no_etiquetable"):
        assert estado not in salida, "la salida no debe mostrar la distribución de estados"
    for codigo_estudiante in tabla["codigo_estudiante"]:
        assert codigo_estudiante not in salida
    assert (tmp_path / "data" / "interim" / "etiquetas.csv").is_file()

    assert main(["--raiz", str(raiz), "objetivo", "demostracion"]) == SALIDA_CORRECTA
    demostracion = capsys.readouterr().out
    assert demostracion.startswith("DEMOSTRACIÓN")
    assert "MPMMMMMM" in demostracion
