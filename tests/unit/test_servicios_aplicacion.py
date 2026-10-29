"""Contratos y servicios de aplicación (H2.1).

Comprueba que los servicios cubren los doce casos de uso de la especificación con
el reparto de la sección 6, que ninguno tiene lógica todavía y que las
dependencias se reciben desde fuera (puerto ``FuenteConfiguracion``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from fixtures.generador_sintetico import generar_historial, sembrar_problemas
from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    CasoDeUso,
    SolicitudCasoDeUso,
    SolicitudGenerarEscenarios,
    SolicitudImportarDataset,
    SolicitudValidarConfiguracion,
    SolicitudValidarDiccionario,
)
from suficiencia.application.errores import (
    CasoDeUsoNoDisponible,
    ConfiguracionInvalida,
    ErrorSuficiencia,
)
from suficiencia.application.servicio_datos import ServicioDatos
from suficiencia.application.servicio_escenarios import ServicioEscenarios
from suficiencia.application.servicio_proyecto import ServicioProyecto
from suficiencia.domain.errores import ConfiguracionInvalida as ErrorDeConfiguracion
from suficiencia.domain.errores import DecisionPendiente
from suficiencia.domain.escenarios.modelo import (
    Bloque,
    CatalogoDeclarado,
    CatalogoVentanas,
    Variable,
    VariablesDeclaradas,
)
from suficiencia.domain.huella import Huella
from suficiencia.domain.proyecto import ConfiguracionProyecto
from suficiencia.domain.puertos import FuenteConfiguracion, FuenteVariables, Seudonimizador
from suficiencia.persistence.diccionario_yaml import cargar_diccionario
from suficiencia.persistence.lectores import leer_tabla
from suficiencia.persistence.objetivo_yaml import cargar_definicion_objetivo

# Sección 6 de la especificación: qué servicio atiende cada caso de uso.
REPARTO_ESPERADO = {
    "datos": {"CU-01", "CU-02", "CU-03"},
    "escenarios": {"CU-04", "CU-11"},
    "protocolo": {"CU-05"},
    "experimentos": {"CU-06", "CU-07"},
    "evaluacion_final": {"CU-08", "CU-12"},
    "interpretabilidad": {"CU-09"},
    "reportes": {"CU-10"},
}
TODOS_LOS_CASOS = sorted(set().union(*REPARTO_ESPERADO.values()))


def test_los_doce_casos_de_uso_estan_repartidos_como_en_la_especificacion(raiz: Path) -> None:
    estado = crear_servicios(raiz).proyecto.estado()
    reparto = {s.servicio: {c.codigo for c in s.casos_de_uso} for s in estado.servicios}
    assert reparto == REPARTO_ESPERADO
    assert [f"CU-{n:02d}" for n in range(1, 13)] == TODOS_LOS_CASOS


def test_ningun_caso_de_uso_figura_como_disponible_en_h2_1(raiz: Path) -> None:
    estado = crear_servicios(raiz).proyecto.estado()
    casos = [c for s in estado.servicios for c in s.casos_de_uso]
    assert casos
    assert not any(c.disponible for c in casos)
    assert all(c.hito for c in casos)


@pytest.mark.parametrize("codigo", TODOS_LOS_CASOS)
def test_ejecutar_un_caso_de_uso_devuelve_un_error_controlado(raiz: Path, codigo: str) -> None:
    servicios = crear_servicios(raiz)
    with pytest.raises(CasoDeUsoNoDisponible) as error:
        servicios.servicio_de(codigo).ejecutar(SolicitudCasoDeUso(codigo=codigo))
    assert error.value.caso == codigo


def test_un_servicio_rechaza_un_caso_de_uso_que_no_atiende(raiz: Path) -> None:
    with pytest.raises(ErrorSuficiencia, match="no atiende"):
        crear_servicios(raiz).datos.ejecutar(SolicitudCasoDeUso(codigo="CU-05"))


def test_un_caso_de_uso_inexistente_se_rechaza(raiz: Path) -> None:
    with pytest.raises(ErrorSuficiencia, match="No existe el caso de uso CU-13"):
        crear_servicios(raiz).servicio_de("CU-13")


def test_los_contratos_rechazan_campos_desconocidos_y_son_inmutables() -> None:
    with pytest.raises(ValidationError):
        SolicitudCasoDeUso(codigo="CU-01", extra="x")  # type: ignore[call-arg]
    solicitud = SolicitudCasoDeUso(codigo="CU-01")
    with pytest.raises(ValidationError):
        solicitud.codigo = "CU-02"  # type: ignore[misc]


@pytest.mark.parametrize("codigo", ["CU-1", "cu-01", "CU-001", "UC-01", ""])
def test_los_contratos_validan_el_codigo_de_caso_de_uso(codigo: str) -> None:
    with pytest.raises(ValidationError):
        SolicitudCasoDeUso(codigo=codigo)
    with pytest.raises(ValidationError):
        CasoDeUso(codigo=codigo, nombre="x", servicio="x", hito="x", disponible=False)


class _FuenteFija:
    """Implementación de prueba del puerto: no lee archivos."""

    def __init__(self, configuracion: ConfiguracionProyecto | None) -> None:
        self.configuracion = configuracion

    def cargar(self) -> ConfiguracionProyecto:
        if self.configuracion is None:
            raise ConfiguracionInvalida("Configuración de prueba inválida.", "Corríjala.")
        return self.configuracion


def _servicio_con(fuente: _FuenteFija, archivos: list[Path]) -> ServicioProyecto:
    def fabrica(archivo: Path) -> FuenteConfiguracion:
        archivos.append(archivo)
        return fuente

    return ServicioProyecto(
        raiz=Path("raiz-ficticia"), version_paquete="0", servicios=(), fuente_configuracion=fabrica
    )


def test_validar_configuracion_usa_el_puerto_y_no_supone_valores_pendientes() -> None:
    configuracion = ConfiguracionProyecto(
        raiz=Path("raiz-ficticia"),
        nombre="Proyecto de prueba",
        version_especificacion="0.5",
        rutas={},
        semilla_global=None,
        tolerancia_metricas=None,
    )
    archivos: list[Path] = []
    resultado = _servicio_con(_FuenteFija(configuracion), archivos).validar_configuracion(
        SolicitudValidarConfiguracion()
    )
    assert archivos == [Path("raiz-ficticia") / "config" / "proyecto.yaml"]
    assert resultado.valida
    assert resultado.nombre_proyecto == "Proyecto de prueba"
    assert resultado.semilla_global_definida is False
    assert resultado.tolerancia_metricas_definida is False


def test_validar_configuracion_invalida_devuelve_el_error_sin_lanzarlo() -> None:
    archivos: list[Path] = []
    resultado = _servicio_con(_FuenteFija(None), archivos).validar_configuracion(
        SolicitudValidarConfiguracion(archivo=Path("otro.yaml"))
    )
    assert archivos == [Path("otro.yaml")]
    assert not resultado.valida
    assert resultado.error is not None
    assert "Acción sugerida" in resultado.error


# H2.2: escenarios ------------------------------------------------------------


def test_cu04_muestra_su_avance_y_sigue_incompleto(raiz: Path) -> None:
    servicios = crear_servicios(raiz)
    estado = servicios.proyecto.estado()
    cu04 = next(c for s in estado.servicios for c in s.casos_de_uso if c.codigo == "CU-04")
    assert not cu04.disponible
    assert cu04.avance is not None
    assert "suficiencia escenarios" in cu04.avance
    with pytest.raises(CasoDeUsoNoDisponible, match="Ya disponible"):
        servicios.servicio_de("CU-04").ejecutar(SolicitudCasoDeUso(codigo="CU-04"))


class _CatalogoEnMemoria:
    def __init__(self, ficticio: bool) -> None:
        self.ficticio = ficticio

    def cargar(self) -> CatalogoDeclarado:
        catalogo = CatalogoVentanas.desde_fechas_indice(
            {codigo: f"FICTICIA {codigo}" for codigo in ("T0", "T1", "T2", "T3")}
        )
        return CatalogoDeclarado(catalogo=catalogo, ficticio=self.ficticio)


class _VariablesEnMemoria:
    def __init__(self, ficticio: bool) -> None:
        self.ficticio = ficticio

    def cargar(self) -> VariablesDeclaradas:
        variables = (
            Variable("a0", Bloque.ACADEMICO, "T0"),
            Variable("b1", Bloque.CONDUCTUAL, "T1"),
        )
        return VariablesDeclaradas(variables=variables, ficticio=self.ficticio)


@pytest.mark.parametrize(
    ("catalogo_ficticio", "variables_ficticias"), [(False, False), (True, False), (False, True)]
)
def test_generar_escenarios_usa_los_puertos_y_propaga_el_rotulo_ficticio(
    catalogo_ficticio: bool, variables_ficticias: bool
) -> None:
    rutas: list[tuple[Path, bool]] = []

    def variables(archivo: Path, por_omision: bool) -> FuenteVariables:
        rutas.append((archivo, por_omision))
        return _VariablesEnMemoria(variables_ficticias)

    servicio = ServicioEscenarios(
        raiz=Path("raiz-ficticia"),
        fuente_catalogo=lambda _archivo: _CatalogoEnMemoria(catalogo_ficticio),
        fuente_variables=variables,
        fuente_diccionario=lambda _archivo: _VariablesEnMemoria(variables_ficticias),
    )
    resultado = servicio.generar_escenarios(SolicitudGenerarEscenarios())
    assert rutas == [(Path("raiz-ficticia") / "config" / "diccionario" / "variables.yaml", True)]
    assert resultado.ficticio == (catalogo_ficticio or variables_ficticias)
    assert len(resultado.escenarios) == 32
    assert resultado.sin_fuga
    no_factibles = {e.codigo for e in resultado.escenarios if not e.factible}
    assert "T0|A+B" in no_factibles
    assert "T1|A+B" not in no_factibles


# H2.3: datos -------------------------------------------------------------------

DICCIONARIO_EJEMPLO = Path("config") / "ejemplos" / "diccionario_sintetico.yaml"


def _proyecto_temporal(tmp_path: Path, raiz: Path, tabla: pd.DataFrame) -> tuple[Path, Path]:
    """Copia mínima de un proyecto: diccionario de ejemplo y un archivo de datos."""
    diccionario = tmp_path / "diccionario.yaml"
    diccionario.write_bytes((raiz / DICCIONARIO_EJEMPLO).read_bytes())
    archivo = tmp_path / "data" / "fuente.csv"
    archivo.parent.mkdir()
    tabla.to_csv(archivo, index=False)
    return diccionario, archivo


def test_importar_un_archivo_sintetico_lo_seudonimiza_y_audita(tmp_path: Path, raiz: Path) -> None:
    diccionario, archivo = _proyecto_temporal(tmp_path, raiz, generar_historial(40, semilla=3))
    servicio = crear_servicios(tmp_path).datos
    resultado = servicio.importar_dataset(
        SolicitudImportarDataset(
            archivo=archivo,
            diccionario=diccionario,
            clave_efimera=True,
            salida=Path("data") / "interim" / "procesado.csv",
        )
    )
    assert resultado.sintetico
    assert resultado.informe.apto_para_m2
    assert resultado.columnas_seudonimizadas == ("codigo_estudiante",)
    salida = Path(resultado.archivo_salida or "")
    assert salida.is_file()
    procesado = pd.read_csv(salida, dtype=str)
    assert "codigo_estudiante" not in procesado.columns
    assert "seudonimo" in procesado.columns
    assert resultado.huella_procesado == Huella.de_bytes(salida.read_bytes()).valor


def test_importar_rechaza_un_archivo_no_marcado_como_sintetico_sin_procesarlo(
    tmp_path: Path, raiz: Path
) -> None:
    tabla = generar_historial(10, semilla=3)
    tabla.loc[2, "origen_datos"] = "INSTITUCION"
    diccionario, archivo = _proyecto_temporal(tmp_path, raiz, tabla)
    llamadas: list[bool] = []

    def seudonimizador(efimera: bool) -> Seudonimizador:
        llamadas.append(efimera)
        raise AssertionError("no debe llegar a seudonimizar")

    servicio = ServicioDatos(
        raiz=tmp_path,
        cargar_diccionario=cargar_diccionario,
        leer_tabla=lambda a, s: (leer_tabla(a, s).tabla, leer_tabla(a, s).huella_fuente),
        seudonimizador=seudonimizador,
        huella_de_tabla=lambda t: Huella.de_bytes(b""),
        escribir_tabla=lambda t, a: Huella.de_bytes(b""),
        cargar_definicion=cargar_definicion_objetivo,
    )
    with pytest.raises(DecisionPendiente) as error:
        servicio.importar_dataset(
            SolicitudImportarDataset(archivo=archivo, diccionario=diccionario, clave_efimera=True)
        )
    assert error.value.decision == "DP-02"
    assert llamadas == []


def test_importar_no_guarda_nada_fuera_de_data_ni_si_la_auditoria_falla(
    tmp_path: Path, raiz: Path
) -> None:
    con_problemas, _ = sembrar_problemas(generar_historial(20, semilla=3))
    diccionario, archivo = _proyecto_temporal(tmp_path, raiz, con_problemas)
    servicio = crear_servicios(tmp_path).datos
    with pytest.raises(ErrorDeConfiguracion, match="fuera de la carpeta data/"):
        servicio.importar_dataset(
            SolicitudImportarDataset(
                archivo=archivo,
                diccionario=diccionario,
                clave_efimera=True,
                salida=Path("reports") / "x.csv",
            )
        )
    resultado = servicio.importar_dataset(
        SolicitudImportarDataset(
            archivo=archivo,
            diccionario=diccionario,
            clave_efimera=True,
            salida=Path("data") / "x.csv",
        )
    )
    assert not resultado.informe.apto_para_m2
    assert resultado.huella_procesado is None
    assert resultado.archivo_salida is None
    assert not (tmp_path / "data" / "x.csv").exists()


def test_validar_diccionario_resume_roles_y_rasgos(raiz: Path) -> None:
    resultado = crear_servicios(raiz).datos.validar_diccionario(
        SolicitudValidarDiccionario(archivo=raiz / DICCIONARIO_EJEMPLO)
    )
    assert resultado.ficticio
    assert resultado.variables_por_rol["rasgo"] == 8
    assert resultado.variables_por_rol["identificador"] == 1
    assert len(resultado.rasgos) == 8


def test_cu01_y_cu02_muestran_su_avance(raiz: Path) -> None:
    estado = crear_servicios(raiz).proyecto.estado()
    casos = {c.codigo: c for s in estado.servicios for c in s.casos_de_uso}
    assert "suficiencia datos importar" in (casos["CU-01"].avance or "")
    assert "suficiencia datos diccionario" in (casos["CU-02"].avance or "")
    assert not casos["CU-01"].disponible
