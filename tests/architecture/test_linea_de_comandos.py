"""PA-02: cada servicio de aplicación se ejecuta desde la línea de comandos.

También comprueba que la línea de comandos no carga Streamlit ni bibliotecas de
aprendizaje automático, que el comando ``suficiencia`` está instalado y que su
salida se puede escribir con la codificación de la consola de Windows (cp1252).
"""

from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

import pytest

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
    raiz: Path,
) -> None:
    """Simula la salida redirigida en Windows, donde Python usa la codificación cp1252.

    Se ejecuta en un proceso aparte para partir de módulos sin cargar.
    """
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
    assert salida.rstrip().endswith("CARGADAS=")
