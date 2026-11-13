"""Fixtures compartilhadas de grafos pequenos com resposta conhecida (M2)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


class SimpleTestGraph:
    """Grafo não direcionado leve para testes unitários, com suporte a máscara de arestas."""

    def __init__(self, num_vertices: int) -> None:
        if num_vertices < 0:
            raise ValueError("num_vertices deve ser não negativo.")
        self._num_vertices = num_vertices
        self._adj: list[dict[int, float]] = [{} for _ in range(num_vertices)]
        self._inactive_edges: set[tuple[int, int]] = set()

    @property
    def num_vertices(self) -> int:
        return self._num_vertices

    def add_edge(self, u: int, v: int, weight: float = 1.0) -> None:
        if u == v:
            return
        self._adj[u][v] = weight
        self._adj[v][u] = weight

    def set_edge_active(self, u: int, v: int, active: bool) -> None:
        edge = (min(u, v), max(u, v))
        if active:
            self._inactive_edges.discard(edge)
        else:
            self._inactive_edges.add(edge)

    def neighbors(self, u: int) -> Iterator[int]:
        for v in self._adj[u]:
            edge = (min(u, v), max(u, v))
            if edge not in self._inactive_edges:
                yield v

    def edge_weight(self, u: int, v: int) -> float:
        return self._adj[u].get(v, 1.0)


@pytest.fixture
def empty_graph() -> SimpleTestGraph:
    """Grafo com 4 vértices e nenhuma aresta."""
    return SimpleTestGraph(4)


@pytest.fixture
def path_graph() -> SimpleTestGraph:
    """Grafo caminho P4: 0 - 1 - 2 - 3."""
    g = SimpleTestGraph(4)
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    return g


@pytest.fixture
def cycle_graph() -> SimpleTestGraph:
    """Grafo ciclo C4: 0 - 1 - 2 - 3 - 0."""
    g = SimpleTestGraph(4)
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 0)
    return g


@pytest.fixture
def complete_graph() -> SimpleTestGraph:
    """Grafo completo K4: todos os 4 vértices conectados entre si."""
    g = SimpleTestGraph(4)
    for u in range(4):
        for v in range(u + 1, 4):
            g.add_edge(u, v)
    return g


@pytest.fixture
def star_graph() -> SimpleTestGraph:
    """Grafo estrela S5: centro 0 ligado às folhas 1, 2, 3 e 4."""
    g = SimpleTestGraph(5)
    for leaf in range(1, 5):
        g.add_edge(0, leaf)
    return g


@pytest.fixture
def bridge_triangles_graph() -> SimpleTestGraph:
    """Dois triângulos (0-1-2 e 3-4-5) conectados pela ponte (2, 3)."""
    g = SimpleTestGraph(6)
    # Triângulo 1
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 0)
    # Ponte
    g.add_edge(2, 3)
    # Triângulo 2
    g.add_edge(3, 4)
    g.add_edge(4, 5)
    g.add_edge(5, 3)
    return g
