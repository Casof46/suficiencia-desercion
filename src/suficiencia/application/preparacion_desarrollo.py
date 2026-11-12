"""Preparación del desarrollo: matrices, folds y preprocesamiento (CU-06, parte inicial; F3.1).

Junta lo construido en las fases anteriores para dejar listo el entrenamiento:

1. Lee el historial sintético (H2.3) y **se queda solo con las cohortes de
   desarrollo** antes de etiquetar: las unidades de prueba ni siquiera se etiquetan
   aquí, así que nada de la prueba puede filtrarse al desarrollo.
2. Construye la población del diseño principal en cada ventana (H2.5).
3. Construye los escenarios y verifica que no haya fuga temporal (H2.2).
4. Arma la matriz de cada escenario factible (F3.1).
5. Construye los folds cronológicos, iguales para todos los escenarios (PI-08).

La usarán el entrenamiento y la selección de los hitos siguientes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from suficiencia.domain.datos.objetivo import ColumnasHistorial, DefinicionObjetivo
from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.escenarios.construccion import construir_escenarios, verificar_sin_fuga
from suficiencia.domain.escenarios.matrices import MatrizEscenario, construir_matriz
from suficiencia.domain.escenarios.modelo import CatalogoDeclarado, Escenario, VariablesDeclaradas
from suficiencia.domain.escenarios.poblaciones import (
    ConfiguracionPoblaciones,
    Diseno,
    construir_poblaciones,
)
from suficiencia.domain.experimentos import ConfiguracionExperimentos, Fold, construir_folds


@dataclass(frozen=True)
class PreparacionDesarrollo:
    diseno: Diseno
    cohortes_desarrollo: tuple[str, ...]
    folds: tuple[Fold, ...]
    matrices: tuple[MatrizEscenario, ...]
    no_factibles: tuple[Escenario, ...]
    periodos_indice: Mapping[str, int]


def filas_de(matriz: MatrizEscenario, cohortes: tuple[str, ...]) -> pd.Series:
    """Máscara de las filas de la matriz que pertenecen a esas cohortes."""
    return matriz.cohorte.astype(str).isin(cohortes)


def preparar(
    tabla: pd.DataFrame,
    columnas: ColumnasHistorial,
    definicion_objetivo: DefinicionObjetivo,
    poblaciones: ConfiguracionPoblaciones,
    catalogo: CatalogoDeclarado,
    variables: VariablesDeclaradas,
    experimentos: ConfiguracionExperimentos,
) -> PreparacionDesarrollo:
    """Prepara el desarrollo; ver el docstring del módulo.

    Raises:
        ConfiguracionInvalida: si el diseño principal no permite entrenar o faltan cohortes.
        FugaTemporal: si algún escenario usa información no disponible en su ventana.
        DecisionPendiente: si falta un dato de una decisión abierta.
    """
    if poblaciones.diseno_principal is Diseno.D3:
        raise ConfiguracionInvalida(
            "El diseño principal es D3, que mide cobertura sobre la cohorte de admisión; "
            "con él no está definida la población de entrenamiento.",
            "Entrenar con D3 exige resolver cómo (DP-04, DP-17). Use D1 o D2 en el ejemplo.",
        )
    desarrollo = tuple(sorted(poblaciones.particion.desarrollo))
    tabla_desarrollo = tabla[tabla[columnas.cohorte].astype(str).isin(desarrollo)]
    if tabla_desarrollo.empty:
        raise ConfiguracionInvalida(
            "El historial no tiene ninguna unidad de las cohortes de desarrollo.",
            "Revise las cohortes de desarrollo de la configuración de poblaciones (DP-05).",
        )
    pobl = construir_poblaciones(
        tabla_desarrollo,
        columnas,
        definicion_objetivo,
        poblaciones.indices,
    )
    folds = construir_folds(desarrollo, experimentos.validacion)
    escenarios = construir_escenarios(catalogo.catalogo, variables.variables)
    verificar_sin_fuga(escenarios, variables.variables)
    matrices = []
    for escenario in escenarios:
        if not escenario.factible:
            continue
        ventana = escenario.ventana.codigo
        matrices.append(
            construir_matriz(
                tabla_desarrollo,
                columnas,
                escenario,
                variables.variables,
                pobl.miembros[(poblaciones.diseno_principal, ventana)],
                poblaciones.indices.periodos[ventana],
                experimentos.matrices,
            )
        )
    return PreparacionDesarrollo(
        diseno=poblaciones.diseno_principal,
        cohortes_desarrollo=desarrollo,
        folds=folds,
        matrices=tuple(matrices),
        no_factibles=tuple(e for e in escenarios if not e.factible),
        periodos_indice=dict(poblaciones.indices.periodos),
    )
