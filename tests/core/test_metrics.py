"""Testes unitários das métricas de grau (M2 — RF18)."""

from __future__ import annotations

import pytest

from epidemia.core.analysis import average_degree, degrees, vertex_degree
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
