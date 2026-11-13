"""Métricas estruturais de análise de redes (M2 — RF18).

Contém funções puras para cálculo de grau de vértices, grau médio da rede,
coeficiente de agrupamento (local e médio global) e centralidade de
intermediação (exata e aproximada por amostragem de fontes — algoritmo de Brandes),
operando apenas sobre a biblioteca padrão do Python.
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable
from typing import Any, Protocol


class GraphLike(Protocol):
    """Contrato mínimo de leitura de um grafo não direcionado para análise."""

    @property
    def num_vertices(self) -> int:
        """Número total de vértices do grafo (indexados de 0 a num_vertices - 1)."""
        ...

    def neighbors(self, u: int) -> Iterable[Any]:
        """Iterável com os vizinhos ativos do vértice ``u``."""
        ...


def _extract_neighbor_id(item: Any) -> int:
    """Extrai o índice inteiro do vértice vizinho a partir de diferentes representações."""
    if isinstance(item, int):
        return item
    if isinstance(item, tuple) and item:
        return int(item[0])
    for attr in ("target", "to", "v", "vertex", "neighbor"):
        if hasattr(item, attr):
            return int(getattr(item, attr))
    raise TypeError(f"Formato de vizinho não suportado: {type(item)!r}")


def _build_adj_sets(graph: GraphLike) -> list[set[int]]:
    """Constrói conjuntos de adjacência simétricos (sem auto-laços) para consulta rápida."""
    n = int(graph.num_vertices)
    adj: list[set[int]] = [set() for _ in range(n)]
    for u in range(n):
        for item in graph.neighbors(u):
            v = _extract_neighbor_id(item)
            if 0 <= v < n and v != u:
                adj[u].add(v)
                adj[v].add(u)
    return adj


def vertex_degree(graph: GraphLike, u: int) -> int:
    """Retorna o grau do vértice ``u`` (número de vizinhos ativos distintos).

    Complexidade: O(k_u) quando ``neighbors(u)`` reflete a adjacência simétrica.
    """
    n = int(graph.num_vertices)
    if not (0 <= u < n):
        raise ValueError(f"Vértice fora do intervalo [0, {n}): {u}")
    neighbors_u = {_extract_neighbor_id(item) for item in graph.neighbors(u)}
    neighbors_u.discard(u)
    return len(neighbors_u)


def degrees(graph: GraphLike) -> dict[int, int]:
    """Retorna um dicionário ``{vertice: grau}`` para todos os vértices do grafo.

    Complexidade: O(V + E).
    """
    adj = _build_adj_sets(graph)
    return {u: len(adj[u]) for u in range(len(adj))}


def average_degree(graph: GraphLike) -> float:
    """Retorna o grau médio do grafo: ``(1 / V) * sum(k_v)``.

    Retorna ``0.0`` se o grafo não possuir vértices.
    Complexidade: O(V + E).
    """
    adj = _build_adj_sets(graph)
    n = len(adj)
    if n == 0:
        return 0.0
    return sum(len(neighbors) for neighbors in adj) / n


def _clustering_from_adj(adj: list[set[int]], u: int) -> float:
    """Calcula o coeficiente de agrupamento local de ``u`` a partir de ``adj``."""
    neighbors_u = adj[u]
    k_u = len(neighbors_u)
    if k_u < 2:
        return 0.0

    # Cada aresta entre dois vizinhos (w1, w2) de u é contada duas vezes no somatório
    links_twice = sum(len(neighbors_u & adj[w]) for w in neighbors_u)
    return links_twice / (k_u * (k_u - 1))


def local_clustering_coefficient(graph: GraphLike, u: int) -> float:
    """Retorna o coeficiente de agrupamento local do vértice ``u``.

    Definido como ``2 * t_u / (k_u * (k_u - 1))``, onde ``t_u`` é o número de
    arestas entre os vizinhos de ``u``. Retorna ``0.0`` se ``k_u < 2``.
    """
    n = int(graph.num_vertices)
    if not (0 <= u < n):
        raise ValueError(f"Vértice fora do intervalo [0, {n}): {u}")
    adj = _build_adj_sets(graph)
    return _clustering_from_adj(adj, u)


def clustering_coefficients(graph: GraphLike) -> dict[int, float]:
    """Retorna ``{vertice: C_v}`` com o coeficiente de agrupamento local de cada vértice.

    Complexidade: O(sum(k_v^2)) usando interseção de conjuntos de vizinhança.
    """
    adj = _build_adj_sets(graph)
    return {u: _clustering_from_adj(adj, u) for u in range(len(adj))}


def average_clustering_coefficient(graph: GraphLike) -> float:
    """Retorna o coeficiente de agrupamento médio global: ``(1 / V) * sum(C_v)``.

    Retorna ``0.0`` se o grafo não possuir vértices.
    Complexidade: O(sum(k_v^2)).
    """
    adj = _build_adj_sets(graph)
    n = len(adj)
    if n == 0:
        return 0.0
    return sum(_clustering_from_adj(adj, u) for u in range(n)) / n


def betweenness_centrality(
    graph: GraphLike,
    k: int | None = None,
    *,
    normalized: bool = True,
    seed: int | random.Random | None = None,
) -> dict[int, float]:
    """Calcula a centralidade de intermediação (algoritmo de Brandes).

    Se ``k`` for ``None`` ou ``k >= V``, calcula a intermediação exata usando
    todos os vértices como fonte em ``O(V * (V + E))``.
    Se ``1 <= k < V``, estima a intermediação amostrando ``k`` fontes sem
    reposição de forma determinística (via ``seed``) em ``O(k * (V + E))``.

    Parâmetros:
        graph: Grafo não direcionado a analisar.
        k: Número de fontes amostradas (``None`` para cálculo exato).
        normalized: Se ``True``, normaliza por ``2 / ((V - 1) * (V - 2))`` para
            grafos não direcionados.
        seed: Semente inteira ou instância de ``random.Random`` para amostragem.
    """
    adj = _build_adj_sets(graph)
    n = len(adj)
    if n == 0:
        return {}

    if k is not None and k <= 0:
        raise ValueError(f"O número de fontes amostradas k deve ser positivo: {k}")

    centrality: dict[int, float] = {u: 0.0 for u in range(n)}
    if n <= 2:
        return centrality

    if k is None or k >= n:
        sources: list[int] = list(range(n))
    else:
        rng = seed if isinstance(seed, random.Random) else random.Random(seed)
        sources = rng.sample(range(n), k)

    for s in sources:
        stack: list[int] = []
        predecessors: list[list[int]] = [[] for _ in range(n)]
        sigma: list[float] = [0.0] * n
        sigma[s] = 1.0
        dist: list[int] = [-1] * n
        dist[s] = 0

        queue: deque[int] = deque([s])
        while queue:
            v = queue.popleft()
            stack.append(v)
            d_v = dist[v]
            sigma_v = sigma[v]
            for w in adj[v]:
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = d_v + 1
                if dist[w] == d_v + 1:
                    sigma[w] += sigma_v
                    predecessors[w].append(v)

        delta: list[float] = [0.0] * n
        while stack:
            w = stack.pop()
            coeff = (1.0 + delta[w]) / sigma[w]
            for v in predecessors[w]:
                delta[v] += sigma[v] * coeff
            if w != s:
                centrality[w] += delta[w]

    # Em grafo não direcionado, cada par {s, t} é contado duas vezes
    scale = 0.5
    if k is not None and k < n:
        scale *= n / k
    if normalized:
        scale *= 2.0 / ((n - 1) * (n - 2))

    for u in range(n):
        centrality[u] *= scale

    return centrality
