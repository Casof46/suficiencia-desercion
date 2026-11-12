"""Contratos de entrada y salida de los servicios de aplicación (RNF-14).

Son objetos inmutables que rechazan campos desconocidos. La línea de comandos, la
futura interfaz y una API futura usan estos mismos contratos.

Los contratos de cada caso de uso se definen en el hito que lo implementa: muchos
dependen de decisiones abiertas (por ejemplo, CU-03 de DP-01) y fijarlos ahora
obligaría a suponer valores (decisión D-21 de H2.1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

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


# H2.7: trazabilidad --------------------------------------------------------------

PATRON_TIPO_REGISTRO = r"^(experimentos|decisiones|accesos|protocolos|desviaciones|congelamientos)$"


class EntornoResumen(Contrato):
    python: str
    sistema: str
    huella_bloqueo: str | None
    commit: str | None
    cambios_sin_commit: bool | None
    nucleos: int | None
    hilos: dict[str, str]
    paquetes: dict[str, str]


class SolicitudRegistrarDecision(Contrato):
    """Registra una decisión metodológica DP-xx (RF-M6-05)."""

    codigo: str = Field(pattern=r"^DP-\d{2}[a-m]?$")
    decision: str = Field(min_length=1)
    justificacion: str = Field(min_length=1)
    responsable: str = Field(min_length=1)
    observaciones: str | None = None


class RegistroResumen(Contrato):
    tipo: str
    numero: int
    fecha: str
    huella: str
    contenido: dict[str, Any]


class SolicitudConsultarRegistro(Contrato):
    tipo: str = Field(pattern=PATRON_TIPO_REGISTRO)


class ResultadoConsultaRegistro(Contrato):
    archivo: str
    tipo: str
    registros: tuple[RegistroResumen, ...]


class ResultadoIntegridad(Contrato):
    archivo: str
    correcto: bool
    registros_por_tipo: dict[str, int]
    problemas: tuple[str, ...]


class SolicitudExportarRegistro(Contrato):
    """Exporta un tipo de registro a CSV o Excel dentro de la carpeta de reportes."""

    tipo: str = Field(pattern=PATRON_TIPO_REGISTRO)
    salida: Path


class ResultadoExportacion(Contrato):
    archivo: str
    filas: int
    huella: str


class ResultadoDemostracion(Contrato):
    archivo: str
    registros: tuple[RegistroResumen, ...]


# H2.4: objetivo y estados de etiqueta -------------------------------------------


class SolicitudValidarObjetivo(Contrato):
    """Pide validar una definición del objetivo (RF-M1-06).

    Sin ``archivo`` se usa la del proyecto (``config/objetivo/definicion.yaml``), que
    no existe mientras DP-01 siga abierta.
    """

    archivo: Path | None = None


class ParametroObjetivo(Contrato):
    decision: str
    parametro: str
    valor: str


class ResultadoDefinicionObjetivo(Contrato):
    archivo: str
    nombre: str
    ficticio: bool
    parametros: tuple[ParametroObjetivo, ...]
    catalogo: dict[str, str]


class SolicitudConstruirObjetivo(Contrato):
    """Pide construir el objetivo y los estados de etiqueta (CU-03 con datos sintéticos).

    Importa, seudonimiza y audita el archivo como ``SolicitudImportarDataset`` y,
    si la auditoría es apta, etiqueta cada unidad con ``definicion``.
    """

    archivo: Path
    diccionario: Path
    definicion: Path | None = None
    clave_efimera: bool = False
    salida: Path | None = None
    separador: str = Field(default=",", min_length=1, max_length=1)


class ResultadoObjetivo(Contrato):
    """Resultado sin la distribución de los estados de etiqueta (RF-M1-03, RF-M2-09)."""

    archivo: str
    sintetico: bool
    definicion: str
    definicion_ficticia: bool
    huella_fuente: str
    huella_dataset: str
    unidades: int
    fuera_de_poblacion: int
    fuera_de_cohortes: int
    huella_registros: str
    archivo_salida: str | None = None


class CasoDemostracionObjetivo(Contrato):
    nombre: str
    historial: tuple[str, ...]
    periodos_observables: int
    estado: str
    motivo: str | None
    periodo_evento: int | None


class ResultadoDemostracionObjetivo(Contrato):
    definicion: str
    horizonte_periodos: int
    casos: tuple[CasoDemostracionObjetivo, ...]


# H2.5: poblaciones, partición y sello ---------------------------------------------


class SolicitudConstruirPoblaciones(Contrato):
    """Pide construir poblaciones, partición y sello (CU-04 y CU-11 con datos sintéticos).

    Sin ``configuracion`` se usa ``config/poblaciones.yaml``, que no existe mientras
    DP-01d, DP-04, DP-05 y DP-17 sigan abiertas. Sin ``definicion``, la del objetivo
    del proyecto (DP-01).
    """

    archivo: Path
    diccionario: Path
    definicion: Path | None = None
    configuracion: Path | None = None
    clave_efimera: bool = False
    separador: str = Field(default=",", min_length=1, max_length=1)


class SeguimientoCohorteResumen(Contrato):
    cohorte: str
    particion: str
    unidades: int
    ultimo_periodo_observable: int
    periodo_necesario: int
    completo: bool


class DescripcionPoblacionResumen(Contrato):
    diseno: str
    ventana: str
    tamano: int
    eventos: int
    prevalencia: float | None
    eventos_detectables: int | None


class NoEtiquetablesCohorteResumen(Contrato):
    cohorte: str
    unidades: int
    no_etiquetables: int
    por_motivo: dict[str, int]
    proporcion: float
    requiere_analisis_sensibilidad: bool


class ResultadoPoblaciones(Contrato):
    """Solo la partición de desarrollo se describe; de la prueba, solo el tamaño (PI-02)."""

    archivo: str
    sintetico: bool
    definicion_ficticia: bool
    configuracion_ficticia: bool
    huella_dataset: str
    diseno_principal: str
    complementarios: tuple[str, ...]
    periodos_indice: dict[str, int]
    seguimiento: tuple[SeguimientoCohorteResumen, ...]
    unidades_desarrollo: int
    tamano_prueba: int
    unidades_piloto: int
    unidades_excluidas: int
    descripciones_desarrollo: tuple[DescripcionPoblacionResumen, ...]
    exclusiones_desarrollo: dict[str, dict[str, int]]
    no_etiquetables_desarrollo: tuple[NoEtiquetablesCohorteResumen, ...]
    nivel_sensibilidad: float
    carpeta_particion: str
    huellas: dict[str, str]


class SolicitudLeerPrueba(Contrato):
    """Intenta leer la prueba de una partición guardada (se rechaza y se registra).

    ``origen`` solo cambia el nombre de la operación que queda en el registro de
    accesos, para distinguir los intentos del visor (H2.D) de los de la línea de
    comandos.
    """

    particion: Path
    motivo: str = Field(min_length=1)
    origen: Literal["linea_de_comandos", "visor"] = "linea_de_comandos"


# --- H2.6: protocolo, desviaciones y congelamiento ------------------------------


class SolicitudGuardarBorrador(Contrato):
    """Guarda un borrador del protocolo leído de un archivo YAML.

    Sin ``version``, crea una versión nueva (o reemplaza la última si sigue en
    borrador). Con ``version``, edita esa versión solo si sigue en borrador.
    """

    archivo: Path
    version: int | None = Field(default=None, ge=1)


class ResultadoBorradorProtocolo(Contrato):
    version: int
    huella: str
    ficticio: bool
    decisiones_faltantes: tuple[str, ...]
    archivo_registro: str


class SolicitudAprobarProtocolo(Contrato):
    """Aprueba una versión en borrador. ``huella`` es la que revisó quien aprueba.

    La desviación (descripción y justificación) es obligatoria si ya hay
    experimentos confirmatorios (RF-M4-13).
    """

    version: int = Field(ge=1)
    huella: str = Field(pattern=r"^[0-9a-f]{64}$")
    responsable: str = Field(min_length=1)
    desviacion: str | None = Field(default=None, min_length=1)
    justificacion: str | None = Field(default=None, min_length=1)


class ResultadoAprobacionProtocolo(Contrato):
    version: int
    huella: str
    version_reemplazada: int | None
    desviacion_registrada: bool
    resultados_afectados: tuple[str, ...]


class VersionProtocoloResumen(Contrato):
    numero: int
    estado: str
    huella: str
    ficticio: bool
    responsable_aprobacion: str | None
    decisiones_faltantes: tuple[str, ...]
    multiplicidad: str
    condiciones: int


class DesviacionResumen(Contrato):
    version_anterior: int
    version_nueva: int
    descripcion: str
    justificacion: str
    responsable: str
    resultados_afectados: tuple[str, ...]


class ResultadoConsultaProtocolo(Contrato):
    archivo_registro: str
    versiones: tuple[VersionProtocoloResumen, ...]
    vigente: int | None
    desviaciones: tuple[DesviacionResumen, ...]


class SolicitudCongelar(Contrato):
    """Congela una configuración descrita en un archivo YAML (CU-07; RF-M4-12)."""

    archivo: Path


class ResultadoCongelamiento(Contrato):
    identificador: str
    rol: str
    escenario: str
    huella: str
    version_protocolo: int
    ficticio: bool


class SolicitudVerificarEvaluacionFinal(Contrato):
    """Comprueba, sin abrir la prueba, las configuraciones que se evaluarían.

    Corresponde a los pasos 2 y 3 de CU-08.
    """

    archivos: tuple[Path, ...] = Field(min_length=1)


class ResultadoVerificacionEvaluacionFinal(Contrato):
    version_protocolo: int
    huella_protocolo: str
    configuraciones: dict[str, str]
    ficticio: bool


class CondicionDemostracion(Contrato):
    descripcion: str
    cumple: bool | None


class EscenarioDemostracion(Contrato):
    escenario: str
    estado: str
    condiciones: tuple[CondicionDemostracion, ...]


class CasoReglaDemostracion(Contrato):
    titulo: str
    estado: str
    escenario: str | None
    empatados: tuple[str, ...]
    escenarios: tuple[EscenarioDemostracion, ...]


class PasoDemostracion(Contrato):
    titulo: str
    resultado: str


class ResultadoDemostracionProtocolo(Contrato):
    """Recorrido completo con el protocolo ficticio en un registro temporal (EJEMPLO FICTICIO)."""

    archivo_protocolo: str
    huella_protocolo: str
    casos: tuple[CasoReglaDemostracion, ...]
    pasos: tuple[PasoDemostracion, ...]


# --- H2.8: estado de las decisiones ---------------------------------------------


class DecisionRegistradaResumen(Contrato):
    codigo: str
    fecha: str
    decision: str
    responsable: str
    observaciones: str | None


class EstadoDecisionResumen(Contrato):
    codigo: str
    nombre: str
    decide: str
    resolver_antes_de: str
    registrada: bool
    registros: tuple[DecisionRegistradaResumen, ...]
    ficha: str | None = Field(description="Ficha en docs/decisiones/, si existe.")


class ResultadoEstadoDecisiones(Contrato):
    archivo_registro: str
    decisiones: tuple[EstadoDecisionResumen, ...]
    registradas: int
    abiertas: int


# --- F3.1: preparación del desarrollo -------------------------------------------


class SolicitudPrepararDesarrollo(Contrato):
    """Prepara matrices, folds y preprocesamiento del desarrollo (CU-06, F3.1).

    Sin ``experimentos`` se usa ``config/experimentos.yaml`` (DP-07); sin
    ``poblaciones``, ``config/poblaciones.yaml`` (DP-04, DP-05); sin ``escenarios``,
    ``config/escenarios.yaml`` (DP-01d); sin ``definicion``, la del objetivo (DP-01).
    """

    archivo: Path
    diccionario: Path
    definicion: Path | None = None
    poblaciones: Path | None = None
    escenarios: Path | None = None
    experimentos: Path | None = None
    clave_efimera: bool = False
    separador: str = Field(default=",", min_length=1, max_length=1)


class FoldResumen(Contrato):
    numero: int
    ajuste: tuple[str, ...]
    calibracion: tuple[str, ...]
    validacion: str


class ConteoFoldResumen(Contrato):
    numero: int
    ajuste: int
    eventos_ajuste: int
    calibracion: int
    eventos_calibracion: int
    validacion: int
    eventos_validacion: int


class VentanaPreparadaResumen(Contrato):
    ventana: str
    periodo_indice: int
    filas: int
    eventos: int
    folds: tuple[ConteoFoldResumen, ...]


class EscenarioPreparadoResumen(Contrato):
    escenario: str
    ventana: str
    conjunto: str
    variables: tuple[str, ...]
    filas: int
    columnas_preprocesadas: dict[str, tuple[int, int]] = Field(
        description="Por perfil: mínimo y máximo de columnas tras el preprocesamiento en los folds."
    )


class ResultadoPreparacionDesarrollo(Contrato):
    archivo: str
    sintetico: bool
    configuraciones_ficticias: bool
    huella_dataset: str
    diseno: str
    cohortes_desarrollo: tuple[str, ...]
    folds: tuple[FoldResumen, ...]
    ventanas: tuple[VentanaPreparadaResumen, ...]
    escenarios: tuple[EscenarioPreparadoResumen, ...]
    no_factibles: tuple[str, ...]
    perfiles: tuple[str, ...]


class SolicitudEntrenar(SolicitudPrepararDesarrollo):
    """Entrena las familias en los folds de desarrollo (CU-06, F3.2), en modo exploratorio.

    Sin ``seleccion_escenarios`` se entrenan todos los escenarios factibles; sin
    ``seleccion_familias``, las cinco familias.
    """

    seleccion_escenarios: tuple[str, ...] = ()
    seleccion_familias: tuple[str, ...] = ()


class CorridaResumen(Contrato):
    escenario: str
    familia: str
    estado: Literal["exitosa", "fallida", "omitida"]
    identificador: str | None
    configuraciones_evaluadas: int
    carpeta: str | None
    error: str | None


class ResultadoEntrenamiento(Contrato):
    archivo: str
    sintetico: bool
    configuraciones_ficticias: bool
    huella_dataset: str
    modo: str
    semilla: int
    corridas: tuple[CorridaResumen, ...]


class SolicitudMetricas(Contrato):
    """Métricas e intervalos de las corridas registradas (CU-06, F3.3), en modo exploratorio.

    Usa las corridas exitosas de la configuración de experimentos indicada (sin
    ``experimentos``, ``config/experimentos.yaml``).
    """

    experimentos: Path | None = None
    seleccion_escenarios: tuple[str, ...] = ()
    seleccion_familias: tuple[str, ...] = ()


class EstimacionResumen(Contrato):
    puntual: float | None
    limite_inferior: float | None
    limite_superior: float | None
    replicas_validas: int


class MetricasCorridaResumen(Contrato):
    identificador: str
    escenario: str
    familia: str
    filas: int
    eventos: int
    prevalencia: float
    metricas: dict[str, EstimacionResumen]


class ResultadoMetricas(Contrato):
    configuracion_experimentos: str
    configuraciones_ficticias: bool
    metodo: str
    nivel: float
    replicas: int
    estratificacion: str
    q: float | None
    corridas: tuple[MetricasCorridaResumen, ...]
    identificador_registro: str


# --- F3.4: selección, congelamiento y evaluación final -----------------------------


class SolicitudSeleccionar(SolicitudPrepararDesarrollo):
    """Elige modelo y umbral por escenario solo con desarrollo (CU-07, F3.4).

    Usa las corridas exitosas de las cinco familias, entrenadas con la misma
    configuración y el mismo archivo. Sin ``seleccion_escenarios``, todos los que
    tengan las cinco corridas.
    """

    seleccion_escenarios: tuple[str, ...] = ()


class SeleccionEscenarioResumen(Contrato):
    escenario: str
    familia: str
    metrica: str
    valores: dict[str, float]
    umbral: float
    reentrenamiento: str
    carpeta: str
    configuracion_candidata: dict[str, Any] = Field(
        description="Todo lo que se congela, salvo identificador, rol y versión del protocolo."
    )


class ReferenteResumen(Contrato):
    """R0 o un control (R0-fam, R-ven), construido con su propia regla (DP-19; F3.5)."""

    codigo: str
    tipo: str
    rol: str
    seleccion: SeleccionEscenarioResumen


class ResultadoSeleccion(Contrato):
    configuracion_experimentos: str
    configuraciones_ficticias: bool
    escenarios: tuple[SeleccionEscenarioResumen, ...]
    referentes: tuple[ReferenteResumen, ...]
    identificador_registro: str


class SolicitudEvaluacionFinal(SolicitudPrepararDesarrollo):
    """Evalúa una sola vez en la prueba las configuraciones congeladas (CU-08, F3.4).

    Exige un protocolo aprobado vigente. Repetirla sobre la misma partición exige
    ``justificacion_repeticion`` (RF-M4-09).
    """

    particion: Path
    configuraciones: tuple[str, ...] = Field(min_length=1)
    version_protocolo: int
    justificacion_repeticion: str | None = None


class MetricasPruebaResumen(Contrato):
    identificador: str
    rol: str
    escenario: str
    algoritmo: str
    filas: int
    eventos: int
    prevalencia: float
    umbral: float
    metricas: dict[str, EstimacionResumen]
    con_umbral: dict[str, float | None]


class ResultadoEvaluacionFinal(Contrato):
    version_protocolo: int
    ficticio: bool
    configuraciones: tuple[MetricasPruebaResumen, ...]
    estado_regla: str
    escenario_suficiente: str | None
    detalle_regla: tuple[str, ...]
    identificador_registro: str
    accesos_a_la_prueba: int


class SolicitudDemostracionFinal(Contrato):
    """Recorre selección, congelamiento y evaluación final en un proyecto temporal (F3.4).

    Solo con datos sintéticos y configuraciones ficticias; nada llega al registro
    del proyecto.
    """

    archivo: Path
    diccionario: Path
    definicion: Path
    poblaciones: Path
    escenarios: Path
    experimentos: Path
    protocolo: Path
    seleccion_escenarios: tuple[str, ...] = Field(min_length=1)
    separador: str = Field(default=",", min_length=1, max_length=1)


# --- F3.5: evaluación comparativa frente a R0 (CU-12) --------------------------------


class SolicitudComparar(Contrato):
    """Compara la configuración seleccionada con R0 y los controles (CU-12, F3.5).

    Usa las predicciones de una evaluación final registrada; no vuelve a abrir la prueba.
    Sin ``experimentos`` ni ``poblaciones``, los archivos del proyecto (DP-19, DP-20).
    """

    evaluacion: str = Field(min_length=1)
    experimentos: Path | None = None
    poblaciones: Path | None = None


class NoInferioridadResumen(Contrato):
    metrica: str
    diferencia: float
    limite_unilateral: float
    limite_inferior: float
    limite_superior: float
    margen: float
    estado: str


class ControlResumen(Contrato):
    codigo: str
    escenario: str
    algoritmo: str
    filas: int
    diferencias: dict[str, EstimacionResumen]


class ResultadoComparacion(Contrato):
    evaluacion: str
    version_protocolo: int
    ficticio: bool
    estado: str
    motivos_no_validez: tuple[str, ...]
    seleccionada: str | None
    escenario_seleccionado: str | None
    referencia: str | None
    escenario_referencia: str | None
    poblacion_comparada: int
    eventos_comparados: int
    no_inferioridad: tuple[NoInferioridadResumen, ...]
    anticipacion_ventanas: int | None
    anticipacion_ciclos: int | None
    bloques_evitados: tuple[str, ...]
    variables_evitadas: tuple[str, ...]
    controles: tuple[ControlResumen, ...]
    identificador_registro: str
    accesos_a_la_prueba: int


class ResultadoDemostracionFinal(Contrato):
    """Selección, congelamiento y evaluación final en un proyecto temporal (EJEMPLO FICTICIO)."""

    archivo_protocolo: str
    seleccion: ResultadoSeleccion
    evaluacion: ResultadoEvaluacionFinal
    comparacion: ResultadoComparacion
    pasos: tuple[PasoDemostracion, ...]
