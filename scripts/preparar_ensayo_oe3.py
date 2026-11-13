"""Prepara el historial del ensayo general de F4.3 con el dataset SINTÉTICO del OE3.

Uso, desde la raíz del repositorio (en Linux o macOS, con ``.venv/bin/python``):

    .venv\\Scripts\\python scripts\\oe3\\generar_dataset_sintetico.py --semilla 20261023 \\
        --salida data\\oe3 --sin-validar
    .venv\\Scripts\\python scripts\\preparar_ensayo_oe3.py data\\oe3 \\
        --salida data\\sintetico\\oe3_ensayo.csv

1. Comprueba que los archivos del generador son los del README del dataset: compara
   el inicio de su huella SHA-256 con la publicada. Si alguna no coincide, se detiene
   y no escribe nada.
2. Arma un solo archivo en el formato del motor (una fila por estudiante y ciclo) con
   el estado de matrícula del archivo longitudinal y las 40 variables del archivo
   ancho (``wide``). Es una conversión del ejemplo, fuera del motor: no es la
   integración de varias tablas de RF-M1-09 y no decide el formato de los datos de la
   institución (DP-15 sigue abierta).
3. Compara la etiqueta que construye el motor con el objetivo ficticio del ensayo y la
   del generador, **solo en las cohortes de desarrollo**: la prueba no se mira.

En la fila del ciclo k, una variable disponible desde T1 lleva su valor a o(Tk) del
archivo ancho (vacío si k > 3 o si el estudiante no estaba en R(Tk) del generador);
una disponible desde T0 lleva su valor a o(T0) en todas las filas. Un ciclo
``matriculado`` con retiro total se escribe como ``retiro_total``.

Los datos son 100 % sintéticos y cada fila lleva ``origen_datos = SINTETICO``. La
salida debe quedar dentro de ``data/``, que git no versiona.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from suficiencia.domain.datos.diccionario import Rol, TipoDato
from suficiencia.domain.datos.objetivo import (
    COLUMNA_ESTADO,
    ColumnasHistorial,
    DefinicionObjetivo,
    construir_objetivo,
)
from suficiencia.persistence.diccionario_yaml import cargar_diccionario
from suficiencia.persistence.objetivo_yaml import cargar_definicion_objetivo

RAIZ = Path(__file__).resolve().parent.parent
DICCIONARIO = RAIZ / "config" / "ejemplos" / "oe3" / "diccionario_oe3_ficticio.yaml"
OBJETIVO = RAIZ / "config" / "ejemplos" / "oe3" / "objetivo_oe3_ficticio.yaml"
ESTADOS = ("positivo", "negativo", "no_etiquetable")
SEMILLA_OE3 = 20261023

# Inicio de la huella SHA-256 de cada archivo, tal como la publica el README del
# dataset (proyecto TP1, claude/README_dataset_sintetico_OE3.md), semilla 20261023.
HUELLAS: dict[str, str] = {
    "dataset_sintetico_longitudinal.csv": "2fbb10171e73066f",
    "dataset_sintetico_wide.csv": "719891af3915f686",
    "particion_temporal_cohortes.csv": "811aca381318c944",
    "ids_cohortes_prueba_bloqueadas.csv": "1b5141992aff4510",
    "fuentes_crudas/estudiantes_admision.csv": "bd2c002131f955d9",
    "fuentes_crudas/matricula_ciclos.csv": "2c6674babfc4da56",
    "fuentes_crudas/cursos_notas.csv": "fb10acf520631ad0",
    "fuentes_crudas/pagos_cuotas.csv": "439566f7f032803d",
    "fuentes_crudas/lms_semanal.csv": "1e6e850abf697f6e",
    "fuentes_crudas/encuesta_socioeconomica.csv": "e670434ed3e32430",
}

VENTANAS_CON_CICLO = {1: "T1", 2: "T2", 3: "T3"}
COLUMNAS_FIJAS = [
    "codigo_estudiante",
    "origen_datos",
    "cohorte",
    "ciclo",
    "fecha_registro",
    "estado_matricula",
]


@dataclass(frozen=True)
class VariableOE3:
    nombre: str
    bloque: str
    ventana_minima: str
    entera: bool


def variables_del_diccionario(archivo: Path = DICCIONARIO) -> list[VariableOE3]:
    """Los rasgos del diccionario del ensayo, en su orden."""
    diccionario = cargar_diccionario(archivo)
    variables = []
    for v in diccionario.de_rol(Rol.RASGO):
        assert v.bloque is not None and v.ventana_minima is not None
        variables.append(
            VariableOE3(v.nombre, v.bloque.value, v.ventana_minima, v.tipo is TipoDato.ENTERO)
        )
    return variables


def huellas_distintas(carpeta: Path) -> list[str]:
    """Archivos que faltan o cuya huella no empieza como la publicada."""
    distintas = []
    for nombre, esperada in HUELLAS.items():
        archivo = carpeta / nombre
        if not archivo.is_file():
            distintas.append(f"{nombre}: no existe")
            continue
        huella = hashlib.sha256(archivo.read_bytes()).hexdigest()
        if not huella.startswith(esperada):
            distintas.append(f"{nombre}: {huella[:16]} (se esperaba {esperada})")
    return distintas


def _entera(serie: pd.Series, nombre: str) -> pd.Series:
    numerica = pd.to_numeric(serie, errors="raise")
    presentes = numerica.dropna()
    if not (presentes == presentes.round()).all():
        raise ValueError(f"La variable entera '{nombre}' tiene valores con decimales.")
    return numerica.astype("Int64")


def convertir(
    longitudinal: pd.DataFrame, ancho: pd.DataFrame, variables: Sequence[VariableOE3]
) -> pd.DataFrame:
    """Una fila por estudiante y ciclo con el estado de matrícula y las 40 variables."""
    retiro = (longitudinal["estado_matricula"] == "matriculado") & (
        longitudinal["retiro_total"] == 1
    )
    historial = pd.DataFrame(
        {
            "codigo_estudiante": longitudinal["id_estudiante"],
            "origen_datos": "SINTETICO",
            "cohorte": longitudinal["periodo_ingreso"],
            "ciclo": longitudinal["ciclo_regular"].astype("int64"),
            "fecha_registro": longitudinal["fecha_registro_estado"],
            "estado_matricula": longitudinal["estado_matricula"].mask(retiro, "retiro_total"),
        }
    )
    por_id = ancho.set_index("id_estudiante")
    if not por_id.index.is_unique:
        raise ValueError("El archivo ancho repite estudiantes.")
    faltan = set(historial["codigo_estudiante"]) - set(por_id.index)
    if faltan:
        raise ValueError(f"{len(faltan)} estudiante(s) del longitudinal no están en el ancho.")
    ids = historial["codigo_estudiante"]
    ciclos = historial["ciclo"]
    for variable in variables:
        if variable.ventana_minima == "T0":
            valores = ids.map(por_id[f"T0_{variable.bloque}_{variable.nombre}"])
        else:
            valores = pd.Series(pd.NA, index=historial.index, dtype="object")
            for ciclo, ventana in VENTANAS_CON_CICLO.items():
                columna = f"{ventana}_{variable.bloque}_{variable.nombre}"
                if columna not in por_id.columns:
                    continue  # la variable aún no está disponible en esa ventana
                filas = ciclos == ciclo
                valores[filas] = ids[filas].map(por_id[columna])
        historial[variable.nombre] = (
            _entera(valores, variable.nombre) if variable.entera else valores
        )
    return historial.sort_values(["cohorte", "codigo_estudiante", "ciclo"]).reset_index(drop=True)


def escribir(historial: pd.DataFrame, salida: Path) -> None:
    """CSV en UTF-8 con fin de línea LF en cualquier sistema, para que la huella del
    historial sea la misma en Windows y en Linux (D-208)."""
    historial.to_csv(salida, index=False, encoding="utf-8", lineterminator="\n")


def etiqueta_del_generador(ancho: pd.DataFrame) -> pd.Series:
    """positivo, negativo o no_etiquetable según las columnas OUT_* del generador."""
    conocida = ancho["OUT_estado_etiqueta"] == "conocida"
    positiva = ancho["OUT_y_desercion"] == 1
    etiqueta = pd.Series("no_etiquetable", index=ancho.index)
    etiqueta[conocida & positiva] = "positivo"
    etiqueta[conocida & ~positiva] = "negativo"
    return pd.Series(etiqueta.to_numpy(), index=ancho["id_estudiante"].to_numpy())


def concordancia(
    historial: pd.DataFrame, ancho: pd.DataFrame, definicion: DefinicionObjetivo
) -> pd.DataFrame:
    """Etiqueta del generador (filas) × etiqueta del motor (columnas), solo en desarrollo.

    Un estudiante que el motor deja fuera de la población inicial cuenta como
    ``fuera_de_poblacion``.
    """
    desarrollo = ancho[ancho["rol_particion"] == "desarrollo"]
    filas = historial["codigo_estudiante"].isin(set(desarrollo["id_estudiante"]))
    columnas = ColumnasHistorial(("codigo_estudiante",), "cohorte", "ciclo", "estado_matricula")
    resultado = construir_objetivo(
        historial.loc[filas, ["codigo_estudiante", "cohorte", "ciclo", "estado_matricula"]],
        columnas,
        definicion,
    )
    motor = resultado.registros.set_index("codigo_estudiante")[COLUMNA_ESTADO]
    generador = etiqueta_del_generador(desarrollo)
    del_motor = motor.reindex(generador.index).fillna("fuera_de_poblacion")
    tabla = pd.crosstab(generador.rename("generador"), del_motor.rename("motor"))
    columnas_tabla = [*ESTADOS, "fuera_de_poblacion"]
    return tabla.reindex(index=list(ESTADOS), columns=columnas_tabla, fill_value=0)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Prepara el historial SINTÉTICO del ensayo de F4.3 con el dataset del OE3."
    )
    analizador.add_argument(
        "carpeta", type=Path, help="Carpeta de salida de scripts/oe3/generar_dataset_sintetico.py."
    )
    analizador.add_argument("--salida", type=Path, required=True, help="Archivo .csv en data/.")
    argumentos = analizador.parse_args(argv)

    salida = argumentos.salida.resolve()
    if not salida.is_relative_to((RAIZ / "data").resolve()):
        print("La salida debe quedar dentro de la carpeta data/ del proyecto.", file=sys.stderr)
        return 1
    distintas = huellas_distintas(argumentos.carpeta)
    if distintas:
        print(
            "Los archivos no son los del dataset del OE3 con la semilla "
            f"{SEMILLA_OE3}; no se usan:",
            file=sys.stderr,
        )
        for linea in distintas:
            print(f"  {linea}", file=sys.stderr)
        return 1
    longitudinal = pd.read_csv(
        argumentos.carpeta / "dataset_sintetico_longitudinal.csv", dtype={"id_estudiante": str}
    )
    ancho = pd.read_csv(
        argumentos.carpeta / "dataset_sintetico_wide.csv", dtype={"id_estudiante": str}
    )
    historial = convertir(longitudinal, ancho, variables_del_diccionario())
    salida.parent.mkdir(parents=True, exist_ok=True)
    escribir(historial, salida)
    print(f"Huellas del dataset del OE3: {len(HUELLAS)} de {len(HUELLAS)} coinciden.")
    print(
        f"Historial SINTÉTICO del ensayo: {len(historial)} filas, "
        f"{historial['codigo_estudiante'].nunique()} estudiantes, "
        f"{historial['cohorte'].nunique()} cohortes -> {argumentos.salida}"
    )
    tabla = concordancia(historial, ancho, cargar_definicion_objetivo(OBJETIVO))
    iguales = int(np.trace(tabla[list(ESTADOS)].to_numpy()))
    print(
        "\nEtiqueta del generador (filas) y del motor con el objetivo ficticio del ensayo "
        "(columnas), solo en las cohortes de desarrollo; la prueba no se mira:"
    )
    print(tabla.to_string())
    print(f"Coinciden {iguales} de {int(tabla.to_numpy().sum())} estudiantes de desarrollo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
