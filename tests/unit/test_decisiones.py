"""Estado de las decisiones DP-01 a DP-20 (H2.8): catálogo y cruce con el registro."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from suficiencia.domain.errores import ConfiguracionInvalida
from suficiencia.domain.trazabilidad.decisiones import (
    DecisionRegistrada,
    catalogo_desde_datos,
    estado_decisiones,
)


def _catalogo_del_repositorio(raiz: Path) -> dict[str, Any]:
    datos = yaml.safe_load(
        (raiz / "config" / "decisiones_metodologicas.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(datos, dict)
    return datos


def _registro(codigo: str) -> DecisionRegistrada:
    return DecisionRegistrada(codigo, "2026-10-29T00:00:00+00:00", "decisión", "equipo", None)


def test_el_catalogo_del_repositorio_lista_las_20_decisiones_sin_valores(raiz: Path) -> None:
    datos = _catalogo_del_repositorio(raiz)
    catalogo = catalogo_desde_datos(datos)
    assert [d.codigo for d in catalogo] == [f"DP-{n:02d}" for n in range(1, 21)]
    # Solo nombre, quién decide y antes de qué: ningún campo de decisión ni de valor.
    assert all(
        set(d) == {"codigo", "nombre", "decide", "resolver_antes_de"} for d in datos["decisiones"]
    )


def test_solo_el_codigo_exacto_registra_una_decision(raiz: Path) -> None:
    catalogo = catalogo_desde_datos(_catalogo_del_repositorio(raiz))
    estados = {
        e.catalogada.codigo: e
        for e in estado_decisiones(
            catalogo, [_registro("DP-16"), _registro("DP-08h"), _registro("DP-08h")]
        )
    }
    assert estados["DP-16"].registrada
    assert not estados["DP-08"].registrada  # un subcódigo no cierra la decisión
    assert [r.codigo for r in estados["DP-08"].subcodigos] == ["DP-08h", "DP-08h"]
    assert sum(e.registrada for e in estados.values()) == 1


@pytest.mark.parametrize(
    "cambio",
    [
        lambda d: d["decisiones"].pop(),
        lambda d: d["decisiones"].append(dict(d["decisiones"][0])),
        lambda d: d["decisiones"][0].update(nombre=" "),
        lambda d: d["decisiones"][0].update(valor="algo"),
        lambda d: d["decisiones"].reverse(),
        lambda d: d.pop("decisiones"),
    ],
)
def test_catalogos_invalidos(raiz: Path, cambio: Any) -> None:
    datos = _catalogo_del_repositorio(raiz)
    cambio(datos)
    with pytest.raises(ConfiguracionInvalida):
        catalogo_desde_datos(datos)
