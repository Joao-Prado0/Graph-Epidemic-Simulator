"""Algoritmo de Tarjan para pontes e pontos de articulação (M2 — RF20).

Identifica arestas críticas (pontes) e vértices críticos (pontos de articulação)
em uma única busca em profundidade (DFS iterativa) com complexidade O(V + E).
"""

from __future__ import annotations

from dataclasses import dataclass

from epidemia.core.analysis.metrics import GraphLike, _build_adj_sets


@dataclass(frozen=True)
class TarjanResult:
    """Resultado da execução única do algoritmo de Tarjan sobre o grafo."""

    bridges: list[tuple[int, int]]
    articulation_points: set[int]


def find_bridges_and_articulation_points(graph: GraphLike) -> TarjanResult:
    """Encontra todas as pontes e pontos de articulação em uma única DFS iterativa.

    - **Ponte:** aresta ``(u, v)`` (com ``u < v``) cuja remoção aumenta o número
      de componentes conexos.
    - **Ponto de articulação:** vértice cuja remoção aumenta o número de
      componentes conexos.

    A implementação usa pilha explícita para suportar grafos grandes (8.000+
    vértices) sem atingir o limite de recursão do Python.

    Complexidade: O(V + E).
    """
    adj_sets = _build_adj_sets(graph)
    n = len(adj_sets)
    adj = [sorted(neighbors) for neighbors in adj_sets]

    disc: list[int] = [-1] * n
    low: list[int] = [-1] * n
    parent: list[int] = [-1] * n
    children_count: list[int] = [0] * n

    bridges: list[tuple[int, int]] = []
    articulation_points: set[int] = set()
    timer = 0

    for start in range(n):
        if disc[start] != -1:
            continue

        disc[start] = timer
        low[start] = timer
        timer += 1

        # Cada quadro da pilha guarda (vertice_atual, indice_proximo_vizinho)
        stack: list[list[int]] = [[start, 0]]

        while stack:
            frame = stack[-1]
            u = frame[0]
            idx = frame[1]
            neighbors_u = adj[u]

            if idx < len(neighbors_u):
                v = neighbors_u[idx]
                frame[1] = idx + 1

                if v == parent[u]:
                    continue

                if disc[v] == -1:
                    parent[v] = u
                    children_count[u] += 1
                    disc[v] = timer
                    low[v] = timer
                    timer += 1
                    stack.append([v, 0])
                elif disc[v] < low[u]:
                    low[u] = disc[v]
            else:
                stack.pop()
                p = parent[u]
                if p != -1:
                    if low[u] < low[p]:
                        low[p] = low[u]
                    if low[u] > disc[p]:
                        bridges.append((min(p, u), max(p, u)))
                    if parent[p] != -1 and low[u] >= disc[p]:
                        articulation_points.add(p)
                else:
                    if children_count[u] > 1:
                        articulation_points.add(u)

    bridges.sort()
    return TarjanResult(bridges=bridges, articulation_points=articulation_points)


def find_bridges(graph: GraphLike) -> list[tuple[int, int]]:
    """Retorna a lista ordenada de pontes ``(u, v)`` (com ``u < v``) do grafo.

    Complexidade: O(V + E).
    """
    return find_bridges_and_articulation_points(graph).bridges


def find_articulation_points(graph: GraphLike) -> set[int]:
    """Retorna o conjunto de pontos de articulação do grafo.

    Complexidade: O(V + E).
    """
    return find_bridges_and_articulation_points(graph).articulation_points
