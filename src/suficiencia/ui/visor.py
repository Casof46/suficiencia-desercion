"""Visor de demostración local (H2.D).

Se ejecuta desde la raíz del repositorio:

    .venv\\Scripts\\python -m streamlit run src\\suficiencia\\ui\\visor.py

Muestra, en el navegador y solo en ``localhost``, lo que el motor ya hace con los
datos sintéticos y los ejemplos ficticios (H2.2 a H2.5 y H2.7). No es la interfaz
definitiva del proyecto: no elige escenarios, no entrena modelos y no lee datos
reales (el motor rechaza cualquier archivo sin la marca sintética, DP-02).

Solo usa la capa de aplicación (RF-UI-02, contrato ``ui-solo-aplicacion``).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import streamlit as st

from suficiencia.application.composicion import Servicios, crear_servicios
from suficiencia.application.contratos import (
    ResultadoDefinicionObjetivo,
    ResultadoDemostracionObjetivo,
    ResultadoEscenarios,
    ResultadoImportacion,
    SolicitudConstruirPoblaciones,
    SolicitudConsultarRegistro,
    SolicitudGenerarEscenarios,
    SolicitudImportarDataset,
    SolicitudLeerPrueba,
    SolicitudValidarObjetivo,
)
from suficiencia.application.errores import AccesoPruebaDenegado, ErrorSuficiencia
from suficiencia.ui import presentacion as p

HISTORIAL = Path("data/sintetico/historial.xlsx")
DICCIONARIO = Path("config/ejemplos/diccionario_sintetico.yaml")
OBJETIVO = Path("config/ejemplos/objetivo_ficticio.yaml")
ESCENARIOS = Path("config/ejemplos/escenarios_ficticio.yaml")
POBLACIONES = Path("config/ejemplos/poblaciones_ficticio.yaml")

R = TypeVar("R")

_ESTILOS = """
<style>
.suf-aviso {border-left: 4px solid #C8553D; background: #FBEDEA; color: #3A1F1A;
  padding: .7rem 1rem; border-radius: 2px; font-size: .92rem; margin-bottom: 1.2rem;}
.suf-linea {display: flex; gap: 3px; margin: .15rem 0 .2rem;}
.suf-celda {display: inline-flex; align-items: center; justify-content: center;
  width: 1.9rem; height: 1.9rem; border-radius: 3px; color: #fff; font-weight: 600;
  font-size: .85rem; box-sizing: border-box;}
