"""Generador sintético, lectores, seudonimización y auditoría (H2.3).

PU-08, PU-14, PU-15 y PU-17 de la especificación, y los criterios de H2.3. Todos
los datos son sintéticos (tests/fixtures/generador_sintetico.py).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fixtures.generador_sintetico import (
    COLUMNAS,
    ORIGEN,
    ciclos_observados,
    generar_historial,
    sembrar_problemas,
)
from suficiencia.domain.datos.auditoria import (
    AuditoriaConErrores,
    auditar,
    exigir_apto,
)
from suficiencia.domain.datos.diccionario import COLUMNA_SEUDONIMO, Diccionario
from suficiencia.domain.errores import ConfiguracionInvalida, DecisionPendiente
from suficiencia.persistence.diccionario_yaml import cargar_diccionario
from suficiencia.persistence.lectores import contenido_canonico, escribir_csv, leer_tabla
from suficiencia.persistence.seudonimizacion import (
    VARIABLE_ENTORNO_CLAVE,
    SeudonimizadorHmac,
)

CLAVE_DE_PRUEBA = b"clave-de-prueba-solo-para-tests-0123456789"
CATEGORIAS_DEL_OBJETIVO = ("matriculado", "no_matriculado", "reserva", "retiro_total", "traslado")


@pytest.fixture(scope="module")
def historial() -> pd.DataFrame:
    return generar_historial(120, semilla=20261028)


@pytest.fixture
def diccionario(raiz: Path) -> Diccionario:
    return cargar_diccionario(raiz / "config" / "ejemplos" / "diccionario_sintetico.yaml")


def _seudonimizar(tabla: pd.DataFrame, diccionario: Diccionario) -> pd.DataFrame:
    return SeudonimizadorHmac(CLAVE_DE_PRUEBA).seudonimizar(tabla, diccionario.identificadores)


# Generador ---------------------------------------------------------------------


def test_el_generador_es_reproducible_y_marca_cada_fila_como_sintetica(
    historial: pd.DataFrame,
) -> None:
    assert historial.equals(generar_historial(120, semilla=20261028))
    assert not historial.equals(generar_historial(120, semilla=1))
    assert tuple(historial.columns) == COLUMNAS
    assert (historial["origen_datos"] == ORIGEN).all()


def test_el_generador_incluye_los_casos_especiales(historial: pd.DataFrame) -> None:
    """Pausas, reingresos, transferencias, retiros y seguimiento incompleto (para H2.4)."""
    por_estudiante = historial.groupby("codigo_estudiante")["estado_matricula"].apply(tuple)
    secuencias = set(por_estudiante)
    assert ("matriculado", "reserva", "matriculado", "matriculado") in secuencias
    assert ("matriculado", "no_matriculado", "matriculado", "matriculado") in secuencias
    assert any(s[-1] == "traslado" for s in secuencias)
    assert any("retiro_total" in s for s in secuencias)
    assert ciclos_observados("2017-2") < ciclos_observados("2014-1") == 8
    recientes = historial[historial["cohorte"] == "2017-2"]
    assert recientes["ciclo"].astype(int).max() == ciclos_observados("2017-2")


def test_el_generador_produce_codigos_con_ceros_a_la_izquierda(historial: pd.DataFrame) -> None:
    assert "00012345" in set(historial["codigo_estudiante"])
    assert historial["codigo_estudiante"].str.fullmatch(r"[0-9]{8}").all()


# PU-14: lectura con tipos declarados -------------------------------------------


@pytest.mark.parametrize("extension", [".csv", ".xlsx"])
def test_pu14_un_archivo_conforme_se_importa_con_sus_tipos_y_ceros_a_la_izquierda(
    tmp_path: Path, historial: pd.DataFrame, diccionario: Diccionario, extension: str
) -> None:
    archivo = tmp_path / f"historial{extension}"
    if extension == ".csv":
        historial.to_csv(archivo, index=False)
    else:
        historial.to_excel(archivo, index=False)
    leida = leer_tabla(archivo)
    assert "00012345" in set(leida.tabla["codigo_estudiante"])
    assert leida.huella_fuente.valor == leida.huella_fuente.de_bytes(archivo.read_bytes()).valor

    resultado = auditar(_seudonimizar(leida.tabla, diccionario), diccionario)
    assert resultado.informe.errores_criticos == ()
    assert resultado.informe.apto_para_m2
    assert resultado.informe.sintetico
    tipos = resultado.tabla.dtypes
    assert str(tipos["ciclo"]) == "Int64"
    assert str(tipos["puntaje_admision"]) == "Float64"
    assert str(tipos["beca_al_ingreso"]) == "boolean"
    assert str(tipos["fecha_registro"]).startswith("datetime64")


def test_pu14_el_seudonimo_se_calcula_sobre_el_codigo_con_sus_ceros(
    tmp_path: Path, historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    archivo = tmp_path / "h.csv"
    historial.to_csv(archivo, index=False)
    seudonimizada = _seudonimizar(leer_tabla(archivo).tabla, diccionario)
    esperado = SeudonimizadorHmac(CLAVE_DE_PRUEBA).seudonimo(("00012345",))
    assert esperado in set(seudonimizada[COLUMNA_SEUDONIMO])
    assert SeudonimizadorHmac(CLAVE_DE_PRUEBA).seudonimo(("12345",)) != esperado


@pytest.mark.parametrize(
    ("columna", "valor", "mensaje"),
    [
        ("ciclo", "tres", "no son de tipo entero"),
        ("puntaje_admision", "60,5", "no son de tipo decimal"),
        ("fecha_registro", "15/03/2014", "no son de tipo fecha"),
        ("beca_al_ingreso", "quizas", "no son de tipo booleano"),
        ("ciclo", "9", "fuera de su dominio"),
        ("estado_matricula", "egresado", "fuera de su dominio"),
        ("cohorte", "2014-3", "fuera de su dominio"),
    ],
)
def test_pu14_tipos_incorrectos_y_valores_fuera_de_dominio_se_rechazan_con_su_motivo(
    historial: pd.DataFrame, diccionario: Diccionario, columna: str, valor: str, mensaje: str
) -> None:
    tabla = historial.copy()
    tabla.loc[4, columna] = valor
    informe = auditar(_seudonimizar(tabla, diccionario), diccionario).informe
    assert not informe.apto_para_m2
    assert any(columna in e and mensaje in e for e in informe.errores_criticos)
    problema = next(c for c in informe.columnas if c.nombre == columna)
    assert 5 in problema.filas_con_problemas


def test_pu14_una_columna_faltante_o_no_declarada_se_rechaza(
    historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    tabla = historial.drop(columns=["tipo_colegio"]).assign(dni="12345678")
    informe = auditar(_seudonimizar(tabla, diccionario), diccionario).informe
    assert "Falta la columna 'tipo_colegio' declarada en el diccionario." in (
        informe.errores_criticos
    )
    assert any("'dni' no está en el diccionario" in e for e in informe.errores_criticos)


def test_un_archivo_que_no_es_csv_ni_excel_se_rechaza(tmp_path: Path) -> None:
    archivo = tmp_path / "datos.json"
    archivo.write_text("{}", encoding="utf-8")
    with pytest.raises(ConfiguracionInvalida, match=r"no es CSV ni Excel"):
        leer_tabla(archivo)


# PU-15 y PU-17: auditoría ------------------------------------------------------


def test_pu15_la_auditoria_detecta_los_problemas_sembrados(
    historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    con_problemas, sembrados = sembrar_problemas(historial)
    informe = auditar(_seudonimizar(con_problemas, diccionario), diccionario).informe
    puntaje = next(c for c in informe.columnas if c.nombre == "puntaje_admision")
    creditos = next(c for c in informe.columnas if c.nombre == "creditos_aprobados_ciclo")
    assert puntaje.nulos == 1
    assert puntaje.fuera_de_dominio == 1
    assert sembrados.fila_nula_obligatoria in puntaje.filas_con_problemas
    assert sembrados.fila_fuera_de_rango in puntaje.filas_con_problemas
    assert creditos.tipo_invalido == 1
    assert sembrados.fila_tipo_invalido in creditos.filas_con_problemas
    assert informe.duplicados_clave == 1
    assert informe.filas_duplicadas == 1
    assert len(informe.errores_criticos) == 4


def test_pu15_la_auditoria_no_expone_la_distribucion_de_la_clase(
    historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    """De la columna del objetivo solo se informan vacíos e inválidos: nada por valor."""
    informe = auditar(_seudonimizar(historial, diccionario), diccionario).informe
    objetivo = next(c for c in informe.columnas if c.nombre == "estado_matricula")
    assert objetivo.cardinalidad is None
    assert objetivo.minimo is None
    assert objetivo.maximo is None
    texto = repr(informe)
    for categoria in CATEGORIAS_DEL_OBJETIVO:
        assert categoria not in texto


def test_pu17_una_auditoria_con_errores_criticos_impide_pasar_a_m2(
    historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    con_problemas, _ = sembrar_problemas(historial)
    informe = auditar(_seudonimizar(con_problemas, diccionario), diccionario).informe
    with pytest.raises(AuditoriaConErrores, match="error"):
        exigir_apto(informe)
    exigir_apto(auditar(_seudonimizar(historial, diccionario), diccionario).informe)


def test_una_tabla_sin_seudonimizar_no_pasa_la_auditoria(
    historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    informe = auditar(historial, diccionario).informe
    assert any("no se seudonimizó" in e for e in informe.errores_criticos)


# PU-08: seudonimización ----------------------------------------------------------


def test_pu08_elimina_los_identificadores_y_repite_el_seudonimo_del_mismo_valor(
    historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    original = historial.copy()
    seudonimizada = _seudonimizar(historial, diccionario)
    assert "codigo_estudiante" not in seudonimizada.columns
    assert historial.equals(original), "la tabla original no debe modificarse"
    pares = pd.DataFrame(
        {"codigo": historial["codigo_estudiante"], "seudonimo": seudonimizada["seudonimo"]}
    ).drop_duplicates()
    assert pares["codigo"].is_unique
    assert pares["seudonimo"].is_unique
    codigos = set(historial["codigo_estudiante"])
    celdas = {str(v) for v in seudonimizada.to_numpy().ravel().tolist()}
    assert codigos.isdisjoint(celdas), "ningún identificador original sale de la seudonimización"


def test_pu08_otra_clave_produce_otros_seudonimos() -> None:
    a = SeudonimizadorHmac(CLAVE_DE_PRUEBA)
    b = SeudonimizadorHmac(CLAVE_DE_PRUEBA[::-1])
    assert a.seudonimo(("00012345",)) == a.seudonimo(("00012345",))
    assert a.seudonimo(("00012345",)) != b.seudonimo(("00012345",))
    assert len(a.seudonimo(("x",))) == 24


def test_una_fila_sin_identificador_queda_sin_seudonimo(diccionario: Diccionario) -> None:
    tabla = pd.DataFrame({"codigo_estudiante": ["00000001", " "], "otro": ["a", "b"]})
    seudonimizada = SeudonimizadorHmac(CLAVE_DE_PRUEBA).seudonimizar(tabla, ("codigo_estudiante",))
    assert pd.notna(seudonimizada.loc[0, COLUMNA_SEUDONIMO])
    assert pd.isna(seudonimizada.loc[1, COLUMNA_SEUDONIMO])


def test_sin_clave_la_causa_es_dp14(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VARIABLE_ENTORNO_CLAVE, raising=False)
    with pytest.raises(DecisionPendiente) as error:
        SeudonimizadorHmac.desde_entorno()
    assert error.value.decision == "DP-14"


def test_la_clave_puede_venir_del_entorno_y_debe_ser_larga(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_ENTORNO_CLAVE, "x" * 40)
    assert SeudonimizadorHmac.desde_entorno().seudonimo(("1",))
    with pytest.raises(ConfiguracionInvalida, match="demasiado corta"):
        SeudonimizadorHmac(b"corta")


def test_la_clave_efimera_cambia_en_cada_ejecucion() -> None:
    a = SeudonimizadorHmac.con_clave_efimera().seudonimo(("1",))
    b = SeudonimizadorHmac.con_clave_efimera().seudonimo(("1",))
    assert a != b


# Huella y escritura del dataset procesado --------------------------------------


def test_el_dataset_procesado_tiene_huella_estable_y_no_se_sobrescribe(
    tmp_path: Path, historial: pd.DataFrame, diccionario: Diccionario
) -> None:
    tabla = auditar(_seudonimizar(historial, diccionario), diccionario).tabla
    archivo = tmp_path / "procesado.csv"
    huella = escribir_csv(tabla, archivo)
    assert huella.valor == huella.de_bytes(archivo.read_bytes()).valor
    assert contenido_canonico(tabla) == archivo.read_bytes()
    with pytest.raises(ConfiguracionInvalida, match="no se sobrescriben"):
        escribir_csv(tabla, archivo)
