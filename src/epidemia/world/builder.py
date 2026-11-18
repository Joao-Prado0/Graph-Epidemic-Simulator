"""Construtor do grafo global unificado e cache por (semente, cenário) (Modelagem 2.4–2.7).

Combina a alocação iterativa de vértices, o sorteio geométrico nos polígonos
dos países, a grade espacial para arestas internas e a adição de arestas
internacionais ponderadas pelas rotas aéreas do OpenFlights.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Final

from epidemia.core.errors import InvalidDatasetError, ParameterOutOfRangeError
from epidemia.core.graph.graph import Graph
from epidemia.core.graph.weights import DEFAULT_BETA, normalized_route_weight
from epidemia.core.seeds import SUBSYSTEM_NETWORK, SeedBook
from epidemia.world.allocation import (
    DEFAULT_ALPHA,
    DEFAULT_MIN_VERTICES,
    DEFAULT_TOTAL_VERTICES,
    allocate_vertices,
)
from epidemia.world.geometry import (
    CountryGeometry,
    Point2D,
    build_country_geometry,
    sample_points_in_polygons,
)
from epidemia.world.scenarios import SCENARIO_GLOBAL, ScenarioSpec, resolve_scenario
from epidemia.world.spatial_grid import (
    DEFAULT_TARGET_AVG_DEGREE,
    connection_radius,
    spatial_grid_edges,
)
from epidemia.world.world import CountryInput, RouteInput, World

DEFAULT_K_MAX: Final[int] = 10
DEFAULT_ROUTE_SCALE: Final[float] = 5.0
INTERNAL_EDGE_WEIGHT: Final[float] = 1.0


def route_edge_multiplicity(
    routes: int,
    *,
    k_max: int = DEFAULT_K_MAX,
    scale: float = DEFAULT_ROUTE_SCALE,
) -> int:
    """Calcula ``k_ij = min(k_max, ceil(routes_ij / scale))`` (Modelagem 2.5)."""
    if routes <= 0:
        raise ParameterOutOfRangeError(f"routes deve ser > 0: {routes}")
    if k_max < 1:
        raise ParameterOutOfRangeError(f"k_max deve ser >= 1: {k_max}")
    if scale <= 0.0 or not math.isfinite(scale):
        raise ParameterOutOfRangeError(f"scale deve ser finito e positivo: {scale}")
    return min(k_max, int(math.ceil(routes / scale)))


def _populate_internal_subgraphs(
    graph: Graph,
    country_codes: Sequence[str],
    country_geometries: Mapping[str, CountryGeometry],
    allocated: Mapping[str, int],
    *,
    target_avg_degree: float,
    rng: random.Random,
) -> tuple[dict[str, list[int]], list[int], list[Point2D], int]:
    """Cria os vértices e as conexões geométricas internas de cada país."""
    country_vertices: dict[str, list[int]] = {}
    vertex_country: list[int] = []
    vertex_positions: list[Point2D] = []
    internal_edge_count = 0

    for c_idx, iso3 in enumerate(country_codes):
        n_i = allocated[iso3]
        cg = country_geometries[iso3]
        local_positions = sample_points_in_polygons(cg.polygons, n_i, rng)

        global_ids: list[int] = []
        for pos in local_positions:
            u = graph.add_vertex(country_id=c_idx, position=pos)
            global_ids.append(u)
            vertex_country.append(c_idx)
            vertex_positions.append(pos)

        country_vertices[iso3] = global_ids

        radius = connection_radius(cg.area, n_i, target_avg_degree=target_avg_degree)
        local_edges = spatial_grid_edges(local_positions, radius)
        for lu, lv in local_edges:
            graph.add_edge(global_ids[lu], global_ids[lv], weight=INTERNAL_EDGE_WEIGHT)
            internal_edge_count += 1

    return country_vertices, vertex_country, vertex_positions, internal_edge_count


def _connect_international_routes(
    graph: Graph,
    routes: Sequence[RouteInput],
    country_codes: Sequence[str],
    country_index: Mapping[str, int],
    country_vertices: Mapping[str, Sequence[int]],
    *,
    k_max: int,
    route_scale: float,
    rng: random.Random,
) -> tuple[int, tuple[str, ...]]:
    """Consolida rotas aéreas em pares não ordenados, cria arestas e lista países isolados."""
    pair_routes: dict[tuple[str, str], int] = defaultdict(int)
    countries_with_routes: set[str] = set()

    for route in routes:
        if route.routes <= 0:
            continue
        a, b = route.iso3_a, route.iso3_b
        if a == b or a not in country_index or b not in country_index:
            continue
        pair = (a, b) if a < b else (b, a)
        pair_routes[pair] += route.routes
        countries_with_routes.add(a)
        countries_with_routes.add(b)

    international_edge_count = 0
    if pair_routes:
        max_routes = max(pair_routes.values())
        for (iso_a, iso_b), count_routes in sorted(pair_routes.items()):
            k_ij = route_edge_multiplicity(count_routes, k_max=k_max, scale=route_scale)
            w_ij = normalized_route_weight(count_routes, max_routes)
            verts_a = country_vertices[iso_a]
            verts_b = country_vertices[iso_b]
            target_k = min(k_ij, len(verts_a) * len(verts_b))

            added_for_pair = 0
            attempts = 0
            max_attempts = target_k * 20
            while added_for_pair < target_k and attempts < max_attempts:
                attempts += 1
                u = rng.choice(verts_a)
                v = rng.choice(verts_b)
                if not graph.has_edge(u, v):
                    graph.add_edge(u, v, weight=w_ij)
                    added_for_pair += 1
                    international_edge_count += 1

    isolated_countries = tuple(iso3 for iso3 in country_codes if iso3 not in countries_with_routes)
    return international_edge_count, isolated_countries


def build_world(
    countries: Sequence[CountryInput],
    routes: Sequence[RouteInput] = (),
    *,
    seed: int = 42,
    scenario: str | ScenarioSpec = SCENARIO_GLOBAL,
    daily_cases_by_country: Mapping[str, Sequence[int]] | None = None,
    total_vertices: int = DEFAULT_TOTAL_VERTICES,
    min_vertices: int = DEFAULT_MIN_VERTICES,
    alpha: float = DEFAULT_ALPHA,
    target_avg_degree: float = DEFAULT_TARGET_AVG_DEGREE,
    k_max: int = DEFAULT_K_MAX,
    route_scale: float = DEFAULT_ROUTE_SCALE,
    beta: float = DEFAULT_BETA,
) -> World:
    """Constrói o objeto ``World`` completo de forma 100% determinística."""
    if not countries:
        raise InvalidDatasetError("A lista de países não pode ser vazia.")

    scenario_spec = resolve_scenario(scenario, daily_cases_by_country=daily_cases_by_country)
    rng = SeedBook(seed).rng(SUBSYSTEM_NETWORK)

    sorted_countries = sorted(countries, key=lambda c: c.iso3)
    country_codes = tuple(c.iso3 for c in sorted_countries)
    if len(set(country_codes)) != len(country_codes):
        raise InvalidDatasetError("Códigos ISO3 duplicados na lista de países.")

    country_index = {iso3: idx for idx, iso3 in enumerate(country_codes)}
    country_names = {c.iso3: c.name for c in sorted_countries}
    country_populations = {c.iso3: c.population for c in sorted_countries}
    country_geometries: dict[str, CountryGeometry] = {
        c.iso3: build_country_geometry(c.iso3, c.geometry) for c in sorted_countries
    }

    allocated = allocate_vertices(
        country_populations,
        total_vertices=total_vertices,
        min_vertices=min_vertices,
        alpha=alpha,
        focus_countries=scenario_spec.focus_countries,
    )

    graph = Graph(0, beta=beta)
    country_vertices, vertex_country, vertex_positions, internal_edge_count = (
        _populate_internal_subgraphs(
            graph,
            country_codes,
            country_geometries,
            allocated,
            target_avg_degree=target_avg_degree,
            rng=rng,
        )
    )
    international_edge_count, isolated_countries = _connect_international_routes(
        graph,
        routes,
        country_codes,
        country_index,
        country_vertices,
        k_max=k_max,
        route_scale=route_scale,
        rng=rng,
    )

    return World(
        graph=graph,
        scenario=scenario_spec.name,
        seed=seed,
        country_codes=country_codes,
        country_index=country_index,
        country_names=country_names,
        country_populations=country_populations,
        country_geometries=country_geometries,
        country_vertices=country_vertices,
        vertex_country=vertex_country,
        vertex_positions=vertex_positions,
        isolated_countries=isolated_countries,
        internal_edge_count=internal_edge_count,
        international_edge_count=international_edge_count,
    )


class WorldCache:
    """Cache em memória de instâncias ``World`` indexado por ``(seed, scenario, ...)``.

    Como a construção do grafo global unificado envolve amostragem geométrica e
    grade espacial para milhares de vértices, o cache evita reconstruir a mesma
    topologia ao reiniciar ou alternar fluxos com a mesma semente e cenário
    (Arquitetura v0.6, seção 6 e 9.2 item 3).
    """

    def __init__(self) -> None:
        self._store: dict[tuple[object, ...], World] = {}

    def get_or_build(
        self,
        countries: Sequence[CountryInput],
        routes: Sequence[RouteInput] = (),
        *,
        seed: int = 42,
        scenario: str | ScenarioSpec = SCENARIO_GLOBAL,
        daily_cases_by_country: Mapping[str, Sequence[int]] | None = None,
        total_vertices: int = DEFAULT_TOTAL_VERTICES,
        min_vertices: int = DEFAULT_MIN_VERTICES,
        alpha: float = DEFAULT_ALPHA,
        target_avg_degree: float = DEFAULT_TARGET_AVG_DEGREE,
        k_max: int = DEFAULT_K_MAX,
        route_scale: float = DEFAULT_ROUTE_SCALE,
        beta: float = DEFAULT_BETA,
    ) -> World:
        """Retorna o ``World`` do cache ou constrói e armazena se ainda não existir."""
        scenario_spec = resolve_scenario(scenario, daily_cases_by_country=daily_cases_by_country)
        key: tuple[object, ...] = (
            seed,
            scenario_spec.name,
            scenario_spec.focus_countries,
            len(countries),
            len(routes),
            total_vertices,
            min_vertices,
            alpha,
            target_avg_degree,
            k_max,
            route_scale,
        )
        cached = self._store.get(key)
        if cached is not None:
            cached.graph.reset_masks()
            cached.graph.update_transmission_costs(beta)
            return cached

        world = build_world(
            countries,
            routes,
            seed=seed,
            scenario=scenario_spec,
            total_vertices=total_vertices,
            min_vertices=min_vertices,
            alpha=alpha,
            target_avg_degree=target_avg_degree,
            k_max=k_max,
            route_scale=route_scale,
            beta=beta,
        )
        self._store[key] = world
        return world

    def clear(self) -> None:
        """Limpa todas as entradas do cache."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


