"""Testes unitários do algoritmo de Tarjan para pontes e articulações (M2 — RF20)."""

from __future__ import annotations

from epidemia.core.analysis import (
    find_articulation_points,
    find_bridges,
    find_bridges_and_articulation_points,
)
from tests.conftest import SimpleTestGraph


def test_tarjan_empty_and_zero_graphs(empty_graph: SimpleTestGraph) -> None:
    res_zero = find_bridges_and_articulation_points(SimpleTestGraph(0))
    assert res_zero.bridges == []
    assert res_zero.articulation_points == set()

    res_empty = find_bridges_and_articulation_points(empty_graph)
    assert res_empty.bridges == []
    assert res_empty.articulation_points == set()


def test_tarjan_path_graph(path_graph: SimpleTestGraph) -> None:
    # Em um caminho P4 (0 - 1 - 2 - 3), todas as arestas são pontes e os vértices
    # internos (1 e 2) são pontos de articulação (critério 11.1 da modelagem).
    assert find_bridges(path_graph) == [(0, 1), (1, 2), (2, 3)]
    assert find_articulation_points(path_graph) == {1, 2}


def test_tarjan_cycle_and_complete_graphs(
    cycle_graph: SimpleTestGraph,
    complete_graph: SimpleTestGraph,
) -> None:
    # Em ciclos e grafos completos (V >= 3), não existem pontes nem articulações.
    for g in (cycle_graph, complete_graph):
        res = find_bridges_and_articulation_points(g)
        assert res.bridges == []
        assert res.articulation_points == set()


def test_tarjan_star_graph(star_graph: SimpleTestGraph) -> None:
    # Na estrela S5, todas as 4 arestas são pontes e apenas o centro (0) é articulação.
    assert find_bridges(star_graph) == [(0, 1), (0, 2), (0, 3), (0, 4)]
    assert find_articulation_points(star_graph) == {0}


def test_tarjan_bridge_triangles_graph(
    bridge_triangles_graph: SimpleTestGraph,
) -> None:
    # Dois triângulos (0-1-2 e 3-4-5) ligados pela ponte (2, 3):
    # A única ponte é (2, 3) e os pontos de articulação são 2 e 3.
    res = find_bridges_and_articulation_points(bridge_triangles_graph)
    assert res.bridges == [(2, 3)]
    assert res.articulation_points == {2, 3}

    # Se a ponte (2, 3) for desativada (isolamento), restam dois triângulos disjuntos
    bridge_triangles_graph.set_edge_active(2, 3, False)
    res_after = find_bridges_and_articulation_points(bridge_triangles_graph)
    assert res_after.bridges == []
    assert res_after.articulation_points == set()


def test_tarjan_deep_line_graph_no_recursion_error() -> None:
    # Garante que a DFS iterativa suporta profundidades maiores que o limite de recursão (1000)
    n = 2500
    g = SimpleTestGraph(n)
    for i in range(n - 1):
        g.add_edge(i, i + 1)

    res = find_bridges_and_articulation_points(g)
    assert len(res.bridges) == n - 1
    assert len(res.articulation_points) == n - 2
