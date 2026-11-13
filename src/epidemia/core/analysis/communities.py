"""Detecção de comunidades por propagação de rótulos (M2 — RF19).

Implementa o algoritmo assíncrono de Propagação de Rótulos (*Label Propagation*)
com desempate determinístico por semente (RN03, RNF05) e suporte à contração
do grafo global por país.
"""

from __future__ import annotations

import random
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from epidemia.core.analysis.metrics import GraphLike, _extract_neighbor_id


@dataclass(frozen=True)
class CommunityResult:
    """Resultado da detecção de comunidades por propagação de rótulos."""

    communities: list[set[int]]
    vertex_community: dict[int, int]
    iterations: int


class ContractedGraph:
    """Grafo ponderado obtido pela contração de vértices por grupo (ex.: país)."""

    def __init__(self, num_vertices: int) -> None:
        self._num_vertices = num_vertices
        self._adj: list[dict[int, float]] = [{} for _ in range(num_vertices)]

    @property
    def num_vertices(self) -> int:
        return self._num_vertices

    def add_edge_weight(self, u: int, v: int, weight: float = 1.0) -> None:
        """Soma ``weight`` à aresta não direcionada ``(u, v)`` (ignora auto-laços)."""
        if u == v:
            return
        self._adj[u][v] = self._adj[u].get(v, 0.0) + weight
        self._adj[v][u] = self._adj[v].get(u, 0.0) + weight

    def neighbors(self, u: int) -> Iterator[int]:
        return iter(self._adj[u].keys())

    def edge_weight(self, u: int, v: int) -> float:
        return self._adj[u].get(v, 0.0)


def _extract_weighted_adj(
    graph: GraphLike,
    *,
    weighted: bool,
) -> list[list[tuple[int, float]]]:
    """Extrai listas de adjacência ``[(vizinho, peso), ...]`` ordenadas por vértice."""
    n = int(graph.num_vertices)
    adj_map: list[dict[int, float]] = [{} for _ in range(n)]
    has_edge_weight = hasattr(graph, "edge_weight") and callable(graph.edge_weight)

    for u in range(n):
        for item in graph.neighbors(u):
            v = _extract_neighbor_id(item)
            if not (0 <= v < n) or v == u:
                continue

            w = 1.0
            if weighted:
                if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], int | float):
                    w = float(item[1])
                elif has_edge_weight:
                    w = float(graph.edge_weight(u, v))  # type: ignore[attr-defined]
                else:
                    for attr in ("weight", "w"):
                        if hasattr(item, attr):
                            w = float(getattr(item, attr))
                            break

            adj_map[u][v] = w
            adj_map[v][u] = w

    return [sorted(neighbors.items()) for neighbors in adj_map]


def contract_graph_by_country(
    graph: GraphLike,
    vertex_country: Sequence[int],
    num_countries: int | None = None,
) -> ContractedGraph:
    """Contrai um grafo de indivíduos em um grafo de países ponderado pelas arestas.

    Cada aresta entre dois vértices de países distintos ``(c_u, c_v)`` soma seu
    peso à aresta correspondente entre ``c_u`` e ``c_v`` no grafo contraído.

    Complexidade: O(V + E).
    """
    n = int(graph.num_vertices)
    if len(vertex_country) != n:
        raise ValueError(
            f"Comprimento de vertex_country ({len(vertex_country)}) difere de num_vertices ({n})."
        )

    if num_countries is None:
        num_countries = (max(vertex_country) + 1) if vertex_country else 0

    contracted = ContractedGraph(num_countries)
    adj = _extract_weighted_adj(graph, weighted=True)

    for u in range(n):
        c_u = vertex_country[u]
        for v, w in adj[u]:
            if u < v:
                c_v = vertex_country[v]
                if c_u != c_v:
                    contracted.add_edge_weight(c_u, c_v, w)

    return contracted


def label_propagation_communities(
    graph: GraphLike,
    *,
    seed: int | random.Random | None = None,
    max_iterations: int = 100,
    weighted: bool = True,
) -> CommunityResult:
    """Detecta comunidades pelo algoritmo de Propagação de Rótulos (RF19).

    Cada vértice inicia com seu próprio rótulo e, a cada iteração (em ordem
    embaralhada pela semente fixa), passa a adotar o rótulo de maior peso
    acumulado entre seus vizinhos, desempatando de forma reproduzível.

    Complexidade por iteração: O(V + E).
    """
    if max_iterations <= 0:
        raise ValueError(f"max_iterations deve ser positivo: {max_iterations}")

    adj = _extract_weighted_adj(graph, weighted=weighted)
    n = len(adj)
    if n == 0:
        return CommunityResult(communities=[], vertex_community={}, iterations=0)

    rng = seed if isinstance(seed, random.Random) else random.Random(seed)
    labels: list[int] = list(range(n))
    order: list[int] = list(range(n))

    iterations_done = 0
    for _ in range(max_iterations):
        iterations_done += 1
        rng.shuffle(order)
        changed = False

        for u in order:
            neighbors_u = adj[u]
            if not neighbors_u:
                continue

            scores: dict[int, float] = {}
            for v, w in neighbors_u:
                lbl = labels[v]
                scores[lbl] = scores.get(lbl, 0.0) + w

            max_score = max(scores.values())
            best_labels = sorted(
                lbl for lbl, score in scores.items() if abs(score - max_score) <= 1e-12
            )

            if len(best_labels) == 1:
                chosen = best_labels[0]
            else:
                chosen = rng.choice(best_labels)

            if chosen != labels[u]:
                labels[u] = chosen
                changed = True

        if not changed:
            break

    # Agrupa por rótulo final e ordena as comunidades pelo menor vértice
    groups_by_label: dict[int, set[int]] = {}
    for u, lbl in enumerate(labels):
        groups_by_label.setdefault(lbl, set()).add(u)

    communities = sorted(groups_by_label.values(), key=lambda comm: min(comm))
    vertex_community: dict[int, int] = {}
    for comm_id, comm in enumerate(communities):
        for u in comm:
            vertex_community[u] = comm_id

    return CommunityResult(
        communities=communities,
        vertex_community=vertex_community,
        iterations=iterations_done,
    )
