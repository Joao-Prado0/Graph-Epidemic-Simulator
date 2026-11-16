"""Carregadores de dados estáticos processados (M4 — datasets/loaders.py).

Provê a leitura dos arquivos já processados em ``data/processed/`` usando
exclusivamente a biblioteca padrão do Python (csv, json, pathlib):
- ``countries.csv``: tabela mestra de países e atributos estáticos;
- ``edges.csv``: pares de países e contagem bruta de rotas aéreas;
- ``countries.geojson``: geometrias dos polígonos dos países.

Em conformidade estrita com a regra de isolamento da camada ``datasets``
(tests/architecture/test_camadas.py), este módulo não importa pacotes externos
(pandas, shapely, networkx, Qt) nem camadas superiores ou de domínio (core, world).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "CountryRecord",
    "EdgeRecord",
    "load_countries_csv",
    "load_countries_geojson",
    "load_edges_csv",
    "load_world_inputs",
]


def _parse_optional_float(val: str | None) -> float | None:
    if val is None:
        return None
    val_clean = val.strip()
    if not val_clean:
        return None
    try:
        return float(val_clean)
    except ValueError:
        return None


def _parse_optional_int(val: str | None) -> int | None:
    if val is None:
        return None
    val_clean = val.strip()
    if not val_clean:
        return None
    try:
        return int(float(val_clean))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class CountryRecord:
    """Registro de um país na tabela mestra (countries.csv) com geometria opcional."""

    iso3: str
    name: str
    continent: str
    population: int
    population_density: float | None = None
    median_age: float | None = None
    gdp_per_capita: float | None = None
    hospital_beds_per_thousand: float | None = None
    life_expectancy: float | None = None
    human_development_index: float | None = None
    lat: float | None = None
    lon: float | None = None
    geometry: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EdgeRecord:
    """Registro de rota aérea bruta entre dois países (edges.csv)."""

    iso3_a: str
    iso3_b: str
    routes: int


def load_countries_csv(path: Path | str) -> list[CountryRecord]:
    """Carrega a tabela mestra de países a partir de um arquivo CSV.

    Parameters
    ----------
    path : Path | str
        Caminho para o arquivo ``countries.csv``.

    Returns
    -------
    list[CountryRecord]
        Lista ordenada de países carregados.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    ValueError
        Se colunas obrigatórias estiverem ausentes ou arquivo for inválido.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Arquivo countries.csv não encontrado: {file_path}")

    records: list[CountryRecord] = []
    with file_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Arquivo CSV vazio ou sem cabeçalho: {file_path}")

        fieldnames = set(reader.fieldnames)
        required = {"iso3", "name", "continent", "population"}
        missing = required - fieldnames
        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes em {file_path}: {sorted(missing)}")

        for row_idx, row in enumerate(reader, start=2):
            iso3 = (row.get("iso3") or "").strip().upper()
            name = (row.get("name") or "").strip()
            continent = (row.get("continent") or "").strip()
            pop_str = (row.get("population") or "").strip()

            if not iso3:
                raise ValueError(f"Linha {row_idx} em {file_path} sem código iso3.")
            if not pop_str:
                raise ValueError(f"Linha {row_idx} ({iso3}) em {file_path} sem população.")

            try:
                population = int(float(pop_str))
            except ValueError as err:
                raise ValueError(
                    f"População inválida na linha {row_idx} ({iso3}): {pop_str!r}"
                ) from err

            records.append(
                CountryRecord(
                    iso3=iso3,
                    name=name,
                    continent=continent,
                    population=population,
                    population_density=_parse_optional_float(row.get("population_density")),
                    median_age=_parse_optional_float(row.get("median_age")),
                    gdp_per_capita=_parse_optional_float(row.get("gdp_per_capita")),
                    hospital_beds_per_thousand=_parse_optional_float(
                        row.get("hospital_beds_per_thousand")
                    ),
                    life_expectancy=_parse_optional_float(row.get("life_expectancy")),
                    human_development_index=_parse_optional_float(
                        row.get("human_development_index")
                    ),
                    lat=_parse_optional_float(row.get("lat")),
                    lon=_parse_optional_float(row.get("lon")),
                    geometry=None,
                )
            )

    return records


