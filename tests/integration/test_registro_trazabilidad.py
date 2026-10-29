"""Registro SQLite, entorno, corridas y exportación de punta a punta (H2.7).

PI-03, PI-04 y PI-12 de la especificación, con corridas simuladas (sin modelos).
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    SolicitudConsultarRegistro,
    SolicitudExportarRegistro,
    SolicitudRegistrarDecision,
)
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.huella import Huella
from suficiencia.domain.trazabilidad.filtro import IdentificadorEnExportacion
from suficiencia.domain.trazabilidad.registros import (
    ModoExperimento,
    RegistroAcceso,
    RegistroDecision,
    TipoRegistro,
    huella_encadenada,
    json_canonico,
    verificar_cadena,
)
from suficiencia.persistence.entorno import CapturadorEntornoLocal
from suficiencia.persistence.exportacion import exportar_tabla
from suficiencia.persistence.repositorio_sqlite import RepositorioSqlite


@pytest.fixture
def proyecto(tmp_path: Path, raiz: Path) -> Path:
    """Proyecto temporal con la configuración y el bloqueo del repositorio."""
    (tmp_path / "config").mkdir()
    shutil.copy(raiz / "config" / "proyecto.yaml", tmp_path / "config" / "proyecto.yaml")
    shutil.copy(raiz / "requirements.lock", tmp_path / "requirements.lock")
    return tmp_path


def _decision(numero: int) -> RegistroDecision:
    return RegistroDecision(f"DP-{numero:02d}", "decisión de prueba", "prueba", "pruebas")


def test_el_registro_agrega_en_orden_y_su_cadena_es_valida(tmp_path: Path) -> None:
    repositorio = RepositorioSqlite(tmp_path / "workspace" / "registro.sqlite")
    for numero in (1, 2, 3):
        repositorio.agregar(_decision(numero))
    repositorio.agregar(RegistroAcceso("evaluacion_final", "prueba", False))
    decisiones = repositorio.listar(TipoRegistro.DECISION)
    assert [d.numero for d in decisiones] == [1, 2, 3]
    assert [d.contenido["codigo"] for d in decisiones] == ["DP-01", "DP-02", "DP-03"]
    assert verificar_cadena(TipoRegistro.DECISION, decisiones) == ()
    assert len(repositorio.listar(TipoRegistro.ACCESO)) == 1
    assert repositorio.listar(TipoRegistro.EXPERIMENTO) == []


@pytest.mark.parametrize(
    "sentencia",
    ["UPDATE decisiones SET contenido = '{}' WHERE numero = 1", "DELETE FROM decisiones"],
)
def test_los_registros_solo_admiten_agregar(tmp_path: Path, sentencia: str) -> None:
    archivo = tmp_path / "registro.sqlite"
    RepositorioSqlite(archivo).agregar(_decision(1))
    conexion = sqlite3.connect(archivo)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="solo admite agregar"):
            conexion.execute(sentencia)
    finally:
        conexion.close()
    assert len(RepositorioSqlite(archivo).listar(TipoRegistro.DECISION)) == 1


def test_una_modificacion_fuera_del_programa_se_detecta(tmp_path: Path) -> None:
    """Aunque alguien quite los disparadores, la cadena de huellas delata el cambio."""
    archivo = tmp_path / "registro.sqlite"
    repositorio = RepositorioSqlite(archivo)
    for numero in (1, 2):
        repositorio.agregar(_decision(numero))
    conexion = sqlite3.connect(archivo)
    try:
        conexion.execute("DROP TRIGGER decisiones_sin_modificar")
        conexion.execute(
            "UPDATE decisiones SET contenido = replace(contenido, 'prueba', 'otra') "
            "WHERE numero = 1"
        )
        conexion.commit()
    finally:
        conexion.close()
    problemas = verificar_cadena(TipoRegistro.DECISION, repositorio.listar(TipoRegistro.DECISION))
    assert [(p.numero, p.descripcion) for p in problemas] == [(1, "su contenido fue modificado")]


def test_rehacer_las_huellas_de_un_registro_modificado_tambien_se_detecta(tmp_path: Path) -> None:
    """Quien recalcula la huella del registro alterado y corrige el enlace del siguiente
    deja igualmente una huella que no cuadra: la del siguiente incluye la anterior."""
    archivo = tmp_path / "registro.sqlite"
    repositorio = RepositorioSqlite(archivo)
    for numero in (1, 2, 3):
        repositorio.agregar(_decision(numero))
    primero = repositorio.listar(TipoRegistro.DECISION)[0]
    contenido = {**primero.contenido, "decision": "alterada"}
    nueva = huella_encadenada(primero.huella_anterior, primero.fecha, json_canonico(contenido))
    conexion = sqlite3.connect(archivo)
    try:
        conexion.execute("DROP TRIGGER decisiones_sin_modificar")
        conexion.execute(
            "UPDATE decisiones SET contenido = ?, huella = ? WHERE numero = 1",
            (json_canonico(contenido), nueva),
        )
        conexion.execute("UPDATE decisiones SET huella_anterior = ? WHERE numero = 2", (nueva,))
        conexion.commit()
    finally:
        conexion.close()
    problemas = verificar_cadena(TipoRegistro.DECISION, repositorio.listar(TipoRegistro.DECISION))
    assert [(p.numero, p.descripcion) for p in problemas] == [(2, "su contenido fue modificado")]


def test_el_archivo_no_queda_bloqueado_entre_operaciones(tmp_path: Path) -> None:
    archivo = tmp_path / "registro.sqlite"
    repositorio = RepositorioSqlite(archivo)
    repositorio.agregar(_decision(1))
    repositorio.listar(TipoRegistro.DECISION)
    archivo.unlink()
    assert not archivo.exists()


# Entorno (RNF-17) -------------------------------------------------------------


def test_el_entorno_registra_python_bloqueo_y_paralelismo(proyecto: Path) -> None:
    entorno = CapturadorEntornoLocal(proyecto).capturar()
    assert entorno.python.count(".") == 2
    assert (
        entorno.huella_bloqueo
        == Huella.de_bytes((proyecto / "requirements.lock").read_bytes()).valor
    )
    assert "OMP_NUM_THREADS" in entorno.hilos
    assert entorno.paquetes["suficiencia"]
    assert entorno.commit is None
    assert entorno.cambios_sin_commit is None


@pytest.mark.requiere_git
def test_el_entorno_registra_el_commit(proyecto: Path) -> None:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git no está instalado.")
    identidad = ["-c", "user.name=Prueba", "-c", "user.email=prueba@example.invalid"]
    for argumentos in (["init", "-q"], ["add", "-A"], [*identidad, "commit", "-q", "-m", "x"]):
        subprocess.run([git, *argumentos], cwd=proyecto, check=True, capture_output=True)
    entorno = CapturadorEntornoLocal(proyecto).capturar()
    assert entorno.commit is not None
    assert len(entorno.commit) == 40
    assert entorno.cambios_sin_commit is False
    (proyecto / "nuevo.txt").write_text("x", encoding="utf-8")
    assert CapturadorEntornoLocal(proyecto).capturar().cambios_sin_commit is True


# PI-03 y PI-12: corridas registradas ------------------------------------------


def test_pi03_y_pi12_las_corridas_exitosas_y_fallidas_quedan_registradas(proyecto: Path) -> None:
    repositorio = RepositorioSqlite(proyecto / "workspace" / "registro.sqlite")
    registrador = RegistradorCorridas(repositorio, CapturadorEntornoLocal(proyecto))

    def exitosa() -> dict[str, Any]:
        return {"metrica_simulada": 0.5}

    def fallida() -> dict[str, Any]:
        raise ValueError("falla simulada")

    comunes: dict[str, Any] = {
        "configuracion": {"algoritmo": "simulado", "parametros": {"a": 1}},
        "semillas": {"global": 7},
        "huella_datos": "a" * 64,
    }
    exito = registrador.ejecutar(
        exitosa, modo=ModoExperimento.CONFIRMATORIO, version_protocolo="v1-prueba", **comunes
    )
    falla = registrador.ejecutar(
        fallida, modo=ModoExperimento.EXPLORATORIO, version_protocolo=None, **comunes
    )

    experimentos = repositorio.listar(TipoRegistro.EXPERIMENTO)
    assert [e.numero for e in experimentos] == [exito.numero, falla.numero] == [1, 2]
    primero, segundo = (e.contenido for e in experimentos)
    # PI-03: modo, protocolo, configuración, semilla, entorno, huella de datos y commit.
    assert primero["modo"] == "confirmatorio"
    assert primero["version_protocolo"] == "v1-prueba"
    assert primero["configuracion"] == {"algoritmo": "simulado", "parametros": {"a": 1}}
    assert primero["semillas"] == {"global": 7}
    assert primero["huella_datos"] == "a" * 64
    assert primero["entorno"]["huella_bloqueo"]
    assert "commit" in primero["entorno"]
    assert primero["estado"] == "exitosa"
    assert primero["resultados"] == {"metrica_simulada": 0.5}
    # PI-12: la corrida fallida queda registrada junto con la exitosa.
    assert segundo["estado"] == "fallida"
    assert segundo["error"] == "ValueError: falla simulada"
    assert verificar_cadena(TipoRegistro.EXPERIMENTO, experimentos) == ()


# Servicio y PI-04 -------------------------------------------------------------


def test_el_servicio_registra_consulta_verifica_y_exporta(proyecto: Path) -> None:
    reportes = crear_servicios(proyecto).reportes
    reportes.registrar_decision(
        SolicitudRegistrarDecision(
            codigo="DP-16",
            decision="SQLite",
            justificacion="prueba",
            responsable="pruebas",
            observaciones="pendiente de confirmación",
        )
    )
    consulta = reportes.consultar(SolicitudConsultarRegistro(tipo="decisiones"))
    assert Path(consulta.archivo) == proyecto / "workspace" / "registro.sqlite"
    assert consulta.registros[0].contenido["codigo"] == "DP-16"
    integridad = reportes.verificar()
    assert integridad.correcto
    assert integridad.registros_por_tipo == {"experimentos": 0, "decisiones": 1, "accesos": 0}

    for extension in (".csv", ".xlsx"):
        exportacion = reportes.exportar(
            SolicitudExportarRegistro(tipo="decisiones", salida=Path(f"reports/d{extension}"))
        )
        archivo = Path(exportacion.archivo)
        tabla = pd.read_csv(archivo) if extension == ".csv" else pd.read_excel(archivo)
        assert list(tabla["codigo"]) == ["DP-16"]
        assert exportacion.huella == Huella.de_bytes(archivo.read_bytes()).valor


def test_la_exportacion_solo_va_a_la_carpeta_de_reportes(proyecto: Path) -> None:
    reportes = crear_servicios(proyecto).reportes
    with pytest.raises(ConfiguracionInvalida, match="fuera de la carpeta de reportes"):
        reportes.exportar(SolicitudExportarRegistro(tipo="decisiones", salida=Path("data/x.csv")))


def test_pi04_ninguna_exportacion_contiene_columnas_identificadoras(tmp_path: Path) -> None:
    tabla = pd.DataFrame({"codigo_estudiante": ["00012345"], "ciclo": [1]})
    with pytest.raises(IdentificadorEnExportacion, match="codigo_estudiante"):
        exportar_tabla(tabla, tmp_path / "x.csv")
    assert not (tmp_path / "x.csv").exists()
    with pytest.raises(IdentificadorEnExportacion, match="matricula"):
        exportar_tabla(
            tabla.drop(columns="codigo_estudiante").assign(matricula="1"),
            tmp_path / "y.csv",
            ["matricula"],
        )
    huella = exportar_tabla(tabla.drop(columns="codigo_estudiante"), tmp_path / "z.csv")
    assert huella.valor == Huella.de_bytes((tmp_path / "z.csv").read_bytes()).valor
    with pytest.raises(ConfiguracionInvalida, match="no se sobrescriben"):
        exportar_tabla(tabla.drop(columns="codigo_estudiante"), tmp_path / "z.csv")


def test_pi04_las_exportaciones_del_registro_no_tienen_identificadores(proyecto: Path) -> None:
    reportes = crear_servicios(proyecto).reportes
    reportes.demostracion()
    reportes.registrar_decision(
        SolicitudRegistrarDecision(
            codigo="DP-16", decision="SQLite", justificacion="j", responsable="r"
        )
    )
    exportacion = reportes.exportar(
        SolicitudExportarRegistro(tipo="decisiones", salida=Path("reports/decisiones.csv"))
    )
    columnas = set(pd.read_csv(exportacion.archivo).columns)
    assert columnas.isdisjoint({"codigo_estudiante", "dni", "nombre", "correo"})


def test_la_demostracion_usa_un_registro_aparte(proyecto: Path) -> None:
    reportes = crear_servicios(proyecto).reportes
    resultado = reportes.demostracion()
    assert Path(resultado.archivo).name == "registro_demostracion.sqlite"
    assert [r.contenido["estado"] for r in resultado.registros] == ["exitosa", "fallida"]
    assert reportes.verificar().registros_por_tipo["experimentos"] == 0
