"""Testes unitários para pesos (weights.py) e estrutura Graph (graph.py) (Passo 2 — M1)."""

from __future__ import annotations

import math

import pytest

from epidemia.core.analysis import average_degree, find_bridges
from epidemia.core.errors import (
    InvalidEdgeError,
    ParameterOutOfRangeError,
    VertexNotFoundError,
)
from epidemia.core.graph import (
    MAX_TRANSMISSION_PROBABILITY,
    Graph,
    normalized_route_weight,
    transmission_probability,
)


def test_funcoes_de_peso_probabilidade_e_custo() -> None:
    """Verifica w = ln(1+r)/ln(1+max_r), p = 1 - exp(-beta*w) e custo = -ln(p)."""
    assert math.isclose(normalized_route_weight(99, 99), 1.0)
    w = normalized_route_weight(10, 100)
    assert 0.0 < w < 1.0

    g = Graph(2, beta=0.5)
    g.add_edge(0, 1, weight=2.0)

    expected_p = 1.0 - math.exp(-0.5 * 2.0)
    expected_cost = -math.log(expected_p)
    assert math.isclose(transmission_probability(2.0, 0.5), expected_p, rel_tol=1e-12)
    assert math.isclose(g.edge_weight(0, 1), 2.0)
    assert math.isclose(g.edge_cost(0, 1), expected_cost, rel_tol=1e-12)

    g.update_transmission_costs(beta=100.0)
    assert math.isclose(g.edge_cost(0, 1), -math.log(MAX_TRANSMISSION_PROBABILITY), rel_tol=1e-12)


def test_insercao_e_remocao_de_vertices_e_arestas() -> None:
    """Valida operações fundamentais de criação, consulta e remoção (RF15)."""
    g = Graph(3, beta=0.5)
    u3 = g.add_vertex(country_id=7, position=(10.0, -20.0))
    assert u3 == 3
    assert g.num_vertices == 4
    assert g.vertex_info(3).country_id == 7
    assert g.vertex_info(3).position == (10.0, -20.0)

    g.add_edge(0, 1, weight=2.0)
    g.add_edge(1, 2, weight=1.0)
    assert g.num_edges == 2
    assert g.has_edge(0, 1) and g.has_edge(1, 0)
    assert set(g.neighbors(1)) == {0, 2}

    g.remove_edge(0, 1)
    assert g.num_edges == 1
    assert not g.has_edge(0, 1)

    g.remove_vertex(2)
    assert not g.has_vertex(2)
    assert g.num_edges == 0
    assert list(g.neighbors(1)) == []


def test_mascara_de_arestas_e_isolamento_de_vertice() -> None:
    """Isolar vértice ou desativar aresta oculta conexões sem destruir o grafo (E1, C3)."""
    g = Graph(4)
    g.add_edge(0, 1, weight=1.0)
    g.add_edge(1, 2, weight=1.0)
    g.add_edge(2, 3, weight=1.0)

    g.set_vertex_isolated(1, True)
    assert g.is_vertex_isolated(1)
    assert list(g.neighbors(1, only_active=True)) == []
    assert list(g.neighbors(0, only_active=True)) == []
    assert list(g.neighbors(2, only_active=True)) == [3]
    assert set(g.neighbors(1, only_active=False)) == {0, 2}

    g.set_vertex_isolated(1, False)
    assert set(g.neighbors(1, only_active=True)) == {0, 2}

    g.set_edge_active(1, 2, False)
    assert not g.has_edge(1, 2, only_active=True)
    assert g.has_edge(1, 2, only_active=False)

    g.reset_masks()
    assert set(g.neighbors(1, only_active=True)) == {0, 2}


def test_integracao_com_analise_m2() -> None:
    """Garante que as funções de análise do M2 rodam diretamente sobre Graph."""
    g = Graph(4)
    g.add_edge(0, 1, weight=1.5)
    g.add_edge(1, 2, weight=2.5)
    g.add_edge(2, 3, weight=3.5)

    assert math.isclose(average_degree(g), 1.5)
    assert find_bridges(g) == [(0, 1), (1, 2), (2, 3)]


def test_validacao_de_erros_no_grafo() -> None:
    """Operações ilegais levantam exceções da hierarquia de domínio."""
    with pytest.raises(ParameterOutOfRangeError):
        Graph(-1)
    with pytest.raises(ParameterOutOfRangeError):
        Graph(2, beta=0.0)

    g = Graph(3)
    with pytest.raises(InvalidEdgeError):
        g.add_edge(1, 1)
    with pytest.raises(InvalidEdgeError):
        g.add_edge(0, 1, weight=-0.5)
    with pytest.raises(VertexNotFoundError):
        g.add_edge(0, 99)
    with pytest.raises(InvalidEdgeError):
        g.remove_edge(0, 2)
