"""Contratos y servicios de aplicación (H2.1).

Comprueba que los servicios cubren los doce casos de uso de la especificación con
el reparto de la sección 6, que ninguno tiene lógica todavía y que las
dependencias se reciben desde fuera (puerto ``FuenteConfiguracion``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from suficiencia.application.composicion import crear_servicios
from suficiencia.application.contratos import (
    CasoDeUso,
    SolicitudCasoDeUso,
    SolicitudGenerarEscenarios,
    SolicitudValidarConfiguracion,
)
from suficiencia.application.errores import (
    CasoDeUsoNoDisponible,
    ConfiguracionInvalida,
    ErrorSuficiencia,
)
from suficiencia.application.servicio_datos import ServicioDatos
from suficiencia.application.servicio_escenarios import ServicioEscenarios
from suficiencia.application.servicio_proyecto import ServicioProyecto
from suficiencia.domain.escenarios.modelo import (
    Bloque,
    CatalogoDeclarado,
    CatalogoVentanas,
    Variable,
    VariablesDeclaradas,
)
from suficiencia.domain.proyecto import ConfiguracionProyecto
from suficiencia.domain.puertos import FuenteConfiguracion, FuenteVariables

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


def test_un_servicio_rechaza_un_caso_de_uso_que_no_atiende() -> None:
    with pytest.raises(ErrorSuficiencia, match="no atiende"):
        ServicioDatos().ejecutar(SolicitudCasoDeUso(codigo="CU-05"))


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
    )
    resultado = servicio.generar_escenarios(SolicitudGenerarEscenarios())
    assert rutas == [(Path("raiz-ficticia") / "config" / "diccionario" / "variables.yaml", True)]
    assert resultado.ficticio == (catalogo_ficticio or variables_ficticias)
    assert len(resultado.escenarios) == 32
    assert resultado.sin_fuga
    no_factibles = {e.codigo for e in resultado.escenarios if not e.factible}
    assert "T0|A+B" in no_factibles
    assert "T1|A+B" not in no_factibles
