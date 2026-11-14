"""Algoritmos clássicos de travessia em grafos: BFS, DFS e Componentes Conexos.
Todas as funções operam em tempo O(V + E) e espaço O(V) usando apenas a
biblioteca padrão do Python e respeitando a máscara de isolamento/arestas
ativas da classe ``Graph`` por padrão (``only_active=True``).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from epidemia.core.errors import VertexNotFoundError
from epidemia.core.graph.graph import Graph


@dataclass(frozen=True, slots=True)
class BFSResult:
    """Resultado de uma Busca em Largura (BFS) a partir de ``source``."""

    source: int
    order: list[int]
    distances: dict[int, int]
    parent: dict[int, int | None]

    def path_to(self, target: int) -> list[int]:
        """Reconstrói o caminho mínimo em número de saltos de ``source`` até ``target``.
        Retorna lista vazia se ``target`` não foi alcançado pela busca.
        """
        if target not in self.parent:
            return []
        path: list[int] = []
        curr: int | None = target
        while curr is not None:
            path.append(curr)
            curr = self.parent[curr]
        path.reverse()
        return path


@dataclass(frozen=True, slots=True)
class DFSResult:
    """Resultado de uma Busca em Profundidade (DFS) iterativa a partir de ``source``."""

    source: int
    order: list[int]
    parent: dict[int, int | None]

    def path_to(self, target: int) -> list[int]:
        """Reconstrói o caminho na árvore de DFS de ``source`` até ``target``.
        Retorna lista vazia se ``target`` não foi alcançado pela busca.
        """
        if target not in self.parent:
            return []
        path: list[int] = []
        curr: int | None = target
        while curr is not None:
            path.append(curr)
            curr = self.parent[curr]
        path.reverse()
        return path


def bfs(graph: Graph, source: int, *, only_active: bool = True) -> BFSResult:
    """Executa Busca em Largura (BFS) a partir de ``source``.
    Se ``only_active=True`` e o próprio vértice ``source`` estiver isolado,
    ele é visitado a distância 0, mas não expande arestas para seus vizinhos.
    Complexidade de tempo: O(V + E).
    Complexidade de espaço: O(V).
    """
    if not graph.has_vertex(source):
        raise VertexNotFoundError(f"Vértice de origem {source} não existe no grafo.")
    order: list[int] = []
    distances: dict[int, int] = {source: 0}
    parent: dict[int, int | None] = {source: None}
    queue: deque[int] = deque([source])
    while queue:
        u = queue.popleft()
        order.append(u)
        dist_u = distances[u]
        for v in graph.neighbors(u, only_active=only_active):
            if v not in distances:
                distances[v] = dist_u + 1
                parent[v] = u
                queue.append(v)
    return BFSResult(source=source, order=order, distances=distances, parent=parent)


def dfs(graph: Graph, source: int, *, only_active: bool = True) -> DFSResult:
    """Executa Busca em Profundidade (DFS) iterativa a partir de ``source``.
    Utiliza pilha explícita em vez de recursão para suportar grafos grandes
    (ex.: V = 8.000 a 50.000) sem atingir o limite de recursão do Python.
    Complexidade de tempo: O(V + E).
    Complexidade de espaço: O(V).
    """
    if not graph.has_vertex(source):
        raise VertexNotFoundError(f"Vértice de origem {source} não existe no grafo.")
    order: list[int] = []
    parent: dict[int, int | None] = {}
    visited: set[int] = set()
    # Pilha guarda tuplas (vertice_atual, pai_que_o_descobriu)
    stack: list[tuple[int, int | None]] = [(source, None)]
    while stack:
        u, p = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        parent[u] = p
        order.append(u)
        # Empilha em ordem reversa para visitar os vizinhos na ordem natural da adjacência
        neighbors_u = list(graph.neighbors(u, only_active=only_active))
        for v in reversed(neighbors_u):
            if v not in visited:
                stack.append((v, u))
    return DFSResult(source=source, order=order, parent=parent)


def connected_components(graph: Graph, *, only_active: bool = True) -> list[list[int]]:
    """Encontra todas as componentes conexas dos vértices presentes no grafo.
    Retorna uma lista de componentes (cada componente ordenada por ID de vértice),
    ordenadas da maior componente (Componente Gigante) para a menor.
    Complexidade de tempo: O(V + E).
    Complexidade de espaço: O(V).
    """
    visited: set[int] = set()
    components: list[list[int]] = []
    for start in graph.vertices():
        if start in visited:
            continue
        comp: list[int] = []
        queue: deque[int] = deque([start])
        visited.add(start)
        while queue:
            u = queue.popleft()
            comp.append(u)
            for v in graph.neighbors(u, only_active=only_active):
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
        comp.sort()
        components.append(comp)
    components.sort(key=lambda c: (-len(c), c[0] if c else 0))
    return components
