"""Testes unitários para as funções de normalização e resolução de aliases (M4)."""

from __future__ import annotations

from pathlib import Path

from data.prepare_data import (
    _calculate_centroid_with_antimeridian,
    finalize_series,
    load_aliases,
    normalize_name,
    resolve_covid_row_iso,
    resolve_iso,
    validate_processed_data,
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


def test_finalize_series_logic() -> None:
    data = [
        {"iso3": "BRA", "date": "2020-03-01", "cases": 10, "deaths": 1, "recovered": 0},
        # Salto temporal de 2 dias (deve ser preenchido)
        {"iso3": "BRA", "date": "2020-03-04", "cases": 30, "deaths": 2, "recovered": 5},
        # Queda retroativa no acumulado (deve ser corrigida pelo cummax)
        {"iso3": "BRA", "date": "2020-03-05", "cases": 25, "deaths": 2, "recovered": 4},
    ]

    final_rows = finalize_series(data, valid_iso3={"BRA"}, has_recovered=True)

    assert len(final_rows) == 5  # 01, 02, 03, 04, 05 de março
    dates = [r["date"] for r in final_rows]
    assert dates == [
        "2020-03-01",
        "2020-03-02",
        "2020-03-03",
        "2020-03-04",
        "2020-03-05",
    ]

    cases = [r["cases"] for r in final_rows]
    # 02 e 03 devem ter forward-fill de 10; 05 deve ter cummax de 30 (não pode cair para 25)
    assert cases == [10, 10, 10, 30, 30]

    rec = [r["recovered"] for r in final_rows]
    assert rec == [0, 0, 0, 5, 5]


def test_finalize_series_d21_territory_aggregation() -> None:
    """Verifica a Decisão D21: ffill e cummax por origin_id antes de somar no país-mãe."""
    rows = [
        # França metropolitana reporta nos dias 01 e 02
        {"iso3": "FRA", "origin_id": "FRA", "date": "2009-05-01", "cases": 100, "deaths": 1},
        {"iso3": "FRA", "origin_id": "FRA", "date": "2009-05-02", "cases": 110, "deaths": 2},
        # Guadalupe (agregada a FRA) reporta nos dias 01 e 03, mas omite o dia 02
        {"iso3": "FRA", "origin_id": "GLP", "date": "2009-05-01", "cases": 15, "deaths": 0},
        {"iso3": "FRA", "origin_id": "GLP", "date": "2009-05-03", "cases": 20, "deaths": 1},
    ]

    final_rows = finalize_series(rows, valid_iso3={"FRA"}, has_recovered=False)
    assert [r["date"] for r in final_rows] == ["2009-05-01", "2009-05-02", "2009-05-03"]
    # Dia 01: 100 + 15 = 115; Dia 02: 110 + 15 (ffill GLP) = 125; Dia 03: 110 (ffill FRA) + 20 = 130
    assert [r["cases"] for r in final_rows] == [115, 125, 130]
    assert [r["deaths"] for r in final_rows] == [1, 2, 3]


def test_real_country_aliases_and_covid_province_resolution() -> None:
    """Verifica os aliases reais em data/country_aliases.csv e a prioridade de Province/State."""
    repo_root = Path(__file__).resolve().parents[2]
    aliases_csv = repo_root / "data" / "country_aliases.csv"
    aliases, drops, _iata = load_aliases(aliases_csv)
    owid_names = {"china": "CHN", "denmark": "DNK", "canada": "CAN", "united kingdom": "GBR"}
    valid_iso3 = {"USA", "IRL", "VAT", "HKG", "MAC", "GRL", "GBR", "FRA", "CHN", "DNK", "CAN"}

    assert resolve_iso("United States of America", aliases, drops, owid_names) == ("USA", None)
    assert resolve_iso("Republic of Ireland", aliases, drops, owid_names) == ("IRL", None)
    assert resolve_iso("Holy See", aliases, drops, owid_names) == ("VAT", None)
    assert resolve_iso("Guadeloupe FOC", aliases, drops, owid_names) == ("GLP", "FRA")

    # Entidades autônomas em Province/State não são engolidas pelo país-mãe no JHU
    assert resolve_covid_row_iso("China", "Hong Kong", aliases, drops, owid_names, valid_iso3) == (
        "HKG",
        "HKG",
    )
    assert resolve_covid_row_iso(
        "Denmark", "Greenland", aliases, drops, owid_names, valid_iso3
    ) == ("GRL", "GRL")
    # Território fundido (D9) preserva origin_id próprio para a regra D21
    assert resolve_covid_row_iso(
        "United Kingdom", "Gibraltar", aliases, drops, owid_names, valid_iso3
    ) == ("GBR", "GIB")
    # Província doméstica cai no país-mãe com origin_id composto
    assert resolve_covid_row_iso("Canada", "Alberta", aliases, drops, owid_names, valid_iso3) == (
        "CAN",
        "CAN:Alberta",
    )


def test_calculate_centroid_with_antimeridian_d15() -> None:
    """Verifica o cálculo real de centróide no antimeridiano (D15)."""
    geom_fji = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[178.0, -18.0], [180.0, -18.0], [180.0, -16.0], [178.0, -16.0], [178.0, -18.0]]],
            [
                [
                    [-180.0, -18.0],
                    [-179.0, -18.0],
                    [-179.0, -16.0],
                    [-180.0, -16.0],
                    [-180.0, -18.0],
                ]
            ],
        ],
    }
    lat, lon = _calculate_centroid_with_antimeridian(geom_fji, "FJI")
    assert -18.0 <= lat <= -16.0
    assert lon > 178.0  # Centróide permanece próximo a +179.5°, não perto de 0°


def test_validate_processed_data_integrity() -> None:
    """Valida a integridade estrutural dos arquivos reais em data/processed/."""
    repo_root = Path(__file__).resolve().parents[2]
    processed_dir = repo_root / "data" / "processed"
    errors = validate_processed_data(processed_dir)
    assert errors == []
