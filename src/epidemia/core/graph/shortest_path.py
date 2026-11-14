"""Algoritmo de Dijkstra para caminho mínimo epidemiológico.

Minimiza a distância efetiva de transmissão ``sum(-ln(min(p_e, 0.999)))``, o que
equivale matematicamente a encontrar o caminho de maior probabilidade acumulada
de contágio entre a origem e os demais vértices da rede.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from epidemia.core.errors import ParameterOutOfRangeError, VertexNotFoundError
from epidemia.core.graph.graph import Graph
from epidemia.core.graph.traversal import reconstruct_path
from epidemia.core.graph.weights import transmission_probability, travel_cost


@dataclass(frozen=True, slots=True)
class ShortestPathResult:
    """Resultado do algoritmo de Dijkstra a partir de ``source``."""

    source: int
    distances: dict[int, float]
    parent: dict[int, int | None]

    def distance_to(self, target: int) -> float:
        """Retorna a distância efetiva mínima até ``target`` (ou ``math.inf`` se inalcançável)."""
        return self.distances.get(target, math.inf)

    def path_probability(self, target: int) -> float:
        """Retorna a probabilidade acumulada ``exp(-dist)`` ao longo do caminho mais provável."""
        dist = self.distances.get(target)
        if dist is None:
            return 0.0
        return math.exp(-dist)

    def path_to(self, target: int) -> list[int]:
        """Reconstrói o caminho de menor custo de ``source`` até ``target``."""
        return reconstruct_path(self.parent, target)


def dijkstra(
    graph: Graph,
    source: int,
    target: int | None = None,
    *,
    beta: float | None = None,
    only_active: bool = True,
) -> ShortestPathResult:
    """Calcula caminhos mínimos a partir de ``source`` com fila de prioridade (heap binário).

    Parâmetros:
        graph: Instância de ``Graph``.
        source: Vértice de partida.
        target: Se informado, encerra a busca assim que a distância mínima de
            ``target`` for fixada (parada antecipada).
        beta: Se informado, calcula o custo de cada aresta dinamicamente via
            ``travel_cost(transmission_probability(w, beta))`` (Decisão A16).
            Caso ``None``, utiliza ``graph.edge_cost(u, v)``.
        only_active: Se ``True`` (padrão), ignora arestas desativadas e vértices isolados.

    Complexidade de tempo: O((V + E) log V).
    Complexidade de espaço: O(V).
    """
    if not graph.has_vertex(source):
        raise VertexNotFoundError(f"Vértice de origem {source} não existe no grafo.")
    if target is not None and not graph.has_vertex(target):
        raise VertexNotFoundError(f"Vértice de destino {target} não existe no grafo.")
    if beta is not None and (beta <= 0.0 or not math.isfinite(beta)):
        raise ParameterOutOfRangeError(f"O parâmetro beta deve ser positivo: {beta}")

    distances: dict[int, float] = {source: 0.0}
    parent: dict[int, int | None] = {source: None}
    heap: list[tuple[float, int]] = [(0.0, source)]

    while heap:
        dist_u, u = heapq.heappop(heap)

        # Entrada obsoleta no heap (já encontramos caminho mais curto para u antes)
        if dist_u > distances.get(u, math.inf):
            continue

        if target is not None and u == target:
            break

        for v in graph.neighbors(u, only_active=only_active):
            if beta is not None:
                w = graph.edge_weight(u, v)
                cost_uv = travel_cost(transmission_probability(w, beta))
            else:
                cost_uv = graph.edge_cost(u, v)

            new_dist = dist_u + cost_uv
            if new_dist < distances.get(v, math.inf):
                distances[v] = new_dist
                parent[v] = u
                heapq.heappush(heap, (new_dist, v))

    return ShortestPathResult(source=source, distances=distances, parent=parent)