.suf-vacia {border: 1px dashed #B5BAC1;}
.suf-horizonte {box-shadow: inset 0 -4px 0 #1B2430;}
.suf-evento {outline: 3px solid #1B2430; outline-offset: 1px;}
.suf-leyenda {display: flex; flex-wrap: wrap; gap: .4rem 1.1rem; font-size: .85rem;
  margin: .3rem 0 1rem;}
.suf-ley {display: inline-flex; align-items: center; gap: .35rem;}
.suf-ley .suf-celda {width: 1.3rem; height: 1.3rem; font-size: .7rem;}
</style>
"""


def _raiz() -> Path:
    """Carpeta desde la que se lanzó el visor: la raíz del repositorio."""
    return Path.cwd()


@st.cache_resource
def _servicios(raiz: str) -> Servicios:
    return crear_servicios(Path(raiz))


def _ejecutar(operacion: Callable[[], R]) -> R | None:
    """Muestra los errores del motor tal como los redacta (causa y acción sugerida)."""
    try:
        return operacion()
    except ErrorSuficiencia as error:
        st.error(f"{error.causa}\n\n**Acción sugerida:** {error.accion}")
        return None


def _colores() -> list[Any]:
    """Colores de D1, D2 y D3 en el formato que espera el gráfico de Streamlit."""
    return list(p.COLORES_DISENOS)


def _encabezado(titulo: str, descripcion: str) -> None:
    st.html(_ESTILOS)
    st.title(titulo)
    st.html(f'<div class="suf-aviso">{p.AVISO_DEMOSTRACION}</div>')
    st.write(descripcion)


def _falta_historial() -> bool:
    if (_raiz() / HISTORIAL).exists():
        return False
    st.warning(
        f"No existe {HISTORIAL}. Genérelo desde la raíz del repositorio con:\n\n"
        "`.venv\\Scripts\\python scripts\\generar_sintetico.py --semilla 1 "
        "--salida data\\sintetico\\historial.xlsx`"
    )
    return True


# --- Páginas -----------------------------------------------------------------------


def pagina_inicio() -> None:
    _encabezado(
        "Suficiencia de información para la detección temprana de la deserción",
        "El artefacto de la investigación es un **método temporal**: determinar en qué "
        "momento de la trayectoria (T0 admisión, T1 a T3 final de cada ciclo) y con qué "
        "bloques de información (A académica, F financiera, S socioeconómica, "
        "B conductual) el riesgo de deserción puede detectarse cumpliendo criterios "
        "definidos de antemano. Este visor muestra las partes del motor ya construidas.",
    )
    servicios = _servicios(str(_raiz()))
    estado = servicios.proyecto.estado()
    casos = p.tabla_casos_de_uso(estado)
    col1, col2, col3 = st.columns(3)
    col1.metric("Versión del motor", estado.version_paquete)
    col2.metric("Casos de uso", len(casos))
    col3.metric("Con avance disponible", int((casos["Ya disponible"] != "—").sum()))
    st.subheader("Casos de uso y en qué hito se construyen")
    st.dataframe(casos, hide_index=True, width="stretch")
    st.caption(
        "Ninguno figura como completo: los hitos construidos aportan partes de cada caso "
        "de uso. Los modelos, la regla de suficiencia y la interpretabilidad vienen después."
    )


def pagina_datos() -> None:
    _encabezado(
        "Datos: importación y auditoría",
        "El historial sintético se lee, se seudonimiza con una clave efímera que no se "
        "guarda y se audita columna por columna. El motor rechaza cualquier archivo sin "
        "la marca de datos sintéticos (DP-02) y no muestra la distribución de la clase "
        "antes de sellar la prueba (RF-M1-03).",
    )
    if _falta_historial():
        return
    servicios = _servicios(str(_raiz()))

    def importar() -> ResultadoImportacion:
        return servicios.datos.importar_dataset(
            SolicitudImportarDataset(
                archivo=_raiz() / HISTORIAL, diccionario=_raiz() / DICCIONARIO, clave_efimera=True
            )
        )

    resultado = _ejecutar(importar)
    if resultado is None:
        return
    informe = resultado.informe
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas", informe.n_filas)
    col2.metric("Columnas", informe.n_columnas)
    col3.metric("Claves duplicadas", informe.duplicados_clave)
    col4.metric("Apto para el siguiente módulo", "Sí" if informe.apto_para_m2 else "No")
    st.write(f"Columnas seudonimizadas: {', '.join(resultado.columnas_seudonimizadas)}")
    st.dataframe(p.tabla_auditoria(resultado), hide_index=True, width="stretch")
    for alerta in informe.alertas:
        st.info(alerta)
    for error in informe.errores_criticos:
        st.error(error)
    with st.expander("Huellas SHA-256 (trazabilidad)"):
        st.code(
            f"Archivo fuente:     {resultado.huella_fuente}\n"
            f"Dataset procesado:  {resultado.huella_procesado or '—'}"
        )


def pagina_escenarios() -> None:
    _encabezado(
        "Escenarios: 4 ventanas × 8 conjuntos",
        "Cada escenario combina una ventana temporal con un conjunto de bloques. El motor "
        "solo admite una variable en una ventana si ya está disponible en ese momento "
        "(ventana mínima del diccionario) y verifica que no haya fuga temporal "
        "(RF-M2-04). Un escenario es no factible si algún bloque no tiene variables.",
    )
    servicios = _servicios(str(_raiz()))

    def generar() -> ResultadoEscenarios:
        return servicios.escenarios.generar_escenarios(
            SolicitudGenerarEscenarios(
                configuracion=_raiz() / ESCENARIOS, diccionario=_raiz() / DICCIONARIO
            )
        )

    resultado = _ejecutar(generar)
    if resultado is None:
        return
    factibles = sum(e.factible for e in resultado.escenarios)
    col1, col2, col3 = st.columns(3)
    col1.metric("Escenarios", len(resultado.escenarios))
    col2.metric("Factibles", factibles)
    col3.metric("Variables evaluadas", resultado.variables_evaluadas)
    st.dataframe(p.matriz_escenarios(resultado), width="stretch")
    if resultado.sin_fuga:
        st.success(
            "Verificación anti-fuga correcta: ninguna variable aparece en una ventana "
            "anterior a su ventana mínima."
        )
    with st.expander("Variables de cada escenario factible"):
        for escenario in resultado.escenarios:
            if escenario.factible:
                st.write(
                    f"**{escenario.ventana} · {escenario.conjunto}**: "
                    f"{', '.join(escenario.variables)}"
                )


def pagina_objetivo() -> None:
    _encabezado(
        "Objetivo: ¿desertó, no desertó o no se puede saber?",
        "Cada estudiante recibe un estado de etiqueta según reglas configurables, una por "
        "cada punto de DP-01. Aquí se aplican las reglas del ejemplo ficticio a diez "
        "historiales escritos a mano.",
    )
    servicios = _servicios(str(_raiz()))

    def demostrar() -> ResultadoDemostracionObjetivo:
        return servicios.datos.demostracion_objetivo()

    demostracion = _ejecutar(demostrar)
    if demostracion is None:
        return
    st.write(
        f"Definición: **{demostracion.definicion}**, con un horizonte de "
        f"{demostracion.horizonte_periodos} periodos desde el ingreso. La raya inferior "
        "marca el fin del horizonte y el recuadro, el periodo del evento."
    )
    st.html(_ESTILOS + p.leyenda_estados())
    for caso in demostracion.casos:
        izquierda, derecha = st.columns([3, 2], vertical_alignment="center")
        with izquierda:
            st.markdown(f"**{caso.nombre}**")
            st.html(_ESTILOS + p.linea_de_tiempo(caso, demostracion.horizonte_periodos))
        derecha.write(p.resultado_caso(caso))

    def validar() -> ResultadoDefinicionObjetivo:
        return servicios.datos.validar_objetivo(
            SolicitudValidarObjetivo(archivo=_raiz() / OBJETIVO)
        )

    definicion = _ejecutar(validar)
    if definicion is not None:
        with st.expander("Reglas del ejemplo ficticio, con su código de decisión"):
            st.dataframe(
                [
                    {"Decisión": r.decision, "Parámetro": r.parametro, "Valor": r.valor}
                    for r in definicion.parametros
                ],
                hide_index=True,
                width="stretch",
            )


def pagina_poblaciones() -> None:
    _encabezado(
        "Poblaciones, partición por cohortes y sello de la prueba",
        "Las cohortes se reparten en desarrollo, prueba, piloto y excluidas; la prueba "
        "siempre es posterior. La prueba queda **sellada**: solo la evaluación final, "
        "que todavía no existe, podrá leerla. De ella solo se informa el tamaño.",
    )
    if _falta_historial():
        return
    servicios = _servicios(str(_raiz()))
    st.caption("Construir guarda una partición nueva en workspace/particiones/ (fuera de git).")
    if st.button("Construir poblaciones y partición", type="primary"):
        resultado = _ejecutar(
            lambda: servicios.escenarios.construir_poblaciones(
                SolicitudConstruirPoblaciones(
                    archivo=_raiz() / HISTORIAL,
                    diccionario=_raiz() / DICCIONARIO,
                    definicion=_raiz() / OBJETIVO,
                    configuracion=_raiz() / POBLACIONES,
                    clave_efimera=True,
                )
            )
        )
        if resultado is not None:
            st.session_state["poblaciones"] = resultado
    resultado = st.session_state.get("poblaciones")
    if resultado is None:
        return

    st.subheader("Partición cronológica")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Desarrollo", resultado.unidades_desarrollo)
    col2.metric("Prueba (SELLADA)", resultado.tamano_prueba)
    col3.metric("Piloto", resultado.unidades_piloto)
    col4.metric("Excluidas", resultado.unidades_excluidas)
    st.dataframe(p.tabla_seguimiento(resultado), hide_index=True, width="stretch")

    st.subheader("D1, D2 y D3 por ventana, solo en desarrollo")
    st.write(
        f"Diseño principal del ejemplo: **{resultado.diseno_principal}**; "
        f"complementarios: {', '.join(resultado.complementarios)}. "
        "D1: quienes todavía pueden desertar en la ventana. D2: los mismos estudiantes "
        "en todas las ventanas. D3: toda la cohorte."
    )
    izquierda, derecha = st.columns([3, 2])
    izquierda.dataframe(
        p.tabla_poblaciones(resultado),
        hide_index=True,
        width="stretch",
        column_config={"Prevalencia": st.column_config.NumberColumn(format="%.3f")},
    )
    derecha.bar_chart(
        p.serie_tamanos(resultado),
        stack=False,
        y_label="Estudiantes",
        color=_colores(),
    )
    st.dataframe(
        p.tabla_no_etiquetables(resultado),
        hide_index=True,
        width="stretch",
        column_config={"Proporción": st.column_config.NumberColumn(format="%.3f")},
    )

    st.subheader("Probar el sello")
    st.write(
        "Este botón intenta leer la prueba desde el visor. Debe ser rechazado y quedar "
        "en el registro de accesos."
    )
    if st.button("Intentar leer la prueba"):
        try:
            servicios.escenarios.leer_prueba(
                SolicitudLeerPrueba(
                    particion=Path(resultado.carpeta_particion),
                    motivo="demostración del sello desde el visor",
                    origen="visor",
                )
            )
        except AccesoPruebaDenegado as error:
            st.error(f"{error.causa}\n\n**Acción sugerida:** {error.accion}")
        except ErrorSuficiencia as error:
            st.error(f"{error.causa}\n\n**Acción sugerida:** {error.accion}")
        else:
            st.error("La lectura no fue rechazada. Esto no debería ocurrir: revise el sello.")


def pagina_registro() -> None:
    _encabezado(
        "Registro de trazabilidad",
        "Experimentos, decisiones y accesos quedan en un registro encadenado por huellas: "
        "si alguien edita un registro anterior, la verificación lo detecta.",
    )
    servicios = _servicios(str(_raiz()))
    integridad = _ejecutar(servicios.reportes.verificar)
    if integridad is None:
        return
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Integridad", "correcta" if integridad.correcto else "CON PROBLEMAS")
    col2.metric("Experimentos", integridad.registros_por_tipo.get("experimentos", 0))
    col3.metric("Decisiones", integridad.registros_por_tipo.get("decisiones", 0))
    col4.metric("Accesos", integridad.registros_por_tipo.get("accesos", 0))
    for problema in integridad.problemas:
        st.error(problema)
    st.subheader("Intentos de acceso a la prueba")
    accesos = _ejecutar(
        lambda: servicios.reportes.consultar(SolicitudConsultarRegistro(tipo="accesos"))
    )
    if accesos is not None:
        st.dataframe(p.tabla_accesos(accesos.registros), hide_index=True, width="stretch")
        st.caption(f"Archivo: {accesos.archivo}")


def main() -> None:
    st.set_page_config(page_title="Suficiencia · visor de demostración", layout="wide")
    paginas = [
        st.Page(pagina_inicio, title="Inicio", url_path="inicio", default=True),
        st.Page(pagina_datos, title="Datos y auditoría", url_path="datos"),
        st.Page(pagina_escenarios, title="Escenarios", url_path="escenarios"),
        st.Page(pagina_objetivo, title="Objetivo de deserción", url_path="objetivo"),
        st.Page(pagina_poblaciones, title="Poblaciones y partición", url_path="poblaciones"),
        st.Page(pagina_registro, title="Registro", url_path="registro"),
    ]
    st.navigation(paginas).run()


if __name__ == "__main__":
    main()
