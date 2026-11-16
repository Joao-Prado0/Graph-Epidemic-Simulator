"""Pacote de leitura de dados processados e séries temporais (M4).

Lê exclusivamente arquivos processados em ``data/processed/`` usando a
biblioteca padrão do Python, em conformidade com as regras de camadas do projeto.
"""

from __future__ import annotations

from epidemia.datasets.loaders import (
    CountryRecord,
    EdgeRecord,
    load_countries_csv,
    load_countries_geojson,
    load_edges_csv,
    load_world_inputs,
)
from epidemia.datasets.series import (
    PANDEMIC_COVID19,
    PANDEMIC_EBOLA,
    PANDEMIC_H1N1,
    PANDEMIC_SARS,
    SUPPORTED_PANDEMICS,
    DailyRecord,
    PandemicSeries,
    load_pandemic_series,
)

__all__ = [
    "PANDEMIC_COVID19",
    "PANDEMIC_EBOLA",
    "PANDEMIC_H1N1",
    "PANDEMIC_SARS",
    "SUPPORTED_PANDEMICS",
    "CountryRecord",
    "DailyRecord",
    "EdgeRecord",
    "PandemicSeries",
    "load_countries_csv",
    "load_countries_geojson",
    "load_edges_csv",
    "load_pandemic_series",
    "load_world_inputs",
]
