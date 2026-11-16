"""Testes unitários para as funções de normalização e resolução de aliases (M4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from data.prepare_data import (
    load_aliases,
    normalize_name,
    resolve_iso,
)


def test_normalize_name() -> None:
    assert normalize_name("São Tomé and Príncipe") == "sao tome and principe"
    assert normalize_name("CÔTE D'IVOIRE") == "cote d ivoire"
    assert normalize_name("  Reunion,   FOC  ") == "reunion foc"
    assert normalize_name("Bosnia & Herzegovina!") == "bosnia herzegovina"
    assert normalize_name("") == ""


def test_load_aliases_and_resolve(tmp_path: Path) -> None:
    csv_file = tmp_path / "country_aliases.csv"
    csv_file.write_text(
        "alias,iso3,parent_iso3,note\n"
        "Diamond Princess,DROP,,Cruzeiro descartado\n"
        "Martinique,MTQ,FRA,Territorio ultramarino\n"
        "Burma,MMR,,Mianmar\n"
        "iata:PRN,KOS,,Aeroporto de Pristina\n",
        encoding="utf-8",
    )

    aliases, drops, iata = load_aliases(csv_file)

    assert "diamond princess" in drops
    assert "DIAMOND PRINCESS" in drops
    assert "iata:PRN" not in drops
    assert iata["PRN"] == "KOS"

    owid_names = {"brasil": "BRA", "france": "FRA"}

    # Resolução de DROP
    iso, parent = resolve_iso("Diamond Princess", aliases, drops, owid_names)
    assert iso == "DROP"
    assert parent is None

    # Resolução com parent_iso3 (agregado)
    iso, parent = resolve_iso("Martinique", aliases, drops, owid_names)
    assert iso == "MTQ"
    assert parent == "FRA"

    # Resolução de alias comum
    iso, parent = resolve_iso("Burma", aliases, drops, owid_names)
    assert iso == "MMR"
    assert parent is None

    # Resolução direta pelo nome OWID
    iso, parent = resolve_iso("Brasil", aliases, drops, owid_names)
    assert iso == "BRA"
    assert parent is None

    # Nome não reconhecido
    iso, parent = resolve_iso("Atlantis", aliases, drops, owid_names)
    assert iso is None
    assert parent is None


def test_finalize_series_logic(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    from data.prepare_data import finalize_series

    data = pd.DataFrame(
        [
            {"iso3": "BRA", "date": "2020-03-01", "cases": 10, "deaths": 1, "recovered": 0},
            # Salto temporal de 2 dias (deve ser preenchido)
            {"iso3": "BRA", "date": "2020-03-04", "cases": 30, "deaths": 2, "recovered": 5},
            # Queda retroativa no acumulado (deve ser corrigida pelo cummax)
            {"iso3": "BRA", "date": "2020-03-05", "cases": 25, "deaths": 2, "recovered": 4},
        ]
    )

    final_df = finalize_series(data, valid_iso3={"BRA"}, has_recovered=True)

    assert len(final_df) == 5  # 01, 02, 03, 04, 05 de março
    dates = list(final_df["date"])
    assert dates == [
        "2020-03-01",
        "2020-03-02",
        "2020-03-03",
        "2020-03-04",
        "2020-03-05",
    ]

    cases = list(final_df["cases"])
    # 02 e 03 devem ter forward-fill de 10; 05 deve ter cummax de 30 (não pode cair para 25)
    assert cases == [10, 10, 10, 30, 30]

    rec = list(final_df["recovered"])
    assert rec == [0, 0, 0, 5, 5]
