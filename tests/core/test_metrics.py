"""Testes unitários das métricas de grau, agrupamento e intermediação (M2 — RF18)."""

from __future__ import annotations

import pytest

from epidemia.core.analysis import (
    average_clustering_coefficient,
    average_degree,
    betweenness_centrality,
    clustering_coefficients,
    degrees,
    local_clustering_coefficient,
    vertex_degree,
)
from tests.conftest import SimpleTestGraph


def test_degrees_empty_graph(empty_graph: SimpleTestGraph) -> None:
    assert degrees(empty_graph) == {0: 0, 1: 0, 2: 0, 3: 0}
    assert average_degree(empty_graph) == 0.0


def test_degrees_zero_vertex_graph() -> None:
    g = SimpleTestGraph(0)
    assert degrees(g) == {}
    assert average_degree(g) == 0.0


def test_degrees_path_graph(path_graph: SimpleTestGraph) -> None:
    assert degrees(path_graph) == {0: 1, 1: 2, 2: 2, 3: 1}
    assert average_degree(path_graph) == pytest.approx(1.5)
    assert vertex_degree(path_graph, 0) == 1
    assert vertex_degree(path_graph, 1) == 2


def test_degrees_cycle_graph(cycle_graph: SimpleTestGraph) -> None:
    assert degrees(cycle_graph) == {0: 2, 1: 2, 2: 2, 3: 2}
    assert average_degree(cycle_graph) == pytest.approx(2.0)


def test_degrees_complete_graph(complete_graph: SimpleTestGraph) -> None:
    assert degrees(complete_graph) == {0: 3, 1: 3, 2: 3, 3: 3}
    assert average_degree(complete_graph) == pytest.approx(3.0)


def test_degrees_star_graph(star_graph: SimpleTestGraph) -> None:
    assert degrees(star_graph) == {0: 4, 1: 1, 2: 1, 3: 1, 4: 1}
    assert average_degree(star_graph) == pytest.approx(8 / 5)


def test_degrees_respect_active_edge_mask(bridge_triangles_graph: SimpleTestGraph) -> None:
    assert degrees(bridge_triangles_graph) == {0: 2, 1: 2, 2: 3, 3: 3, 4: 2, 5: 2}
    # Desativando a ponte (2, 3), os vértices 2 e 3 passam a ter grau 2
    bridge_triangles_graph.set_edge_active(2, 3, False)
    assert degrees(bridge_triangles_graph) == {0: 2, 1: 2, 2: 2, 3: 2, 4: 2, 5: 2}
    assert vertex_degree(bridge_triangles_graph, 2) == 2


def test_vertex_degree_out_of_bounds_raises(path_graph: SimpleTestGraph) -> None:
    with pytest.raises(ValueError):
        vertex_degree(path_graph, -1)
    with pytest.raises(ValueError):
        vertex_degree(path_graph, 4)


def test_clustering_zero_and_triangle_free_graphs(
    empty_graph: SimpleTestGraph,
    path_graph: SimpleTestGraph,
    cycle_graph: SimpleTestGraph,
    star_graph: SimpleTestGraph,
) -> None:
    assert clustering_coefficients(SimpleTestGraph(0)) == {}
    assert average_clustering_coefficient(SimpleTestGraph(0)) == 0.0

    for g in (empty_graph, path_graph, cycle_graph, star_graph):
        coeffs = clustering_coefficients(g)
        assert all(c == 0.0 for c in coeffs.values())
        assert average_clustering_coefficient(g) == 0.0


def test_clustering_complete_graph(complete_graph: SimpleTestGraph) -> None:
    coeffs = clustering_coefficients(complete_graph)
    for u in range(4):
        assert coeffs[u] == pytest.approx(1.0)
        assert local_clustering_coefficient(complete_graph, u) == pytest.approx(1.0)
    assert average_clustering_coefficient(complete_graph) == pytest.approx(1.0)


def test_clustering_bridge_triangles_graph(
    bridge_triangles_graph: SimpleTestGraph,
) -> None:
    coeffs = clustering_coefficients(bridge_triangles_graph)
    # Pontas dos triângulos têm grau 2 e vizinhos conectados -> C = 1.0
    for u in (0, 1, 4, 5):
        assert coeffs[u] == pytest.approx(1.0)
    # Vértices da ponte (2 e 3) têm grau 3 e 1 par conectado entre 3 possíveis -> C = 1/3
    for u in (2, 3):
        assert coeffs[u] == pytest.approx(1 / 3)
        assert local_clustering_coefficient(bridge_triangles_graph, u) == pytest.approx(1 / 3)

    expected_avg = (1.0 * 4 + (1 / 3) * 2) / 6
    assert average_clustering_coefficient(bridge_triangles_graph) == pytest.approx(expected_avg)

    # Se a ponte (2, 3) for desativada (isolamento), os dois triângulos ficam puros -> C = 1.0
    bridge_triangles_graph.set_edge_active(2, 3, False)
    assert average_clustering_coefficient(bridge_triangles_graph) == pytest.approx(1.0)