def _fallback_square_geojson(lon0: float, lat0: float, size: float = 6.0) -> dict[str, object]:
    """Gera geometria GeoJSON retangular mínima para fallback seguro sem arquivos externos."""
    ring = [
        (lon0, lat0),
        (lon0 + size, lat0),
        (lon0 + size, lat0 + size),
        (lon0, lat0 + size),
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def create_fallback_countries() -> list[CountryInput]:
    """Retorna países mínimos de fallback quando ``data/processed/`` está ausente."""
    return [
        CountryInput("BRA", "Brasil", 215_000_000, _fallback_square_geojson(-50.0, -15.0, 8.0)),
        CountryInput("GIN", "Guiné", 13_500_000, _fallback_square_geojson(-12.0, 9.0, 4.0)),
        CountryInput("LBR", "Libéria", 5_200_000, _fallback_square_geojson(-10.0, 5.0, 4.0)),
        CountryInput("SLE", "Serra Leoa", 8_400_000, _fallback_square_geojson(-13.0, 7.0, 4.0)),
        CountryInput("TUV", "Tuvalu", 11_000, _fallback_square_geojson(178.0, -8.0, 3.0)),
    ]


def create_fallback_routes() -> list[RouteInput]:
    """Retorna rotas aéreas mínimas de fallback."""
    return [
        RouteInput("BRA", "GIN", 15),
        RouteInput("GIN", "LBR", 6),
        RouteInput("LBR", "SLE", 10),
        RouteInput("SLE", "BRA", 4),
    ]


def create_fallback_world(
    total_vertices: int = 100,
    seed: int = 42,
    scenario: str | ScenarioSpec = SCENARIO_GLOBAL,
) -> World:
    """Constrói um objeto ``World`` mínimo sem depender de arquivos externos ou ``tests/``."""
    return build_world(
        countries=create_fallback_countries(),
        routes=create_fallback_routes(),
        seed=seed,
        scenario=scenario,
        total_vertices=total_vertices,
        min_vertices=DEFAULT_MIN_VERTICES,
    )
