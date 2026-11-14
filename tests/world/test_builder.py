"""Testes unitários da construção completa do grafo global unificado, cenários e cache."""

from __future__ import annotations

import math

from epidemia.core.graph import normalized_route_weight
from epidemia.world import (
    SCENARIO_GLOBAL,
    SCENARIO_REGIONAL_EBOLA,
    CountryInput,
    RouteInput,
    WorldCache,
    build_world,
    detect_regional_focus_countries,
    route_edge_multiplicity,
)


def _square_geojson(lon0: float, lat0: float, size: float = 4.0) -> dict[str, object]:
    """Cria um polígono quadrado simples para testes sintéticos."""
    ring = [
        (lon0, lat0),
        (lon0 + size, lat0),
        (lon0 + size, lat0 + size),
        (lon0, lat0 + size),
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _sample_countries() -> list[CountryInput]:
    return [
        CountryInput("BRA", "Brazil", 215_000_000, _square_geojson(-50.0, -15.0)),
        CountryInput("GIN", "Guinea", 13_500_000, _square_geojson(-12.0, 10.0)),
        CountryInput("LBR", "Liberia", 5_200_000, _square_geojson(-10.0, 6.0)),
        CountryInput("SLE", "Sierra Leone", 8_400_000, _square_geojson(-12.0, 8.0)),
        CountryInput("TUV", "Tuvalu", 11_000, _square_geojson(179.0, -8.0)),
    ]


def test_multiplicidade_de_rotas_aereas_respeita_teto_e_arredondamento() -> None:
    """Verifica k_ij = min(k_max, ceil(routes / scale)) (Modelagem 2.5)."""
    assert route_edge_multiplicity(1, k_max=10, scale=5.0) == 1
    assert route_edge_multiplicity(5, k_max=10, scale=5.0) == 1
    assert route_edge_multiplicity(6, k_max=10, scale=5.0) == 2
    assert route_edge_multiplicity(999, k_max=10, scale=5.0) == 10


def test_build_world_determinismo_pesos_internacionais_e_paises_isolados() -> None:
    """Verifica construção completa, determinismo por semente e detecção de país sem rota (D16)."""
    countries = _sample_countries()
    routes = [
        # Rotas bidirecionais entre BRA e GIN somam 10 + 5 = 15 rotas
        RouteInput("BRA", "GIN", 10),
        RouteInput("GIN", "BRA", 5),
        # Rota entre GIN e LBR com 3 rotas
        RouteInput("GIN", "LBR", 3),
        # Rota doméstica deve ser ignorada
        RouteInput("BRA", "BRA", 50),
    ]

    w1 = build_world(countries, routes, seed=42, total_vertices=120, min_vertices=12)
    w2 = build_world(countries, routes, seed=42, total_vertices=120, min_vertices=12)

    assert w1.graph.num_vertices == 120
    assert w1.vertex_positions == w2.vertex_positions
    assert w1.graph.num_edges == w2.graph.num_edges

    # Tuvalu (TUV) e Serra Leoa (SLE) não possuem rotas na lista acima -> isolados na malha aérea
    assert w1.isolated_countries == ("SLE", "TUV")

    # Multiplicidade esperada:
    # Par (BRA, GIN): 15 rotas -> ceil(15 / 5.0) = 3 arestas com peso w = 1.0 (pois é o max_routes)
    # Par (GIN, LBR): 3 rotas  -> ceil(3 / 5.0)  = 1 aresta com peso ln(4)/ln(16)
    assert w1.international_edge_count == 4

    expected_w_gin_lbr = normalized_route_weight(3, 15)
    found_weights: list[float] = []
    for u in w1.vertices_of_country("GIN"):
        for v in w1.graph.neighbors(u):
            if w1.country_of_vertex(v) == "LBR":
                found_weights.append(w1.graph.edge_weight(u, v))

    assert len(found_weights) == 1
    assert math.isclose(found_weights[0], expected_w_gin_lbr, rel_tol=1e-12)


def test_cenario_regional_ebola_por_series_diarias_e_cache_de_mundo() -> None:
    """Verifica detecção automática de países com >= 10 casos em 60 dias e WorldCache."""
    countries = _sample_countries()
    daily_cases = {
        "GIN": [2, 5, 12, 30],
        "LBR": [0, 4, 10, 25],
        "SLE": [1, 3, 15, 40],
        "BRA": [0, 0, 0, 0],
        "TUV": [0, 0, 0, 0],
    }

    focus = detect_regional_focus_countries(daily_cases, window_days=60, min_cases=10)
    assert focus == frozenset({"GIN", "LBR", "SLE"})

    cache = WorldCache()
    world_reg = cache.get_or_build(
        countries,
        seed=7,
        scenario=SCENARIO_REGIONAL_EBOLA,
        daily_cases_by_country=daily_cases,
        total_vertices=120,
        min_vertices=12,
    )
    assert len(cache) == 1
    # Países fora do foco (BRA e TUV) ficam cravados em 12 vértices
    assert len(world_reg.vertices_of_country("BRA")) == 12
    assert len(world_reg.vertices_of_country("TUV")) == 12
    # Países do foco dividem o restante (120 - 24 = 96 vértices)
    focus_total = sum(len(world_reg.vertices_of_country(c)) for c in ("GIN", "LBR", "SLE"))
    assert focus_total == 96

    # Segunda chamada com mesma semente e cenário reutiliza a instância do cache
    world_reg_cached = cache.get_or_build(
        countries,
        seed=7,
        scenario=SCENARIO_REGIONAL_EBOLA,
        daily_cases_by_country=daily_cases,
        total_vertices=120,
        min_vertices=12,
    )
    assert world_reg_cached is world_reg

    # Cenário global gera nova entrada no cache
    world_glob = cache.get_or_build(
        countries,
        seed=7,
        scenario=SCENARIO_GLOBAL,
        total_vertices=120,
        min_vertices=12,
    )
    assert len(cache) == 2
    assert len(world_glob.vertices_of_country("BRA")) > 12
