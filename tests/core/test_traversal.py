"""Testes unitários dos algoritmos de travessia: BFS, DFS e Componentes Conexos (RF16)."""

from __future__ import annotations

import pytest

from epidemia.core.errors import VertexNotFoundError
from epidemia.core.graph import (
    Graph,
    bfs,
    connected_components,
    dfs,
)


def _build_line_graph(n: int) -> Graph:
    """Cria um grafo caminho 0 - 1 - 2 - ... - (n-1)."""
    g = Graph(n)
    for i in range(n - 1):
        g.add_edge(i, i + 1)
    return g


def test_bfs_em_grafo_caminho_e_reconstrucao_de_rota() -> None:
    """Em um caminho 0-1-2-3-4, a BFS deve calcular distâncias exatas em saltos."""
    g = _build_line_graph(5)
    res = bfs(g, 0)

    assert res.source == 0
    assert res.order == [0, 1, 2, 3, 4]
    assert res.distances == {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}
    assert res.path_to(4) == [0, 1, 2, 3, 4]
    assert res.path_to(99) == []


def test_bfs_em_ciclo_escolhe_menor_numero_de_saltos() -> None:
    """Em um ciclo 0-1-2-3-4-0, a distância de 0 até 4 deve ser 1 salto."""
    g = _build_line_graph(5)
    g.add_edge(4, 0)

    res = bfs(g, 0)
    assert res.distances[0] == 0
    assert res.distances[1] == 1
    assert res.distances[4] == 1
    assert res.distances[2] == 2
    assert res.distances[3] == 2
    assert res.path_to(4) == [0, 4]


def test_dfs_iterativa_visita_em_profundidade_e_suporta_grafo_longo() -> None:
    """DFS iterativa deve percorrer ramos até o fim e suportar caminhos > 1500 vértices."""
    # Árvore binária simples: 0 -> (1 -> 3, 4), (2 -> 5)
    g = Graph(6)
    g.add_edge(0, 1)
    g.add_edge(0, 2)
    g.add_edge(1, 3)
    g.add_edge(1, 4)
    g.add_edge(2, 5)

    res = dfs(g, 0)
    # 0 visita primeiro a subárvore de 1 inteira (1, 3, 4) antes de visitar 2 e 5
    assert res.order == [0, 1, 3, 4, 2, 5]
    assert res.path_to(4) == [0, 1, 4]
    assert res.path_to(5) == [0, 2, 5]

    # Teste de resistência contra RecursionError (limite padrão do Python é 1000)
    long_line = _build_line_graph(1500)
    long_res = dfs(long_line, 0)
    assert len(long_res.order) == 1500
    assert long_res.order[-1] == 1499


def test_connected_components_ordena_da_maior_para_a_menor() -> None:
    """Componentes conexas devem vir ordenadas por tamanho decrescente."""
    g = Graph(7)
    # Componente de tamanho 2: {0, 1}
    g.add_edge(0, 1)
    # Componente de tamanho 4: {2, 3, 4, 5}
    g.add_edge(2, 3)
    g.add_edge(3, 4)
    g.add_edge(4, 5)
    # Componente isolada de tamanho 1: {6}

    comps = connected_components(g)
    assert comps == [[2, 3, 4, 5], [0, 1], [6]]


def test_travessias_respeitam_mascara_de_isolamento_e_arestas_inativas() -> None:
    """Isolar um vértice ponte ou desativar aresta deve dividir a componente conexa."""
    # Caminho 0 - 1 - 2 - 3 - 4
    g = _build_line_graph(5)

    # Desativa a aresta (1, 2)
    g.set_edge_active(1, 2, False)
    assert bfs(g, 0).order == [0, 1]
    assert connected_components(g) == [[2, 3, 4], [0, 1]]
    # Mas na topologia bruta (only_active=False), o grafo segue conexo
    assert connected_components(g, only_active=False) == [[0, 1, 2, 3, 4]]

    # Reativa (1, 2) e isola o vértice central 2
    g.set_edge_active(1, 2, True)
    g.set_vertex_isolated(2, True)
    assert bfs(g, 0).order == [0, 1]
    assert bfs(g, 2).order == [2]
    assert connected_components(g) == [[0, 1], [3, 4], [2]]


def test_travessia_em_vertice_inexistente_levanta_erro() -> None:
    """Chamar bfs ou dfs em vértice ausente deve levantar VertexNotFoundError."""
    g = Graph(3)
    with pytest.raises(VertexNotFoundError):
        bfs(g, 10)
    with pytest.raises(VertexNotFoundError):
        dfs(g, -1)