def load_edges_csv(path: Path | str) -> list[EdgeRecord]:
    """Carrega o conjunto de arestas de rotas aéreas a partir de edges.csv.

    Parameters
    ----------
    path : Path | str
        Caminho para o arquivo ``edges.csv``.

    Returns
    -------
    list[EdgeRecord]
        Lista de conexões entre pares de países com volume bruto de rotas.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Arquivo edges.csv não encontrado: {file_path}")

    edges: list[EdgeRecord] = []
    with file_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Arquivo CSV vazio ou sem cabeçalho: {file_path}")

        fieldnames = set(reader.fieldnames)
        required = {"iso3_a", "iso3_b", "routes"}
        missing = required - fieldnames
        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes em {file_path}: {sorted(missing)}")

        for row_idx, row in enumerate(reader, start=2):
            iso3_a = (row.get("iso3_a") or "").strip().upper()
            iso3_b = (row.get("iso3_b") or "").strip().upper()
            routes_str = (row.get("routes") or "").strip()

            if not iso3_a or not iso3_b:
                raise ValueError(f"Linha {row_idx} em {file_path} com código de país vazio.")
            if iso3_a == iso3_b:
                raise ValueError(
                    f"Linha {row_idx} em {file_path} contém auto-laço: {iso3_a} == {iso3_b}."
                )

            try:
                routes = int(float(routes_str))
            except ValueError as err:
                raise ValueError(
                    f"Contagem de rotas inválida na linha {row_idx}: {routes_str!r}"
                ) from err

            if routes <= 0:
                raise ValueError(
                    f"Contagem de rotas não positiva na linha {row_idx}: {routes}."
                )

            edges.append(EdgeRecord(iso3_a=iso3_a, iso3_b=iso3_b, routes=routes))

    return edges


def load_countries_geojson(path: Path | str) -> dict[str, dict[str, Any]]:
    """Carrega as geometrias dos países a partir de countries.geojson.

    Parameters
    ----------
    path : Path | str
        Caminho para o arquivo ``countries.geojson``.

    Returns
    -------
    dict[str, dict[str, Any]]
        Mapeamento ``iso3 -> geojson_geometry_or_feature``.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Arquivo GeoJSON não encontrado: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Formato GeoJSON inválido (raiz deve ser objeto JSON): {file_path}")

    features = data.get("features", [])
    if not isinstance(features, list):
        raise ValueError(f"Formato GeoJSON inválido: 'features' deve ser uma lista.")

    result: dict[str, dict[str, Any]] = {}
    for feat in features:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") or {}
        # Busca chave de código do país (iso3 com fallback em chaves padrão)
        iso3 = (
            props.get("iso3")
            or props.get("ISO3")
            or props.get("ISO_A3_EH")
            or props.get("ADM0_A3")
            or props.get("ISO_A3")
        )
        if iso3 and isinstance(iso3, str):
            code = iso3.strip().upper()
            # Guarda a geometria (ou a feição inteira se a geometria não estiver isolada)
            geom = feat.get("geometry") or feat
            result[code] = geom

    return result


def load_world_inputs(
    processed_dir: Path | str,
) -> tuple[list[CountryRecord], list[EdgeRecord]]:
    """Carrega e vincula countries.csv, edges.csv e countries.geojson.

    Retorna instâncias de ``CountryRecord`` (com ``geometry`` preenchida) e
    ``EdgeRecord`` prontas para serem repassadas ao construtor ``build_world()``
    da camada ``world/``, garantindo interoperabilidade entre M4 e M1.

    Parameters
    ----------
    processed_dir : Path | str
        Diretório contendo ``countries.csv``, ``edges.csv`` e ``countries.geojson``.

    Returns
    -------
    tuple[list[CountryRecord], list[EdgeRecord]]
        Tupla com a lista de países (com geometria vinculada) e a lista de arestas.
    """
    base_dir = Path(processed_dir)
    countries_path = base_dir / "countries.csv"
    edges_path = base_dir / "edges.csv"
    geojson_path = base_dir / "countries.geojson"

    raw_countries = load_countries_csv(countries_path)
    edges = load_edges_csv(edges_path)
    geometries = load_countries_geojson(geojson_path)

    linked_countries: list[CountryRecord] = []
    for c in raw_countries:
        geom = geometries.get(c.iso3)
        linked_countries.append(
            CountryRecord(
                iso3=c.iso3,
                name=c.name,
                continent=c.continent,
                population=c.population,
                population_density=c.population_density,
                median_age=c.median_age,
                gdp_per_capita=c.gdp_per_capita,
                hospital_beds_per_thousand=c.hospital_beds_per_thousand,
                life_expectancy=c.life_expectancy,
                human_development_index=c.human_development_index,
                lat=c.lat,
                lon=c.lon,
                geometry=geom,
            )
        )

    return linked_countries, edges
