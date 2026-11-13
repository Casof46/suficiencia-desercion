"""Visor de demostración (H2.D): cada página se ejecuta y el sello funciona desde la web.

Se usa el ejecutor de pruebas de Streamlit (``AppTest``), que corre las páginas en
el mismo proceso, sin servidor ni navegador y sin red. Cada prueba trabaja en una
copia temporal del proyecto, para no escribir en workspace/ del repositorio.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from fixtures.generador_sintetico import COHORTES_AMPLIADAS, generar_historial
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import SolicitudConsultarRegistro, SolicitudEntrenar
from suficiencia.ui import presentacion

PAGINAS = (
    "pagina_inicio",
    "pagina_datos",
    "pagina_escenarios",
    "pagina_objetivo",
    "pagina_poblaciones",
    "pagina_validacion",
    "pagina_resultados",
    "pagina_registro",
)


def _pagina(nombre: str) -> None:
    from suficiencia.ui import visor

    getattr(visor, nombre)()


@pytest.fixture
def proyecto(tmp_path: Path, raiz: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copytree(raiz / "config", tmp_path / "config")
    archivo = tmp_path / "data" / "sintetico" / "historial.xlsx"
    archivo.parent.mkdir(parents=True)
    generar_historial(300, semilla=1).to_excel(archivo, index=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _app(nombre: str) -> AppTest:
    return AppTest.from_function(_pagina, args=(nombre,), default_timeout=60)


@pytest.mark.parametrize("nombre", PAGINAS)
def test_cada_pagina_se_ejecuta_con_el_aviso_de_demostracion(proyecto: Path, nombre: str) -> None:
    app = _app(nombre).run()
    assert not app.exception, app.exception
    assert not app.error, [e.value for e in app.error]
    html = " ".join(str(h.proto.body) for h in app.get("html"))
    assert "SINTÉTICOS" in html and "FICTICIAS" in html


def test_sin_historial_la_pagina_de_datos_explica_como_generarlo(
    proyecto: Path,
) -> None:
    (proyecto / "data" / "sintetico" / "historial.xlsx").unlink()
    app = _app("pagina_datos").run()
    assert not app.exception
    assert "generar_sintetico.py" in app.warning[0].value


def test_la_pagina_de_datos_no_muestra_la_distribucion_de_la_clase(proyecto: Path) -> None:
    app = _app("pagina_datos").run()
    textos = " ".join(str(m.value) for m in app.metric) + " ".join(str(m.label) for m in app.metric)
    assert "prevalencia" not in textos.lower()
    assert [m.value for m in app.metric][-1] == "Sí"


def test_la_matriz_de_escenarios_tiene_4_ventanas_y_8_conjuntos(proyecto: Path) -> None:
    app = _app("pagina_escenarios").run()
    matriz = app.dataframe[0].value
    assert list(matriz.index) == ["T0", "T1", "T2", "T3"]
    assert len(matriz.columns) == 8
    assert app.success, "Debe informar la verificación anti-fuga"


def test_el_sello_rechaza_la_lectura_desde_el_visor_y_la_registra(proyecto: Path) -> None:
    app = _app("pagina_poblaciones").run()
    app.button[0].click().run()
    assert not app.exception and not app.error
    etiquetas = {m.label: m.value for m in app.metric}
    assert etiquetas["Prueba (SELLADA)"] == "42"
    # Solo desarrollo: ninguna fila de la tabla de seguimiento oculta la prueba,
    # pero ninguna tabla describe eventos de la prueba.
    poblaciones = app.dataframe[1].value
    assert set(poblaciones["Diseño"]) == {"D1", "D2", "D3"}

    app.button[1].click().run()
    assert "sellada" in app.error[0].value

    accesos = (
        crear_servicios(proyecto)
        .reportes.consultar(SolicitudConsultarRegistro(tipo="accesos"))
        .registros
    )
    assert len(accesos) == 1
    assert accesos[0].contenido["operacion"] == "consulta_desde_el_visor"
    assert accesos[0].contenido["permitido"] is False


def test_el_registro_muestra_el_intento_rechazado(proyecto: Path) -> None:
    app = _app("pagina_poblaciones").run()
    app.button[0].click().run()
    app.button[1].click().run()
    registro = _app("pagina_registro").run()
    tabla = registro.dataframe[0].value
    assert list(tabla["Resultado"]) == ["RECHAZADO"]
    assert {m.label: m.value for m in registro.metric}["Integridad"] == "correcta"


# --- Presentación, sin Streamlit ------------------------------------------------------


def test_la_linea_de_tiempo_marca_evento_y_horizonte(proyecto: Path) -> None:
    demostracion = crear_servicios(proyecto).datos.demostracion_objetivo()
    caso = next(c for c in demostracion.casos if c.periodo_evento == 3)
    html = presentacion.linea_de_tiempo(caso, demostracion.horizonte_periodos)
    assert html.count("suf-evento") == 1
    assert 'title="Periodo 3: No matriculado"' in html
    assert html.count("suf-horizonte") == 1


def test_el_resultado_de_un_caso_se_redacta_en_espanol(proyecto: Path) -> None:
    demostracion = crear_servicios(proyecto).datos.demostracion_objetivo()
    textos = {presentacion.resultado_caso(c) for c in demostracion.casos}
    assert "Deserta (evento en el periodo 3)" in textos
    assert "No etiquetable: seguimiento incompleto" in textos


def test_sin_historial_ampliado_la_pagina_de_resultados_explica_como_generarlo(
    proyecto: Path,
) -> None:
    app = _app("pagina_resultados").run()
    assert not app.exception
    assert "--ampliado" in app.warning[0].value
    assert not app.button or app.button[0].label != "Ejecutar la demostración"


def test_la_pagina_de_resultados_muestra_graficos_rotulados_y_descargas(proyecto: Path) -> None:
    """F3.7: demostración completa desde el visor, con gráficos Plotly y el reporte (PI-16)."""
    archivo = proyecto / "data" / "sintetico" / "ampliado.csv"
    generar_historial(700, semilla=11, cohortes=COHORTES_AMPLIADAS).to_csv(archivo, index=False)
    app = AppTest.from_function(_pagina, args=("pagina_resultados",), default_timeout=300).run()
    assert not app.exception, app.exception
    app.button[0].click().run()
    assert not app.exception, app.exception
    assert not app.error, [e.value for e in app.error]
    graficos = app.get("plotly_chart")
    assert len(graficos) == 4
    for grafico in graficos:
        figura = json.loads(grafico.proto.spec)["layout"]
        assert figura["title"]["text"].startswith("DATOS SINTÉTICOS · ")
    descargas = [d.proto.label for d in app.get("download_button")]
    assert descargas == ["Descargar reporte.md", "Descargar resultados.xlsx"]
    textos = " ".join(str(m.value) for m in app.markdown)
    assert "No se declara superioridad" in textos
    # Nada llegó al registro del proyecto: la demostración usa un proyecto temporal.
    registro = crear_servicios(proyecto).reportes.consultar(
        SolicitudConsultarRegistro(tipo="experimentos")
    )
    assert registro.registros == ()


def test_la_pagina_de_validacion_compara_escenarios_con_graficos_rotulados(
    proyecto: Path,
) -> None:
    """F4.1 (RF-M4-10, RF-M4-14): matriz ventana × conjunto y familias de cada escenario."""
    archivo = proyecto / "data" / "sintetico" / "ampliado.csv"
    generar_historial(700, semilla=11, cohortes=COHORTES_AMPLIADAS).to_csv(archivo, index=False)
    ejemplos = proyecto / "config" / "ejemplos"
    crear_servicios(proyecto).experimentos.entrenar(
        SolicitudEntrenar(
            archivo=archivo,
            diccionario=ejemplos / "diccionario_sintetico.yaml",
            definicion=ejemplos / "objetivo_ficticio.yaml",
            poblaciones=ejemplos / "poblaciones_ampliado_ficticio.yaml",
            escenarios=ejemplos / "escenarios_ficticio.yaml",
            experimentos=ejemplos / "experimentos_ficticio.yaml",
            clave_efimera=True,
            seleccion_escenarios=("T0|A", "T1|A"),
            seleccion_familias=("lr", "rf"),
        )
    )
    app = AppTest.from_function(_pagina, args=("pagina_validacion",), default_timeout=120).run()
    assert not app.exception, app.exception
    app.button[0].click().run()
    assert not app.exception, app.exception
    assert not app.error, [e.value for e in app.error]
    graficos = app.get("plotly_chart")
    assert len(graficos) == 2
    titulos = [json.loads(g.proto.spec)["layout"]["title"]["text"] for g in graficos]
    assert all(t.startswith("DATOS SINTÉTICOS · ") for t in titulos)
    assert "por ventana y conjunto" in titulos[0] and "las familias de" in titulos[1]
    assert [d.proto.label for d in app.get("download_button")] == [
        "Descargar reporte.md",
        "Descargar resultados.xlsx",
    ]
    assert "4 corridas de 2 escenarios" in " ".join(str(m.value) for m in app.markdown)
