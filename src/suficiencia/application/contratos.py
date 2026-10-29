"""Contratos de entrada y salida de los servicios de aplicación (RNF-14).

Son objetos inmutables que rechazan campos desconocidos. La línea de comandos, la
futura interfaz y una API futura usan estos mismos contratos.

Los contratos de cada caso de uso se definen en el hito que lo implementa: muchos
dependen de decisiones abiertas (por ejemplo, CU-03 de DP-01) y fijarlos ahora
obligaría a suponer valores (decisión D-21 de H2.1).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

PATRON_CASO_DE_USO = r"^CU-\d{2}$"


class Contrato(BaseModel):
    """Base de todos los contratos: inmutable y sin campos adicionales."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class CasoDeUso(Contrato):
    """Un caso de uso de la especificación (sección 3) y su disponibilidad."""

    codigo: str = Field(pattern=PATRON_CASO_DE_USO)
    nombre: str = Field(min_length=1)
    servicio: str = Field(min_length=1)
    hito: str = Field(min_length=1, description="Hito o fase en que se construye.")
    disponible: bool
    avance: str | None = Field(
        default=None, description="Parte ya disponible, si el caso de uso está a medias."
    )


class EstadoServicio(Contrato):
    """Qué casos de uso atiende un servicio y cuáles están disponibles."""

    servicio: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    casos_de_uso: tuple[CasoDeUso, ...]


class EstadoProyecto(Contrato):
    """Estado del motor: versión del paquete y servicios."""

    version_paquete: str
    servicios: tuple[EstadoServicio, ...]


class SolicitudCasoDeUso(Contrato):
    """Pide ejecutar un caso de uso por su código."""

    codigo: str = Field(pattern=PATRON_CASO_DE_USO)


class SolicitudValidarConfiguracion(Contrato):
    """Pide validar un archivo de configuración del proyecto.

    Sin ``archivo``, se valida ``config/proyecto.yaml`` de la raíz del proyecto.
    """

    archivo: Path | None = None


class ResultadoValidacionConfiguracion(Contrato):
    """Resultado de validar la configuración del proyecto."""

    valida: bool
    archivo: str
    nombre_proyecto: str | None = None
    version_especificacion: str | None = None
    semilla_global_definida: bool | None = None
    tolerancia_metricas_definida: bool | None = None
    error: str | None = None


class SolicitudGenerarEscenarios(Contrato):
    """Pide construir los 32 escenarios (CU-04, parte de escenarios; H2.2).

    Sin ``configuracion`` se usa ``config/escenarios.yaml``; sin ``variables``, el
    archivo de variables del proyecto (``config/diccionario/variables.yaml``),
    que no existe mientras DP-03 siga abierta.
    """

    configuracion: Path | None = None
    variables: Path | None = None
    diccionario: Path | None = Field(
        default=None, description="Toma los rasgos de un diccionario de datos (H2.3)."
    )


class VentanaResumen(Contrato):
    codigo: str
    fecha_indice: str


class EscenarioResumen(Contrato):
    codigo: str
    ventana: str
    conjunto: str
    factible: bool
    variables: tuple[str, ...]
    bloques_sin_variables: tuple[str, ...]


class ResultadoEscenarios(Contrato):
    """Matriz de escenarios ya verificada contra la fuga temporal (RF-M2-04)."""

    ficticio: bool = Field(description="True si la configuración o las variables son un ejemplo.")
    ventanas: tuple[VentanaResumen, ...]
    escenarios: tuple[EscenarioResumen, ...]
    variables_evaluadas: int
    sin_fuga: bool


# H2.3: datos -------------------------------------------------------------------


class SolicitudValidarDiccionario(Contrato):
    """Pide validar un diccionario de datos (CU-02, parte de validación; H2.3)."""

    archivo: Path


class RasgoResumen(Contrato):
    nombre: str
    bloque: str
    ventana_minima: str


class ResultadoDiccionario(Contrato):
    nombre: str
    ficticio: bool
    variables_por_rol: dict[str, int]
    rasgos: tuple[RasgoResumen, ...]
    clave: tuple[str, ...]


class SolicitudImportarDataset(Contrato):
    """Pide importar, seudonimizar y auditar un archivo (CU-01 con datos sintéticos; H2.3).

    ``clave_efimera`` usa una clave de seudonimización aleatoria que no se guarda:
    sirve para datos sintéticos. Sin ella, la clave se toma de la variable de
    entorno ``SUFICIENCIA_CLAVE_SEUDONIMO`` (el método definitivo depende de DP-14).
    ``salida``, si se indica, debe estar dentro de la carpeta ``data/``.
    """

    archivo: Path
    diccionario: Path
    clave_efimera: bool = False
    salida: Path | None = None
    separador: str = Field(default=",", min_length=1, max_length=1)


class ColumnaAuditada(Contrato):
    nombre: str
    rol: str
    tipo: str
    nulos: int
    tipo_invalido: int
    fuera_de_dominio: int
    cardinalidad: int | None
    minimo: float | None
    maximo: float | None
    filas_con_problemas: tuple[int, ...]


class InformeAuditoriaResumen(Contrato):
    """Informe de auditoría sin la distribución de la clase (RF-M1-03)."""

    n_filas: int
    n_columnas: int
    columnas: tuple[ColumnaAuditada, ...]
    duplicados_clave: int
    filas_duplicadas: int
    errores_criticos: tuple[str, ...]
    alertas: tuple[str, ...]
    apto_para_m2: bool


class ResultadoImportacion(Contrato):
    archivo: str
    sintetico: bool
    huella_fuente: str
    columnas_seudonimizadas: tuple[str, ...]
    informe: InformeAuditoriaResumen
    huella_procesado: str | None = Field(
        default=None, description="Huella del dataset procesado; solo si la auditoría es apta."
    )
    archivo_salida: str | None = None
