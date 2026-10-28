"""Base común de los servicios de casos de uso."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, NoReturn

from suficiencia.application.contratos import CasoDeUso, EstadoServicio, SolicitudCasoDeUso
from suficiencia.domain.errores import CasoDeUsoNoDisponible, ErrorSuficiencia


@dataclass(frozen=True)
class DefinicionCasoDeUso:
    """Código, nombre (sección 3 de la especificación) e hito en que se construye."""

    codigo: str
    nombre: str
    hito: str
    avance: str | None = None


class ServicioCasosDeUso:
    """Servicio que atiende un grupo de casos de uso (sección 6 de la especificación).

    Mientras un caso de uso no esté completo, ejecutarlo devuelve un error
    controlado que indica en qué hito se construye. Las partes ya construidas se
    ofrecen como métodos propios del servicio, con su contrato (por ejemplo,
    ``ServicioEscenarios.generar_escenarios`` desde H2.2).
    """

    NOMBRE: ClassVar[str]
    DESCRIPCION: ClassVar[str]
    CASOS_DE_USO: ClassVar[tuple[DefinicionCasoDeUso, ...]]

    def estado(self) -> EstadoServicio:
        return EstadoServicio(
            servicio=self.NOMBRE,
            descripcion=self.DESCRIPCION,
            casos_de_uso=tuple(
                CasoDeUso(
                    codigo=caso.codigo,
                    nombre=caso.nombre,
                    servicio=self.NOMBRE,
                    hito=caso.hito,
                    disponible=False,
                    avance=caso.avance,
                )
                for caso in self.CASOS_DE_USO
            ),
        )

    def ejecutar(self, solicitud: SolicitudCasoDeUso) -> NoReturn:
        for caso in self.CASOS_DE_USO:
            if caso.codigo == solicitud.codigo:
                hito = f"{caso.hito}. Ya disponible: {caso.avance}" if caso.avance else caso.hito
                raise CasoDeUsoNoDisponible(caso.codigo, hito)
        raise ErrorSuficiencia(
            f"El servicio {self.NOMBRE} no atiende el caso de uso {solicitud.codigo}.",
            "Consulte `suficiencia estado` para ver qué servicio atiende cada caso de uso.",
        )
