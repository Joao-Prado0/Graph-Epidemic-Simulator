"""Testes unitários do algoritmo de Dijkstra sobre distância efetiva."""

from __future__ import annotations

import math

import pytest

from epidemia.core.errors import ParameterOutOfRangeError, VertexNotFoundError
from epidemia.core.graph import (
    Graph,
    bfs,
    dijkstra,
    transmission_probability,
    travel_cost,
)


def test_dijkstra_em_grafo_de_tres_paises_prefere_rota_via_hub_aereo() -> None:
    """Critério de aceitação M1: grafo de 3 países onde 2 conexões fortes batem 1 fraca.

    País 0 --(w=0.1)--> País 2 (rota direta rara)
    País 0 --(w=1.0)--> País 1 --(w=1.0)--> País 2 (conexão via hub internacional)
    """
    beta = 0.2
    g = Graph(3, beta=beta)
    g.add_edge(0, 2, weight=0.1)
    g.add_edge(0, 1, weight=1.0)
    g.add_edge(1, 2, weight=1.0)

    # Em número de saltos (BFS), o menor caminho é o direto [0, 2] (1 salto)
    assert bfs(g, 0).path_to(2) == [0, 2]

    # No Dijkstra epidemiológico, passar pelo hub 1 tem menor custo (-ln p) e maior probabilidade
    res = dijkstra(g, 0)
    assert res.path_to(2) == [0, 1, 2]

    p_hub = transmission_probability(1.0, beta)
    expected_cost = 2.0 * travel_cost(p_hub)
    assert math.isclose(res.distance_to(2), expected_cost, rel_tol=1e-12)
    assert math.isclose(res.path_probability(2), p_hub * p_hub, rel_tol=1e-12)


def test_dijkstra_calculado_a_mao_com_custos_explicitos() -> None:
    """Verifica distâncias e árvore de caminhos mínimos em grafo de 4 vértices."""
    g = Graph(4)
    g.add_edge(0, 1, weight=1.0, cost=1.0)
    g.add_edge(1, 2, weight=1.0, cost=2.0)
    g.add_edge(0, 2, weight=1.0, cost=5.0)
    g.add_edge(2, 3, weight=1.0, cost=1.5)

    res = dijkstra(g, 0)
    assert res.distances == {0: 0.0, 1: 1.0, 2: 3.0, 3: 4.5}
    assert res.path_to(3) == [0, 1, 2, 3]


def test_dijkstra_parada_antecipada_e_vertice_inalcancavel() -> None:
    """Quando target é informado, deve encontrar o custo exato de target; desconexos dão inf."""
    g = Graph(5)
    g.add_edge(0, 1, weight=1.0, cost=1.0)
    g.add_edge(1, 2, weight=1.0, cost=1.0)
    g.add_edge(2, 3, weight=1.0, cost=10.0)
    # Vértice 4 fica desconexo

    res_target = dijkstra(g, 0, target=1)
    assert res_target.distance_to(1) == 1.0
    assert res_target.path_to(1) == [0, 1]

    res_all = dijkstra(g, 0)
    assert res_all.distance_to(4) == math.inf
    assert res_all.path_probability(4) == 0.0
    assert res_all.path_to(4) == []


def test_dijkstra_com_beta_sob_demanda_e_mascara_de_isolamento() -> None:
    """Passar beta em dijkstra recalcula os custos sem mutar o grafo e respeita isolamento."""
    g = Graph(3, beta=0.05)
    g.add_edge(0, 1, weight=0.8)
    g.add_edge(1, 2, weight=0.5)

    res_custom_beta = dijkstra(g, 0, beta=0.3)
    expected = travel_cost(transmission_probability(0.8, 0.3)) + travel_cost(
        transmission_probability(0.5, 0.3)
    )
    assert math.isclose(res_custom_beta.distance_to(2), expected, rel_tol=1e-12)

    # Isolando o vértice intermediário 1, o destino 2 torna-se inalcançável
    g.set_vertex_isolated(1, True)
    res_isolated = dijkstra(g, 0, beta=0.3)
    assert res_isolated.distance_to(2) == math.inf
    assert res_isolated.path_to(2) == []

    # Com only_active=False, ignora o isolamento
    res_raw = dijkstra(g, 0, beta=0.3, only_active=False)
    assert math.isclose(res_raw.distance_to(2), expected, rel_tol=1e-12)


def test_dijkstra_validacoes_de_entrada() -> None:
    """Vértices inválidos ou beta não positivo devem levantar exceções do domínio."""
    g = Graph(2)
    with pytest.raises(VertexNotFoundError):
        dijkstra(g, 99)
    with pytest.raises(VertexNotFoundError):
        dijkstra(g, 0, target=99)
    with pytest.raises(ParameterOutOfRangeError):
        dijkstra(g, 0, beta=0.0)
    with pytest.raises(ParameterOutOfRangeError):
        dijkstra(g, 0, beta=-0.5)
