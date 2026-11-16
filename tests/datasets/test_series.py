"""Testes unitários para o leitor e indexador de séries temporais (M4 — datasets/series.py)."""

from __future__ import annotations

from pathlib import Path

import pytest
from epidemia.datasets.series import (
    PANDEMIC_COVID19,
    PANDEMIC_SARS,
    DailyRecord,
    PandemicSeries,
    load_pandemic_series,
)


@pytest.fixture
def sample_sars_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "sars.csv"
    content = (
        "iso3,date,cases,deaths,recovered\n"
        "CHN,2003-03-17,100,5,20\n"
        "CHN,2003-03-18,120,6,25\n"
        "CHN,2003-03-19,150,8,30\n"
        "HKG,2003-03-17,50,2,10\n"
        "HKG,2003-03-18,60,3,12\n"
        "HKG,2003-03-19,75,4,15\n"
    )
    csv_file.write_text(content, encoding="utf-8")
    return csv_file


@pytest.fixture
def sample_covid_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "covid19.csv"
    content = (
        "iso3,date,cases,deaths,recovered\n"
        "BRA,2020-02-26,1,0,\n"
        "BRA,2020-02-27,1,0,\n"
        "BRA,2020-02-28,2,0,\n"
        "USA,2020-02-26,15,0,\n"
        "USA,2020-02-27,16,0,\n"
        "USA,2020-02-28,19,1,\n"
    )
    csv_file.write_text(content, encoding="utf-8")
    return csv_file


def test_load_pandemic_series_sars_with_recovered(sample_sars_csv: Path) -> None:
    series = load_pandemic_series(sample_sars_csv, PANDEMIC_SARS)

    assert isinstance(series, PandemicSeries)
    assert series.name == PANDEMIC_SARS
    assert series.total_days == 3
    assert series.first_date == "2003-03-17"
    assert series.last_date == "2003-03-19"
    assert series.countries == ("CHN", "HKG")

    # Busca por índice de dia (int)
    rec_day0 = series.get_record("CHN", 0)
    assert rec_day0 is not None
    assert rec_day0.iso3 == "CHN"
    assert rec_day0.date == "2003-03-17"
    assert rec_day0.cases == 100
    assert rec_day0.deaths == 5
    assert rec_day0.recovered == 20
    assert rec_day0.cumulative_cases == 100

    # Busca por string de data
    rec_date = series.get_record("CHN", "2003-03-19")
    assert rec_date is not None
    assert rec_date.cases == 150
    assert rec_date.deaths == 8
    assert rec_date.recovered == 30

    # Busca país ausente
    assert series.get_record("BRA", 0) is None
    assert series.get_record("CHN", 999) is None

    # Séries completas de um país
    chn_series = series.country_series("CHN")
    assert len(chn_series) == 3
    assert series.cumulative_cases_series("CHN") == (100, 120, 150)
    assert series.deaths_series("CHN") == (5, 6, 8)
    assert series.recovered_series("CHN") == (20, 25, 30)

    # Totais globais no dia
    # Dia 0: CHN(100, 5, 20) + HKG(50, 2, 10) = (150, 7, 30)
    assert series.daily_totals(0) == (150, 7, 30)
    # Dia 2: CHN(150, 8, 30) + HKG(75, 4, 15) = (225, 12, 45)
    assert series.daily_totals(2) == (225, 12, 45)


def test_load_pandemic_series_covid_without_recovered(sample_covid_csv: Path) -> None:
    series = load_pandemic_series(sample_covid_csv, PANDEMIC_COVID19)

    assert series.total_days == 3
    rec = series.get_record("BRA", 0)
    assert rec is not None
    assert rec.cases == 1
    assert rec.deaths == 0
    assert rec.recovered is None

    # recovered_series deve ser None quando recuperados não existem na fonte
    assert series.recovered_series("BRA") is None

    # Registros de todos os países no dia 2
    day2_map = series.day_records(2)
    assert "BRA" in day2_map
    assert "USA" in day2_map
    assert day2_map["BRA"].cases == 2
    assert day2_map["USA"].deaths == 1


def test_load_pandemic_series_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        load_pandemic_series("inexistente.csv")


def test_load_pandemic_series_missing_columns(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("iso3,date,cases\nBRA,2020-01-01,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        load_pandemic_series(bad_csv)


def test_load_pandemic_series_negative_values(tmp_path: Path) -> None:
    bad_csv = tmp_path / "negative.csv"
    bad_csv.write_text("iso3,date,cases,deaths\nBRA,2020-01-01,-5,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Valores negativos proibidos"):
        load_pandemic_series(bad_csv)


def test_load_pandemic_series_empty_file(tmp_path: Path) -> None:
    bad_csv = tmp_path / "empty.csv"
    bad_csv.write_text("iso3,date,cases,deaths,recovered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="não contém registros"):
        load_pandemic_series(bad_csv)
