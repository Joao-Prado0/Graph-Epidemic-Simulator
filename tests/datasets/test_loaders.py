"""Testes unitários para os carregadores de dados estáticos (M4 — datasets/loaders.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from epidemia.datasets.loaders import (
    CountryRecord,
    EdgeRecord,
    load_countries_csv,
    load_countries_geojson,
    load_edges_csv,
    load_world_inputs,
)


@pytest.fixture
def sample_countries_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "countries.csv"
    csv_content = (
        "iso3,name,continent,population,population_density,median_age,gdp_per_capita,"
        "hospital_beds_per_thousand,life_expectancy,human_development_index,lat,lon\n"
        "BRA,Brasil,South America,215000000,25.4,33.5,14500.0,2.1,75.3,0.765,-15.78,-47.93\n"
        "GIN,Guiné,Africa,13500000,55.0,,2100.0,,,61.6,,9.94,-9.69\n"
        "KOS,Kosovo,Europe,1800000,,,,,,,,42.66,21.16\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")
    return csv_file


@pytest.fixture
def sample_edges_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "edges.csv"
    csv_content = (
        "iso3_a,iso3_b,routes\n"
        "BRA,GIN,15\n"
        "GIN,KOS,3\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")
    return csv_file


@pytest.fixture
def sample_geojson(tmp_path: Path) -> Path:
    geo_file = tmp_path / "countries.geojson"
    geo_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"iso3": "BRA", "name": "Brasil"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-50.0, -15.0], [-40.0, -15.0], [-40.0, -5.0], [-50.0, -15.0]],
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"ISO_A3_EH": "GIN", "name": "Guiné"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-15.0, 5.0], [-10.0, 5.0], [-10.0, 10.0], [-15.0, 5.0]]],
                },
            },
        ],
    }
    geo_file.write_text(json.dumps(geo_data), encoding="utf-8")
    return geo_file


def test_load_countries_csv_success(sample_countries_csv: Path) -> None:
    records = load_countries_csv(sample_countries_csv)
    assert len(records) == 3

    bra = records[0]
    assert isinstance(bra, CountryRecord)
    assert bra.iso3 == "BRA"
    assert bra.name == "Brasil"
    assert bra.continent == "South America"
    assert bra.population == 215_000_000
    assert bra.population_density == 25.4
    assert bra.median_age == 33.5
    assert bra.gdp_per_capita == 14500.0
    assert bra.lat == -15.78
    assert bra.lon == -47.93

    gin = records[1]
    assert gin.iso3 == "GIN"
    assert gin.median_age is None
    assert gin.hospital_beds_per_thousand is None

    kos = records[2]
    assert kos.iso3 == "KOS"
    assert kos.population == 1_800_000
    assert kos.population_density is None


def test_load_countries_csv_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        load_countries_csv("caminho_inexistente_12345.csv")


def test_load_countries_csv_missing_columns(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("iso3,name\nBRA,Brasil\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        load_countries_csv(bad_csv)


def test_load_countries_csv_invalid_population(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad_pop.csv"
    bad_csv.write_text("iso3,name,continent,population\nBRA,Brasil,SA,invalido\n", encoding="utf-8")
    with pytest.raises(ValueError, match="População inválida"):
        load_countries_csv(bad_csv)


def test_load_edges_csv_success(sample_edges_csv: Path) -> None:
    edges = load_edges_csv(sample_edges_csv)
    assert len(edges) == 2
    assert edges[0] == EdgeRecord(iso3_a="BRA", iso3_b="GIN", routes=15)
    assert edges[1] == EdgeRecord(iso3_a="GIN", iso3_b="KOS", routes=3)


def test_load_edges_csv_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        load_edges_csv("edges_inexistente.csv")


def test_load_edges_csv_self_loop(tmp_path: Path) -> None:
    bad_edges = tmp_path / "self_loop.csv"
    bad_edges.write_text("iso3_a,iso3_b,routes\nBRA,BRA,10\n", encoding="utf-8")
    with pytest.raises(ValueError, match="auto-laço"):
        load_edges_csv(bad_edges)


def test_load_edges_csv_invalid_routes(tmp_path: Path) -> None:
    bad_edges = tmp_path / "zero_routes.csv"
    bad_edges.write_text("iso3_a,iso3_b,routes\nBRA,ARG,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="não positiva"):
        load_edges_csv(bad_edges)


def test_load_countries_geojson_success(sample_geojson: Path) -> None:
    geos = load_countries_geojson(sample_geojson)
    assert "BRA" in geos
    assert "GIN" in geos
    assert geos["BRA"]["type"] == "Polygon"
    assert geos["GIN"]["type"] == "Polygon"


def test_load_countries_geojson_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        load_countries_geojson("geo_inexistente.geojson")


def test_load_world_inputs(
    tmp_path: Path,
    sample_countries_csv: Path,
    sample_edges_csv: Path,
    sample_geojson: Path,
) -> None:
    # Renomeia/move para a mesma pasta
    base_dir = tmp_path / "processed"
    base_dir.mkdir()
    sample_countries_csv.rename(base_dir / "countries.csv")
    sample_edges_csv.rename(base_dir / "edges.csv")
    sample_geojson.rename(base_dir / "countries.geojson")

    countries, edges = load_world_inputs(base_dir)
    assert len(countries) == 3
    assert len(edges) == 2

    bra = next(c for c in countries if c.iso3 == "BRA")
    assert bra.geometry is not None
    assert bra.geometry["type"] == "Polygon"

    kos = next(c for c in countries if c.iso3 == "KOS")
    assert kos.geometry is None  # Não estava no geojson amostral
