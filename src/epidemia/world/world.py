"""Estruturas de dados do mundo unificado: países, rotas e contêiner ``World``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from epidemia.core.errors import InvalidDatasetError, VertexNotFoundError
from epidemia.core.graph.graph import Graph
from epidemia.world.geometry import CountryGeometry, Point2D


@dataclass(frozen=True, slots=True)
class CountryInput:
    """Dados de entrada de um país para construção da rede global."""

    iso3: str
    name: str
    population: int
    geometry: Mapping[str, Any]
    continent: str = ""


@dataclass(frozen=True, slots=True)
class RouteInput:
    """Par de países e volume de rotas aéreas do OpenFlights (``edges.csv``)."""

    iso3_a: str
    iso3_b: str
    routes: int


@dataclass(frozen=True, slots=True)
class World:
    """Contêiner imutável do grafo global unificado e metadados geográficos (RF10, RF13).

    Compartilhado entre o fluxo de simulação SEIRD e o fluxo de pandemias reais.
    """

    graph: Graph
    scenario: str
    seed: int
    country_codes: tuple[str, ...]
    country_index: dict[str, int]
    country_names: dict[str, str]
    country_populations: dict[str, int]
    country_geometries: dict[str, CountryGeometry]
    country_vertices: dict[str, list[int]]
    vertex_country: list[int]
    vertex_positions: list[Point2D]
    isolated_countries: tuple[str, ...]
    internal_edge_count: int
    international_edge_count: int

    def vertices_of_country(self, iso3: str) -> list[int]:
        """Retorna a lista de IDs de vértices pertencentes ao país ``iso3``."""
        if iso3 not in self.country_vertices:
            raise InvalidDatasetError(f"País {iso3!r} não encontrado no objeto World.")
        return list(self.country_vertices[iso3])

    def country_of_vertex(self, u: int) -> str:
        """Retorna o código ISO3 do país ao qual o vértice ``u`` pertence."""
        if not (0 <= u < len(self.vertex_country)):
            raise VertexNotFoundError(f"Vértice {u} fora do intervalo do objeto World.")
        c_idx = self.vertex_country[u]
        return self.country_codes[c_idx]
