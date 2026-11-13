"""Testes unitários da detecção de comunidades por propagação de rótulos (M2 — RF19)."""

from __future__ import annotations

import pytest

from epidemia.core.analysis import (
    contract_graph_by_country,
    label_propagation_communities,
)
from tests.conftest import SimpleTestGraph


def test_communities_empty_and_zero_graphs(empty_graph: SimpleTestGraph) -> None:
    res_zero = label_propagation_communities(SimpleTestGraph(0), seed=42)
    assert res_zero.communities == []
    assert res_zero.vertex_community == {}
    assert res_zero.iterations == 0

    # Em um grafo sem arestas, cada vértice isolado forma sua própria comunidade
    res_empty = label_propagation_communities(empty_graph, seed=42)
    assert res_empty.communities == [{0}, {1}, {2}, {3}]
    assert res_empty.vertex_community == {0: 0, 1: 1, 2: 2, 3: 3}


def test_communities_complete_graph(complete_graph: SimpleTestGraph) -> None:
    # Em K4, todos os vértices convergem para uma única comunidade
    res = label_propagation_communities(complete_graph, seed=42)
    assert res.communities == [{0, 1, 2, 3}]
    assert all(c == 0 for c in res.vertex_community.values())


def test_communities_two_cliques_connected_by_weak_bridge() -> None:
    # Dois cliques K4 (0..3 e 4..7) conectados por uma ponte fraca (3, 4)
    g = SimpleTestGraph(8)
    for u in range(4):
        for v in range(u + 1, 4):
            g.add_edge(u, v, weight=5.0)
    for u in range(4, 8):
        for v in range(u + 1, 8):
            g.add_edge(u, v, weight=5.0)
    g.add_edge(3, 4, weight=0.2)

    res = label_propagation_communities(g, seed=123)
    assert res.communities == [{0, 1, 2, 3}, {4, 5, 6, 7}]
    for u in range(4):
        assert res.vertex_community[u] == 0
    for u in range(4, 8):
        assert res.vertex_community[u] == 1


def test_communities_reproducibility_with_same_seed(
    bridge_triangles_graph: SimpleTestGraph,
) -> None:
    # RN03 e RNF05: mesma semente produz exatamente o mesmo resultado
    res_a = label_propagation_communities(bridge_triangles_graph, seed=999)
    res_b = label_propagation_communities(bridge_triangles_graph, seed=999)
    assert res_a == res_b


def test_contract_graph_by_country(
    bridge_triangles_graph: SimpleTestGraph,
) -> None:
    # Vértices 0, 1, 2 pertencem ao país 0; vértices 3, 4, 5 ao país 1; país 2 isolado
    vertex_country = [0, 0, 0, 1, 1, 1]
    contracted = contract_graph_by_country(
        bridge_triangles_graph,
        vertex_country,
        num_countries=3,
    )
    assert contracted.num_vertices == 3
    assert list(contracted.neighbors(0)) == [1]
    assert list(contracted.neighbors(1)) == [0]
    assert list(contracted.neighbors(2)) == []
    assert contracted.edge_weight(0, 1) == pytest.approx(1.0)


def test_contract_graph_invalid_length_raises(path_graph: SimpleTestGraph) -> None:
    with pytest.raises(ValueError):
        contract_graph_by_country(path_graph, [0, 1])


def test_communities_invalid_max_iterations_raises(path_graph: SimpleTestGraph) -> None:
    with pytest.raises(ValueError):
        label_propagation_communities(path_graph, max_iterations=0)
