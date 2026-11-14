"""Estrutura própria de grafo não direcionado ponderado com máscara de arestas"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass

from epidemia.core.errors import (
    InvalidEdgeError,
    ParameterOutOfRangeError,
    VertexNotFoundError,
)
from epidemia.core.graph.weights import (
    DEFAULT_BETA,
    effective_distance_cost,
    transmission_probability,
)


@dataclass(frozen=True)
class VertexInfo:
    """Metadados estáticos de um vértice (país e coordenadas no mapa)."""

    vertex_id: int
    country_id: int = 0
    position: tuple[float, float] = (0.0, 0.0)


class Graph:
    """Grafo simples não direcionado com lista de adjacência e máscara de isolamento."""

    def __init__(self, num_vertices: int = 0, *, beta: float = DEFAULT_BETA) -> None:
        if num_vertices < 0:
            raise ParameterOutOfRangeError(f"num_vertices não pode ser negativo: {num_vertices}")
        if beta <= 0.0 or not math.isfinite(beta):
            raise ParameterOutOfRangeError(f"O parâmetro beta deve ser positivo: {beta}")

        self._beta: float = beta
        self._adj: list[dict[int, int]] = []
        self._vertices: list[VertexInfo] = []
        self._vertex_present: bytearray = bytearray()
        self._vertex_isolated: bytearray = bytearray()
        self._weights: list[float] = []
        self._costs: list[float] = []
        self._edge_active: bytearray = bytearray()
        self._present_edge_count: int = 0

        for _ in range(num_vertices):
            self.add_vertex()

    @property
    def num_vertices(self) -> int:
        """Total de indíces de vértices alocados no grafo."""
        return len(self._adj)

    @property
    def num_edges(self) -> int:
        """Quantidade de arestas presentes no grafo."""
        return self._present_edge_count

    @property
    def beta(self) -> float:
        """Taxa de transmissão usada nos custos de caminho."""
        return self._beta

    def _validate_vertex(self, u: int) -> None:
        if not (0 <= u < len(self._adj)) or not self._vertex_present[u]:
            raise VertexNotFoundError(f"Vértice {u} não existe ou foi removido do grafo.")

    def has_vertex(self, u: int) -> bool:
        """Retorna ``True`` se o vértice ``u`` está presente no grafo."""
        return 0 <= u < len(self._adj) and bool(self._vertex_present[u])

    def add_vertex(
        self,
        *,
        country_id: int = 0,
        position: tuple[float, float] = (0.0, 0.0),
    ) -> int:
        """Insere um novo vértice e retorna seu índice ``u`` em O(1)."""
        u = len(self._adj)
        self._adj.append({})
        self._vertices.append(VertexInfo(vertex_id=u, country_id=country_id, position=position))
        self._vertex_present.append(1)
        self._vertex_isolated.append(0)
        return u

    def vertex_info(self, u: int) -> VertexInfo:
        """Retorna os metadados do vértice ``u``."""
        self._validate_vertex(u)
        return self._vertices[u]

    def remove_vertex(self, u: int) -> None:
        """Remove o vértice ``u`` e suas arestas incidentes em O(grau(u)) (RF15)."""
        self._validate_vertex(u)
        for v in list(self._adj[u].keys()):
            self.remove_edge(u, v)
        self._vertex_present[u] = 0
        self._vertex_isolated[u] = 0

    def add_edge(
        self,
        u: int,
        v: int,
        weight: float = 1.0,
        *,
        cost: float | None = None,
    ) -> int:
        """Insere ou atualiza a aresta não direcionada ``(u, v)`` em O(1) médio."""
        self._validate_vertex(u)
        self._validate_vertex(v)
        if u == v:
            raise InvalidEdgeError(f"Auto-laços não são permitidos: ({u}, {v}).")
        if weight <= 0.0 or not math.isfinite(weight):
            raise InvalidEdgeError(f"O peso da aresta deve ser positivo: {weight}")
        if cost is None:
            computed_cost = effective_distance_cost(transmission_probability(weight, self._beta))
        else:
            if cost <= 0.0 or not math.isfinite(cost):
                raise InvalidEdgeError(f"O custo da aresta deve ser positivo: {cost}")
            computed_cost = float(cost)
        existing_id = self._adj[u].get(v)
        if existing_id is not None:
            self._weights[existing_id] = float(weight)
            self._costs[existing_id] = computed_cost
            self._edge_active[existing_id] = 1
            return existing_id
        edge_id = len(self._weights)
        self._weights.append(float(weight))
        self._costs.append(computed_cost)
        self._edge_active.append(1)
        self._present_edge_count += 1
        self._adj[u][v] = edge_id
        self._adj[v][u] = edge_id
        return edge_id

    def remove_edge(self, u: int, v: int) -> None:
        """Remove a aresta ``(u, v)`` em O(1) médio (RF15)."""
        self._validate_vertex(u)
        self._validate_vertex(v)
        edge_id = self._adj[u].pop(v, None)
        if edge_id is None:
            raise InvalidEdgeError(f"A aresta ({u}, {v}) não existe no grafo.")
        self._adj[v].pop(u, None)
        self._edge_active[edge_id] = 0
        self._present_edge_count -= 1

    def has_edge(self, u: int, v: int, *, only_active: bool = False) -> bool:
        """Retorna ``True`` se a aresta ``(u, v)`` existir (e estiver ativa, se ``only_active``)."""
        if not (self.has_vertex(u) and self.has_vertex(v)):
            return False
        edge_id = self._adj[u].get(v)
        if edge_id is None:
            return False
        if not only_active:
            return True
        return bool(
            self._edge_active[edge_id]
            and not self._vertex_isolated[u]
            and not self._vertex_isolated[v]
        )

    def set_edge_active(self, u: int, v: int, active: bool) -> None:
        """Ativa ou desativa a aresta ``(u, v)`` na máscara sem alterar a topologia (E1)."""
        self._validate_vertex(u)
        self._validate_vertex(v)
        edge_id = self._adj[u].get(v)
        if edge_id is None:
            raise InvalidEdgeError(f"A aresta ({u}, {v}) não existe no grafo.")
        self._edge_active[edge_id] = 1 if active else 0

    def set_vertex_isolated(self, u: int, isolated: bool) -> None:
        """Marca ou desmarca o vértice ``u`` como isolado em O(1) (C3, RF05)."""
        self._validate_vertex(u)
        self._vertex_isolated[u] = 1 if isolated else 0

    def is_vertex_isolated(self, u: int) -> bool:
        """Retorna ``True`` se o vértice ``u`` estiver isolado."""
        self._validate_vertex(u)
        return bool(self._vertex_isolated[u])

    def reset_masks(self) -> None:
        """Reativa todas as arestas e remove o isolamento de todos os vértices."""
        for u in range(len(self._adj)):
            self._vertex_isolated[u] = 0
            for edge_id in self._adj[u].values():
                self._edge_active[edge_id] = 1

    def neighbors(self, u: int, *, only_active: bool = True) -> Iterator[int]:
        """Itera sobre os vizinhos de ``u`` (apenas conexões ativas por padrão)."""
        if not self.has_vertex(u):
            return
        if only_active and self._vertex_isolated[u]:
            return
        for v, edge_id in self._adj[u].items():
            if not only_active or (self._edge_active[edge_id] and not self._vertex_isolated[v]):
                yield v

    def edge_weight(self, u: int, v: int) -> float:
        """Retorna o peso de contágio ``w`` da aresta ``(u, v)``."""
        self._validate_vertex(u)
        self._validate_vertex(v)
        edge_id = self._adj[u].get(v)
        if edge_id is None:
            raise InvalidEdgeError(f"A aresta ({u}, {v}) não existe no grafo.")
        return self._weights[edge_id]

    def edge_cost(self, u: int, v: int) -> float:
        """Retorna o custo ``-ln(p)`` da aresta ``(u, v)`` para o Dijkstra."""
        self._validate_vertex(u)
        self._validate_vertex(v)
        edge_id = self._adj[u].get(v)
        if edge_id is None:
            raise InvalidEdgeError(f"A aresta ({u}, {v}) não existe no grafo.")
        return self._costs[edge_id]

    def update_transmission_costs(self, beta: float) -> None:
        """Recalcula todos os custos ``-ln(p)`` quando ``beta`` é calibrado (B2)."""
        if beta <= 0.0 or not math.isfinite(beta):
            raise ParameterOutOfRangeError(f"O parâmetro beta deve ser positivo: {beta}")
        self._beta = beta
        for edge_id, w in enumerate(self._weights):
            self._costs[edge_id] = effective_distance_cost(transmission_probability(w, beta))