def test_local_clustering_out_of_bounds_raises(path_graph: SimpleTestGraph) -> None:
    with pytest.raises(ValueError):
        local_clustering_coefficient(path_graph, -1)
    with pytest.raises(ValueError):
        local_clustering_coefficient(path_graph, 4)


def test_betweenness_empty_and_small_graphs(empty_graph: SimpleTestGraph) -> None:
    assert betweenness_centrality(SimpleTestGraph(0)) == {}
    assert betweenness_centrality(SimpleTestGraph(2)) == {0: 0.0, 1: 0.0}
    assert betweenness_centrality(empty_graph) == {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}


def test_betweenness_path_graph(path_graph: SimpleTestGraph) -> None:
    # Em P4 (0 - 1 - 2 - 3):
    # Vértice 1 está nos caminhos (0,2) e (0,3) -> 2 caminhos não ordenados.
    # Total de pares sem o próprio vértice = (4-1)*(4-2)/2 = 3 -> normalizado = 2/3.
    bc_unnorm = betweenness_centrality(path_graph, normalized=False)
    assert bc_unnorm[0] == pytest.approx(0.0)
    assert bc_unnorm[1] == pytest.approx(2.0)
    assert bc_unnorm[2] == pytest.approx(2.0)
    assert bc_unnorm[3] == pytest.approx(0.0)

    bc_norm = betweenness_centrality(path_graph, normalized=True)
    assert bc_norm[0] == pytest.approx(0.0)
    assert bc_norm[1] == pytest.approx(2 / 3)
    assert bc_norm[2] == pytest.approx(2 / 3)
    assert bc_norm[3] == pytest.approx(0.0)


def test_betweenness_star_and_complete_graphs(
    star_graph: SimpleTestGraph,
    complete_graph: SimpleTestGraph,
) -> None:
    # Na estrela S5, o centro 0 intermedeia todos os pares entre as 4 folhas -> 1.0
    bc_star = betweenness_centrality(star_graph, normalized=True)
    assert bc_star[0] == pytest.approx(1.0)
    for leaf in range(1, 5):
        assert bc_star[leaf] == pytest.approx(0.0)

    # Em K4, todos os pares têm aresta direta -> intermediação 0.0 para todos
    bc_complete = betweenness_centrality(complete_graph, normalized=True)
    for u in range(4):
        assert bc_complete[u] == pytest.approx(0.0)


def test_betweenness_cycle_graph(cycle_graph: SimpleTestGraph) -> None:
    # Em C4 (0-1-2-3-0), os pares opostos (0,2) e (1,3) têm 2 caminhos mínimos de tamanho 2.
    # Cada vértice recebe 0.5 não normalizado, ou 0.5 / 3 = 1/6 normalizado.
    bc = betweenness_centrality(cycle_graph, normalized=True)
    for u in range(4):
        assert bc[u] == pytest.approx(1 / 6)


def test_betweenness_bridge_triangles_and_sampling(
    bridge_triangles_graph: SimpleTestGraph,
) -> None:
    # Nos dois triângulos ligados pela ponte (2, 3), o vértice 2 intermedeia
    # todos os pares entre {0, 1} e {3, 4, 5}: 2 * 3 = 6 pares em C(5, 2) = 10 -> 0.6
    bc_exact = betweenness_centrality(bridge_triangles_graph, normalized=True)
    assert bc_exact[2] == pytest.approx(0.6)
    assert bc_exact[3] == pytest.approx(0.6)
    for u in (0, 1, 4, 5):
        assert bc_exact[u] == pytest.approx(0.0)

    # Aproximada com mesma semente deve ser 100% determinística (RN03)
    bc_approx_a = betweenness_centrality(bridge_triangles_graph, k=3, seed=42)
    bc_approx_b = betweenness_centrality(bridge_triangles_graph, k=3, seed=42)
    assert bc_approx_a == bc_approx_b
    assert bc_approx_a[2] > bc_approx_a[0]


def test_betweenness_invalid_k_raises(path_graph: SimpleTestGraph) -> None:
    with pytest.raises(ValueError):
        betweenness_centrality(path_graph, k=0)
    with pytest.raises(ValueError):
        betweenness_centrality(path_graph, k=-2)
