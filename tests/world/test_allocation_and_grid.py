"""Testes unitários de alocação iterativa, geometria stdlib e grade espacial (M1)."""

from __future__ import annotations

import math

import pytest

from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.core.seeds import SeedBook
from epidemia.world.allocation import (
    allocate_vertices,
    effective_average_degree,
)
from epidemia.world.geometry import (
    build_country_geometry,
    point_in_polygon,
    polygon_area,
    sample_points_in_polygons,
)
from epidemia.world.spatial_grid import connection_radius, spatial_grid_edges


def test_alocacao_iterativa_respeita_soma_exata_piso_e_monotonicidade() -> None:
    """Critério de aceitação M1 (Modelagem 2.3): soma = N_total, n_i >= n_min e monotônica."""
    populations = {
        "IND": 1_428_000_000,
        "CHN": 1_410_000_000,
        "BRA": 215_000_000,
        "PRT": 10_300_000,
        "ISL": 380_000,
        "TUV": 11_000,
        "NRU": 12_500,
    }
    alloc = allocate_vertices(populations, total_vertices=500, min_vertices=12, alpha=0.5)

    assert sum(alloc.values()) == 500
    for count in alloc.values():
        assert count >= 12

    # Microestados ficam no piso 12
    assert alloc["TUV"] == 12
    assert alloc["NRU"] == 12
    # Monotonicidade: se pop(A) >= pop(B), então n_A >= n_B
    sorted_by_pop = sorted(populations.keys(), key=lambda k: populations[k])
    for i in range(len(sorted_by_pop) - 1):
        smaller, larger = sorted_by_pop[i], sorted_by_pop[i + 1]
        assert alloc[smaller] <= alloc[larger]


def test_alocacao_cenario_regional_fixa_nao_foco_no_piso() -> None:
    """No cenário regional (Ebola), países fora de focus_countries recebem exatamente n_min."""
    populations = {
        "GIN": 13_500_000,
        "LBR": 5_200_000,
        "SLE": 8_400_000,
        "BRA": 215_000_000,
        "USA": 333_000_000,
    }
    alloc = allocate_vertices(
        populations,
        total_vertices=200,
        min_vertices=12,
        focus_countries={"GIN", "LBR", "SLE"},
    )
    assert sum(alloc.values()) == 200
    assert alloc["BRA"] == 12
    assert alloc["USA"] == 12
    assert alloc["GIN"] > alloc["SLE"] > alloc["LBR"] > 12


def test_alocacao_orcamento_insuficiente_levanta_erro() -> None:
    """Se total_vertices < M * min_vertices, deve levantar ParameterOutOfRangeError."""
    with pytest.raises(ParameterOutOfRangeError):
        allocate_vertices({"A": 100, "B": 200, "C": 300}, total_vertices=30, min_vertices=12)


def test_geometria_ray_casting_area_e_sorteio_em_poligono_com_buraco() -> None:
    """Verifica área Shoelace, Ray Casting com buraco e sorteio determinístico."""
    # Quadrado externo [0, 10] x [0, 10] (área 100) com buraco [4, 6] x [4, 6] (área 4)
    exterior = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    hole = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]

    assert math.isclose(polygon_area(exterior, [hole]), 96.0, rel_tol=1e-12)
    assert point_in_polygon(2.0, 2.0, exterior, [hole]) is True
    assert point_in_polygon(5.0, 5.0, exterior, [hole]) is False
    assert point_in_polygon(15.0, 5.0, exterior, [hole]) is False

    geojson = {"type": "Polygon", "coordinates": [exterior, hole]}
    cg = build_country_geometry("TST", geojson)
    assert math.isclose(cg.area, 96.0, rel_tol=1e-12)

    rng = SeedBook(42).rng("network")
    pts = sample_points_in_polygons(cg.polygons, 40, rng)
    assert len(pts) == 40
    for lon, lat in pts:
        assert point_in_polygon(lon, lat, exterior, [hole])


def test_grade_espacial_equivale_exatamente_a_forca_bruta() -> None:
    """A grade espacial O(V+E) deve produzir exatamente o mesmo conjunto de arestas que O(V^2)."""
    rng = SeedBook(99).rng("network")
    positions = [(rng.uniform(0.0, 20.0), rng.uniform(0.0, 20.0)) for _ in range(80)]
    radius = connection_radius(area=400.0, num_vertices=80, target_avg_degree=8.0)

    grid_edges = spatial_grid_edges(positions, radius)

    # Comparação com força bruta O(V^2)
    brute_edges: list[tuple[int, int]] = []
    for u in range(len(positions)):
        xu, yu = positions[u]
        for v in range(u + 1, len(positions)):
            xv, yv = positions[v]
            if math.hypot(xu - xv, yu - yv) <= radius:
                brute_edges.append((u, v))

    assert grid_edges == brute_edges
    assert effective_average_degree(8.0, 12) == 8.0
    assert effective_average_degree(8.0, 5) == 4.0
