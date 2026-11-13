"""Exportación del reporte de resultados y rótulo en el registro (F3.7 y F4.1).

PI-16: con datos sintéticos, el rótulo está en las exportaciones (texto, cada CSV y
cada hoja del Excel) y en la exportación de experimentos del registro; una exportación
sin rótulo se rechaza y no escribe nada. Resultados escritos a mano (EJEMPLO FICTICIO).
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import pandas as pd
import pytest

from fixtures import resultados_ficticios as ficticios
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    SolicitudExportarRegistro,
    SolicitudExportarResultados,
    SolicitudResultadosRegistrados,
    TablaReporte,
)
from suficiencia.application.registro_corridas import RegistradorCorridas
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.huella import Huella
from suficiencia.domain.trazabilidad.registros import ModoExperimento
from suficiencia.domain.trazabilidad.rotulo import (
    CAMPO_ORIGEN,
    LEYENDA_SINTETICA,
    ROTULO_SINTETICO,
    RotuloFaltante,
)
from suficiencia.persistence.entorno import CapturadorEntornoLocal


@pytest.fixture
def proyecto(tmp_path: Path, raiz: Path) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(raiz / "config" / "proyecto.yaml", tmp_path / "config" / "proyecto.yaml")
    shutil.copy(raiz / "requirements.lock", tmp_path / "requirements.lock")
    return tmp_path


def test_pi16_la_exportacion_lleva_el_rotulo_en_cada_archivo(proyecto: Path) -> None:
    reportes = crear_servicios(proyecto).reportes
    reporte = reportes.reporte_resultados(
        ficticios.evaluacion(), ficticios.comparacion(), ficticios.explicacion()
    )
    exportado = reportes.exportar_resultados(
        SolicitudExportarResultados(reporte=reporte, carpeta=Path("reports/demostracion"))
    )
    carpeta = Path(exportado.carpeta)
    assert carpeta == proyecto / "reports" / "demostracion"
    assert set(exportado.archivos) == {
        "reporte.md",
        "resultados.xlsx",
        *(f"{t.nombre}.csv" for t in reporte.tablas),
    }
    for nombre, huella in exportado.archivos.items():
        assert Huella.de_bytes((carpeta / nombre).read_bytes()).valor == huella
    texto = (carpeta / "reporte.md").read_text(encoding="utf-8")
    assert texto.splitlines()[0] == f"> **{LEYENDA_SINTETICA}**"
    for tabla in reporte.tablas:
        csv = pd.read_csv(carpeta / f"{tabla.nombre}.csv")
        assert set(csv[CAMPO_ORIGEN]) == {ROTULO_SINTETICO}
    hojas = pd.read_excel(carpeta / "resultados.xlsx", sheet_name=None)
    assert set(hojas) == {t.nombre for t in reporte.tablas}
    assert all(set(h[CAMPO_ORIGEN]) == {ROTULO_SINTETICO} for h in hojas.values())
    # En memoria, para las descargas del visor: el mismo contenido de texto.
    contenido = reportes.contenido_resultados(reporte)
    assert contenido["reporte.md"].decode("utf-8") == texto
    assert set(pd.read_csv(io.BytesIO(contenido["controles.csv"]))[CAMPO_ORIGEN]) == {
        ROTULO_SINTETICO
    }


def test_pi16_un_reporte_sin_rotulo_no_se_exporta_ni_escribe_nada(proyecto: Path) -> None:
    reportes = crear_servicios(proyecto).reportes
    reporte = reportes.reporte_resultados(ficticios.evaluacion(), ficticios.comparacion(), None)
    sin_rotulo = reporte.model_copy(
        update={
            "tablas": (
                TablaReporte(nombre="metricas", titulo="t", columnas=("auc",), filas=((0.7,),)),
            )
        }
    )
    with pytest.raises(RotuloFaltante):
        reportes.exportar_resultados(
            SolicitudExportarResultados(reporte=sin_rotulo, carpeta=Path("reports/x"))
        )
    with pytest.raises(RotuloFaltante):
        reportes.contenido_resultados(sin_rotulo)
    assert not (proyecto / "reports" / "x").exists()


def test_la_exportacion_solo_va_a_reports_y_no_sobrescribe(proyecto: Path) -> None:
    reportes = crear_servicios(proyecto).reportes
    reporte = reportes.reporte_resultados(ficticios.evaluacion(), ficticios.comparacion(), None)
    with pytest.raises(ConfiguracionInvalida, match="fuera de la carpeta de reportes"):
        reportes.exportar_resultados(
            SolicitudExportarResultados(reporte=reporte, carpeta=Path("data/x"))
        )
    solicitud = SolicitudExportarResultados(reporte=reporte, carpeta=Path("reports/una"))
    reportes.exportar_resultados(solicitud)
    with pytest.raises(ConfiguracionInvalida, match="no se sobrescriben"):
        reportes.exportar_resultados(solicitud)


def test_pi16_la_exportacion_de_experimentos_del_registro_lleva_el_rotulo(
    proyecto: Path,
) -> None:
    servicios = crear_servicios(proyecto)
    registrador = RegistradorCorridas(
        servicios.reportes.repositorio(), CapturadorEntornoLocal(proyecto)
    )
    for configuracion in ({"tipo": "prueba", CAMPO_ORIGEN: "sintetico"}, {"tipo": "antigua"}):
        registrador.ejecutar(
            lambda: {},
            modo=ModoExperimento.EXPLORATORIO,
            configuracion=configuracion,
            semillas={},
            huella_datos=None,
            version_protocolo=None,
        )
    exportacion = servicios.reportes.exportar(
        SolicitudExportarRegistro(tipo="experimentos", salida=Path("reports/experimentos.csv"))
    )
    tabla = pd.read_csv(exportacion.archivo)
    # La corrida sin origen declarado también se rotula como sintética.
    assert list(tabla[CAMPO_ORIGEN]) == [ROTULO_SINTETICO, ROTULO_SINTETICO]


def test_una_comparacion_sin_resultado_completo_pide_repetirla(proyecto: Path) -> None:
    """F4.1: las comparaciones registradas antes de F4.1 no guardan todo su resultado."""
    servicios = crear_servicios(proyecto)
    registrador = RegistradorCorridas(
        servicios.reportes.repositorio(), CapturadorEntornoLocal(proyecto)
    )
    evaluacion = registrador.ejecutar(
        lambda: {
            "configuraciones": [],
            "regla": {"estado": "ningun_escenario_cumple", "escenario": None, "detalle": []},
        },
        modo=ModoExperimento.EXPLORATORIO,
        configuracion={"tipo": "evaluacion_final", "configuraciones": [], "ficticio": True},
        semillas={},
        huella_datos=None,
        version_protocolo="1",
    ).contenido["identificador"]
    solicitud = SolicitudResultadosRegistrados(evaluacion=evaluacion)
    registrados = servicios.evaluacion_final.resultados_registrados(solicitud)
    assert registrados.comparacion is None and registrados.explicacion is None
    assert registrados.evaluacion.origen_datos == "sintetico"  # sin origen declarado
    registrador.ejecutar(
        lambda: {"estado": "C5_ningun_escenario_suficiente"},
        modo=ModoExperimento.EXPLORATORIO,
        configuracion={"tipo": "evaluacion_comparativa", "evaluacion_final": evaluacion},
        semillas={},
        huella_datos=None,
        version_protocolo="1",
    )
    with pytest.raises(ConfiguracionInvalida, match="antes de F4.1"):
        servicios.evaluacion_final.resultados_registrados(solicitud)
