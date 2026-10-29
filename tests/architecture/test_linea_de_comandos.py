"""PA-02: cada servicio de aplicación se ejecuta desde la línea de comandos.

También comprueba que la línea de comandos no carga Streamlit ni bibliotecas de
aprendizaje automático, que el comando ``suficiencia`` está instalado y que su
salida se puede escribir con la codificación de la consola de Windows (cp1252).
"""

from __future__ import annotations

import importlib.metadata
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from fixtures.generador_sintetico import generar_historial, sembrar_problemas
from suficiencia.cli import (
    SALIDA_CORRECTA,
    SALIDA_ERROR,
    SALIDA_NO_DISPONIBLE,
    SALIDA_USO_INCORRECTO,
    main,
)

# Un caso de uso de cada servicio (sección 6 de la especificación).
UN_CASO_POR_SERVICIO = {
    "datos": "CU-01",
    "escenarios": "CU-04",
    "protocolo": "CU-05",
    "experimentos": "CU-06",
    "evaluacion_final": "CU-08",
    "interpretabilidad": "CU-09",
    "reportes": "CU-10",
}
BIBLIOTECAS_PROHIBIDAS = ("streamlit", "plotly", "sklearn", "xgboost", "lightgbm", "shap", "lime")


def _correr(
    argumentos: list[str], raiz: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    codigo = main(["--raiz", str(raiz), *argumentos])
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def test_estado_lista_todos_los_servicios(raiz: Path, capsys: pytest.CaptureFixture[str]) -> None:
    codigo, salida, _ = _correr(["estado"], raiz, capsys)
    assert codigo == SALIDA_CORRECTA
    for servicio in UN_CASO_POR_SERVICIO:
        assert f"Servicio {servicio}:" in salida
    for numero in range(1, 13):
        assert f"CU-{numero:02d}" in salida


@pytest.mark.parametrize(("servicio", "caso"), UN_CASO_POR_SERVICIO.items())
def test_cada_servicio_se_ejecuta_desde_la_linea_de_comandos(
    raiz: Path, capsys: pytest.CaptureFixture[str], servicio: str, caso: str
) -> None:
    codigo, salida, error = _correr(["ejecutar", caso], raiz, capsys)
    assert codigo == SALIDA_NO_DISPONIBLE, (servicio, salida, error)
    assert f"El caso de uso {caso} todavía no está implementado." in error
    assert "Acción sugerida" in error


def test_config_validar_acepta_la_configuracion_del_repositorio(
    raiz: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo, salida, _ = _correr(["config", "validar"], raiz, capsys)
    assert codigo == SALIDA_CORRECTA
    assert "Configuración válida" in salida
    assert "Semilla global: pendiente" in salida


def test_config_validar_rechaza_un_archivo_invalido(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalido = tmp_path / "proyecto.yaml"
    invalido.write_text("version_configuracion: 99\n", encoding="utf-8")
    codigo, _, error = _correr(["config", "validar", "--archivo", str(invalido)], raiz, capsys)
    assert codigo == SALIDA_ERROR
    assert "Configuración NO válida" in error
    assert "Acción sugerida" in error


EJEMPLOS = [
    "--configuracion",
    "config/ejemplos/escenarios_ficticio.yaml",
    "--variables",
    "config/ejemplos/variables_ficticias.yaml",
]


def test_escenarios_con_los_ejemplos_ficticios(
    raiz: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(raiz)
    codigo, salida, _ = _correr(["escenarios", *EJEMPLOS], raiz, capsys)
    assert codigo == SALIDA_CORRECTA
    assert salida.startswith("EJEMPLO FICTICIO")
    assert "Escenarios: 32 (factibles: 28; no factibles: 4)" in salida
    assert "T0  A+B       NO factible  sin variables en B" in salida
    assert "Verificación anti-fuga: correcta" in salida
    assert "a_ficticia_ingreso" not in salida


def test_escenarios_con_detalle_muestra_las_variables(
    raiz: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(raiz)
    codigo, salida, _ = _correr(["escenarios", *EJEMPLOS, "--detalle"], raiz, capsys)
    assert codigo == SALIDA_CORRECTA
    assert "a_ficticia_ingreso" in salida


def test_escenarios_con_la_configuracion_del_proyecto_se_detiene_por_dp01d(
    raiz: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo, salida, error = _correr(["escenarios"], raiz, capsys)
    assert codigo == SALIDA_ERROR
    assert salida == ""
    assert "DP-01d" in error


DICCIONARIO = "config/ejemplos/diccionario_sintetico.yaml"


def test_datos_diccionario(
    raiz: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(raiz)
    codigo, salida, _ = _correr(["datos", "diccionario", DICCIONARIO], raiz, capsys)
    assert codigo == SALIDA_CORRECTA
    assert salida.startswith("EJEMPLO FICTICIO")
    assert "Rasgos (8)" in salida


def _proyecto(tmp_path: Path, tabla: pd.DataFrame) -> Path:
    (tmp_path / "data").mkdir(exist_ok=True)
    archivo = tmp_path / "data" / "fuente.csv"
    tabla.to_csv(archivo, index=False)
    return archivo


def test_datos_importar_un_archivo_sintetico(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tabla = generar_historial(30, semilla=5)
    archivo = _proyecto(tmp_path, tabla)
    argumentos = ["datos", "importar", str(archivo), "--diccionario", str(raiz / DICCIONARIO)]
    codigo, salida, _ = _correr(
        [*argumentos, "--clave-efimera", "--salida", "data/interim/p.csv"], tmp_path, capsys
    )
    assert codigo == SALIDA_CORRECTA
    assert salida.startswith("DATOS SINTÉTICOS")
    assert "Resultado: APTO para M2" in salida
    assert "distribución omitida (columna del objetivo)" in salida
    assert (tmp_path / "data" / "interim" / "p.csv").is_file()
    for codigo_estudiante in tabla["codigo_estudiante"]:
        assert codigo_estudiante not in salida


def test_datos_importar_con_errores_o_sin_clave_termina_con_codigo_1(
    raiz: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUFICIENCIA_CLAVE_SEUDONIMO", raising=False)
    con_problemas, _ = sembrar_problemas(generar_historial(30, semilla=5))
    archivo = _proyecto(tmp_path, con_problemas)
    argumentos = ["datos", "importar", str(archivo), "--diccionario", str(raiz / DICCIONARIO)]
    codigo, salida, _ = _correr([*argumentos, "--clave-efimera"], tmp_path, capsys)
    assert codigo == SALIDA_ERROR
    assert "Resultado: NO APTO" in salida
    codigo, _, error = _correr(argumentos, tmp_path, capsys)
    assert codigo == SALIDA_ERROR
    assert "DP-14" in error


def test_escenarios_desde_el_diccionario(
    raiz: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(raiz)
    codigo, salida, _ = _correr(
        [
            "escenarios",
            "--configuracion",
            "config/ejemplos/escenarios_ficticio.yaml",
            "--diccionario",
            DICCIONARIO,
        ],
        raiz,
        capsys,
    )
    assert codigo == SALIDA_CORRECTA
    assert "con 8 variables evaluadas" in salida


def _proyecto_con_config(tmp_path: Path, raiz: Path) -> Path:
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "proyecto.yaml").write_bytes(
        (raiz / "config" / "proyecto.yaml").read_bytes()
    )
    return tmp_path


def test_entorno(raiz: Path, capsys: pytest.CaptureFixture[str]) -> None:
    codigo, salida, _ = _correr(["entorno"], raiz, capsys)
    assert codigo == SALIDA_CORRECTA
    assert "Huella de requirements.lock:" in salida
    assert "OMP_NUM_THREADS" in salida


def test_registro_decision_ver_verificar_y_exportar(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proyecto = _proyecto_con_config(tmp_path, raiz)
    codigo, salida, _ = _correr(
        [
            "registro",
            "decision",
            "--codigo",
            "DP-16",
            "--decision",
            "SQLite para el registro",
            "--justificacion",
            "prueba",
            "--responsable",
            "pruebas",
        ],
        proyecto,
        capsys,
    )
    assert codigo == SALIDA_CORRECTA
    assert "Decisión registrada: n.º 1, DP-16" in salida
    codigo, salida, _ = _correr(["registro", "ver", "decisiones"], proyecto, capsys)
    assert codigo == SALIDA_CORRECTA
    assert "Decisiones: 1" in salida
    codigo, salida, _ = _correr(["registro", "verificar"], proyecto, capsys)
    assert codigo == SALIDA_CORRECTA
    assert "Integridad correcta" in salida
    codigo, salida, _ = _correr(
        ["registro", "exportar", "decisiones", "--salida", "reports/d.xlsx"], proyecto, capsys
    )
    assert codigo == SALIDA_CORRECTA
    assert (proyecto / "reports" / "d.xlsx").is_file()


def test_registro_verificar_detecta_una_modificacion(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proyecto = _proyecto_con_config(tmp_path, raiz)
    for numero in (1, 2):
        _correr(
            [
                "registro",
                "decision",
                "--codigo",
                f"DP-0{numero}",
                "--decision",
                "d",
                "--justificacion",
                "j",
                "--responsable",
                "r",
            ],
            proyecto,
            capsys,
        )
    conexion = sqlite3.connect(proyecto / "workspace" / "registro.sqlite")
    try:
        conexion.execute("DROP TRIGGER decisiones_sin_borrar")
        conexion.execute("DELETE FROM decisiones WHERE numero = 1")
        conexion.commit()
    finally:
        conexion.close()
    codigo, salida, _ = _correr(["registro", "verificar"], proyecto, capsys)
    assert codigo == SALIDA_ERROR
    assert "Integridad ROTA" in salida


def test_registro_demostracion(
    raiz: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proyecto = _proyecto_con_config(tmp_path, raiz)
    codigo, salida, _ = _correr(["registro", "demostracion"], proyecto, capsys)
    assert codigo == SALIDA_CORRECTA
    assert "exploratorio exitosa" in salida
    assert "exploratorio fallida - RuntimeError: falla simulada a propósito" in salida


@pytest.mark.parametrize("argumentos", [[], ["ejecutar", "XX"], ["desconocido"]])
def test_un_uso_incorrecto_termina_con_codigo_2(
    raiz: Path, capsys: pytest.CaptureFixture[str], argumentos: list[str]
) -> None:
    with pytest.raises(SystemExit) as salida:
        main(["--raiz", str(raiz), *argumentos])
    assert salida.value.code == SALIDA_USO_INCORRECTO
    assert "Uso: suficiencia" in capsys.readouterr().err


def test_el_comando_suficiencia_esta_instalado() -> None:
    puntos = importlib.metadata.entry_points(group="console_scripts", name="suficiencia")
    assert [p.value for p in puntos] == ["suficiencia.cli:main"], (
        "Reinstale el paquete: python -m pip install --no-deps --no-build-isolation -e ."
    )


def test_la_salida_se_puede_escribir_en_cp1252_sin_cargar_bibliotecas_prohibidas(
    raiz: Path, tmp_path: Path
) -> None:
    """Simula la salida redirigida en Windows, donde Python usa la codificación cp1252.

    Se ejecuta en un proceso aparte para partir de módulos sin cargar.
    """
    (tmp_path / "data").mkdir()
    generar_historial(15, semilla=2).to_csv(tmp_path / "data" / "bien.csv", index=False)
    con_problemas, _ = sembrar_problemas(generar_historial(15, semilla=2))
    con_problemas.to_csv(tmp_path / "data" / "mal.csv", index=False)
    _proyecto_con_config(tmp_path, raiz)
    diccionario = str(raiz / "config" / "ejemplos" / "diccionario_sintetico.yaml")
    codigo = (
        "import sys\n"
        "from suficiencia.cli import main\n"
        f"raiz = {str(raiz)!r}\n"
        "ejemplos = ['--configuracion', raiz + '/config/ejemplos/escenarios_ficticio.yaml',\n"
        "            '--variables', raiz + '/config/ejemplos/variables_ficticias.yaml']\n"
        "for argumentos in (['estado'], ['config', 'validar'], ['ejecutar', 'CU-03'],\n"
        "                   ['ejecutar', 'CU-04'], ['ejecutar', 'CU-13'], ['escenarios'],\n"
        "                   ['escenarios', *ejemplos, '--detalle']):\n"
        "    main(['--raiz', raiz, *argumentos])\n"
        f"diccionario = {diccionario!r}\n"
        f"proyecto = {str(tmp_path)!r}\n"
        "main(['datos', 'diccionario', diccionario])\n"
        "main(['--raiz', raiz, 'entorno'])\n"
        "for argumentos in (['registro', 'decision', '--codigo', 'DP-16', '--decision',\n"
        "                    'Decisión de prueba', '--justificacion', 'j', '--responsable', 'r'],\n"
        "                   ['registro', 'ver', 'decisiones'], ['registro', 'verificar'],\n"
        "                   ['registro', 'demostracion']):\n"
        "    main(['--raiz', proyecto, *argumentos])\n"
        "objetivo = raiz + '/config/ejemplos/objetivo_ficticio.yaml'\n"
        "main(['--raiz', raiz, 'objetivo', 'validar', objetivo])\n"
        "main(['--raiz', raiz, 'objetivo', 'demostracion'])\n"
        "main(['--raiz', proyecto, 'objetivo', 'construir', proyecto + '/data/bien.csv',\n"
        "      '--diccionario', diccionario, '--definicion', objetivo, '--clave-efimera'])\n"
        "for archivo in ('bien.csv', 'mal.csv'):\n"
        "    main(['--raiz', proyecto, 'datos', 'importar', proyecto + '/data/' + archivo,\n"
        "          '--diccionario', diccionario, '--clave-efimera'])\n"
        f"cargadas = [m for m in {BIBLIOTECAS_PROHIBIDAS!r} if m in sys.modules]\n"
        "print('CARGADAS=' + ','.join(cargadas))\n"
    )
    entorno = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    proceso = subprocess.run(
        [sys.executable, "-c", codigo],
        capture_output=True,
        env=entorno,
        check=False,
    )
    assert proceso.returncode == 0, proceso.stderr.decode("cp1252", errors="replace")
    salida = proceso.stdout.decode("cp1252")
    assert "CU-12" in salida
    assert "Verificación anti-fuga: correcta" in salida
    assert "Resultado: APTO" in salida
    assert "ERROR CRÍTICO" in salida
    assert "Integridad correcta" in salida
    assert "DEMOSTRACIÓN" in salida
    assert "Definición del objetivo válida" in salida
    assert "DEMOSTRACIÓN: historiales FICTICIOS" in salida
    assert "omitida hasta el sellado" in salida
    assert salida.rstrip().endswith("CARGADAS=")
